# Reproducible Demonstration of ASTRA

Verified configuration: Windows, Python 3.10, Node 24, Ollama 0.32.5, model `qwen3:8b` (local identifier `500a1f067a9f`), context 8192 tokens, response up to 600 tokens, temperature 0. Internet is not required for running the scripts. Links to original sources in the interface are optional navigation; cards and screenshots are already in the project.

## Launch

In the first PowerShell from the `backend` directory:

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

In the second PowerShell from the `frontend` directory:

```powershell
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`. On startup, the API applies migrations, checks the SHA-256 of local CSVs, and idempotently imports 84 RadLab points and 532 OSD-575 laboratory records. It does not connect to NASA during startup.

For one-time import verification without the main database from the `backend` directory:

```powershell
..\.venv\Scripts\python.exe import_research_snapshots.py --database .\demo-research.sqlite3
```

A repeated launch should show zero new records.

## Scenarios

1. **Sleep and Fatigue.** Select a synthetic profile with a history, open "Input and Analysis", view sleep and fatigue. Ask: "Why might sleep change in space and what data should be compared?". Under the response, the HRP/HRR sources should appear, and the response should distinguish a personal series from general documentation.
2. **RadLab.** Open "Scientific and Archive Data." The graph should contain 84 DosTel1 points, `ISS · Columbus`, interval 2022-04-01—2022-04-02 and `µGy/hour`. The interface should explicitly state that `µSv/hour` is missing and the series is not a personal dose. In the chat, ask about RadLab, then: "Do these values relate personally to me?". The second response should start with "No" and retain the link to RadLab.
3. **OSD-575.** In the same section, select the participant and analytical. The table should show points L-92/L-44/L-3 and R+1/R+45/R+82/R+194, the original unit and boundaries from the file. Ask about OSD-575: the response should name the research participants separately from the ASTRA profile.
4. **Complaint Dialog.** In one profile, sequentially report a new complaint, numerical detail, explicit denial, correction of the number and a new topic. Check that Qwen responds with a new reply, preserves the correction, does not return the cancelled fact and does not transfer the complaint to another profile.
5. **Profile Switch on Request.** Send a message, immediately select another profile and write there. An unfinished message remains with the original profile; draft, history, response and error of another profile are not mixed.
6. **Measurement Conditions.** Create a manual measurement with instrument/method, location, stillness or load, posture and note. Correct the value through history and reload the page. Conditions should be preserved in the new revision; the old record remains in the change log.

## Automatic Checks

From `backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests -q
..\.venv\Scripts\python.exe -X utf8 verify_space_chat.py
..\.venv\Scripts\python.exe verify_chat_browser.py --live
```

From `frontend`:

```powershell
npm run build
```

Checks use temporary databases. They do not change user profiles, conversation or main SQLite.
