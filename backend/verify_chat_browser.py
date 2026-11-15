"""Run isolated browser acceptance against Vite, the application API and temporary SQLite.

--live uses the installed Ollama model. --replay-db reads an authorized historical
conversation from SQLite in read-only mode, then replays only its user turns.
Set ASTRA_PLAYWRIGHT to an installed Playwright package if it is not on NODE_PATH.
"""
import argparse
from contextlib import ExitStack, closing
from pathlib import Path
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import threading
from urllib.request import urlopen

import uvicorn
from app.db import Database, sqlite_url, upgrade_database
from app.forecast_demo_seed import seed_forecast_profiles


ROOT = Path(__file__).resolve().parents[1]


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def stop(proc):
    if proc.poll() is None:
        proc.terminate()
        proc.wait(timeout=15)


def fixture_app(web_url):
    from app.main import create_app
    app = create_app(browser_origins={web_url})

    def controlled(*args, **kwargs):
        gate = Path(os.environ["ASTRA_QA_GATE"])
        gate.with_suffix(".entered").touch()
        for _ in range(1200):
            if gate.exists():
                break
            time.sleep(0.05)
        else:
            raise RuntimeError("fixture gate timed out")
        return {"answer": "Have you vomited?"} if gate.read_text() == "ok" else None

    app.state.chat_model.generate = controlled
    return app


def historical_turns(path):
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        rows = db.execute("SELECT crew_member_id, role, body, engine FROM chat_messages WHERE created_at "
                          "BETWEEN ? AND ? ORDER BY created_at,id", ("2026-11-12 16:30", "2026-11-12 16:35")).fetchall()
    if len(rows) != 12 or len({r[0] for r in rows}) != 1 or [r[1] for r in rows] != ["user", "assistant"] * 6:
        raise ValueError("Original six-turn interaction not uniquely present in this database")
    failed = [index for index, row in enumerate(rows[1::2], 1) if (row[3] or "").startswith("local_model_error:")]
    print("Archived baseline: six user turns; model errors at", failed)
    return [r[2] for r in rows if r[1] == "user"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--replay-db", type=Path)
    args = parser.parse_args()
    replay = historical_turns(args.replay_db) if args.replay_db else []
    with tempfile.TemporaryDirectory(prefix="astra-browser-qa-") as directory, ExitStack() as stack:
        data = Path(directory)
        url = sqlite_url(data / "astra.sqlite3")
        upgrade_database(url)
        db = Database(url)
        with db.session_factory() as session:
            seed_forecast_profiles(session)
        db.dispose()
        api_port, web_port = port(), port()
        env = dict(os.environ, ASTRA_DATA_DIR=directory, ASTRA_DATABASE_URL=url, ASTRA_CHAT_MODEL_ENABLED="1",
                   ASTRA_QA_GATE=str(data / "gate"), VITE_API_BASE_URL="/api/v1",
                   PYTHONUTF8="1", NO_PROXY="127.0.0.1,localhost")
        api_url = f"http://127.0.0.1:{api_port}"
        web_url = f"http://127.0.0.1:{web_port}"
        os.environ.update({k: env[k] for k in ("ASTRA_DATA_DIR","ASTRA_DATABASE_URL","ASTRA_QA_GATE","ASTRA_CHAT_MODEL_ENABLED")})
        from app.main import create_app
        app = create_app(browser_origins={web_url}) if args.live else fixture_app(web_url)
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=api_port, access_log=False))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        def stop_api():
            server.should_exit = True
            thread.join(30)
            for handler in app.state.diagnostics.handlers:
                handler.close()
        stack.callback(stop_api)
        proc = subprocess.Popen([shutil.which("node"), "node_modules/vite/bin/vite.js","--host","127.0.0.1",
                                 "--port", str(web_port),"--strictPort"], cwd=ROOT/"frontend",env=env, stdout=subprocess.DEVNULL)
        stack.callback(stop, proc)
        for health in (api_url + "/api/v1/health", web_url):
            for _ in range(100):
                if proc.poll() is not None:
                    raise RuntimeError("Vite quit")
                try:
                    with urlopen(health, timeout=0.5):
                        break
                except OSError:
                    time.sleep(0.15)
            else:
                raise RuntimeError("Service not ready")
        try:
            subprocess.run([shutil.which("node"), str(ROOT / "frontend/tests/chat-browser.cjs")],
                           env=env, input=json.dumps(dict(api=api_url, web=web_url, live=args.live, replay=replay)),
                           encoding="utf-8", check=True)
        finally:
            if args.live:
                attempts = []
                operational = []
                for line in (data / "logs" / "astra.jsonl").read_text(encoding="utf-8").splitlines():
                    event = json.loads(line)
                    operational.append(event)
                    if event.get("event") == "chat_generation_attempt":
                        attempts.append(event)
                        print("generation", *(event.get(k) for k in ("attempt","category","retry_reason","prompt_eval_count","done_reason")))
                if not attempts and not sys.exc_info()[0]:
                    raise AssertionError("Real server has no chat_generation_attempt diagnostics")
                if any(message.casefold() in line.casefold() for message in replay if len(message) > 10
                       for line in (json.dumps(row, ensure_ascii=False) for row in operational)):
                    raise AssertionError("Private replay text in operational log")
                if any(row.get("attempt") not in {1, 2, 3} or not row.get("request_id") for row in attempts):
                    raise AssertionError("Missing identity or unbounded attempt in operational log")


if __name__ == "__main__":
    main()
