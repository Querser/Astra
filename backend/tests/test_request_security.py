import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request

import httpx
import pytest

from app.assistant import urlopen
from app.main import create_app
from app.security import MAX_REQUEST_BYTES


def test_local_api_rejects_foreign_browser_writes_and_large_streams(tmp_path):
    app = create_app(database_url=f"sqlite:///{(tmp_path / 'test.sqlite3').as_posix()}",
                     chat_model_enabled=False)

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            blocked = await client.post("/api/v1/crew", json={"display_name": "Example"},
                                        headers={"Origin": "https://elsewhere.example"})
            assert blocked.status_code == 403
            async def chunks():
                for _ in range(5):
                    yield b"x" * (MAX_REQUEST_BYTES // 4)
            oversized = await client.post("/api/v1/crew", content=chunks())
            assert oversized.status_code == 413
            health = await client.get("/api/v1/health", headers={"Origin": "http://127.0.0.1:5173"})
            assert health.status_code == 200
            assert health.headers["cache-control"] == "no-store"
            assert health.headers["x-content-type-options"] == "nosniff"
            assert health.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    try:
        asyncio.run(exercise())
    finally:
        app.state.database.dispose()


def test_model_client_does_not_follow_redirects():
    paths = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            paths.append(self.path)
            self.send_response(307)
            self.send_header("Location", f"http://127.0.0.1:{self.server.server_port}/other")
            self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = Request(f"http://127.0.0.1:{server.server_port}/model", data=b"synthetic")
        with pytest.raises(HTTPError) as error:
            urlopen(request, timeout=3)
        assert error.value.code == 307
        assert paths == ["/model"]
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
