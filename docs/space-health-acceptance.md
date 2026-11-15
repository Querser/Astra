# NASA/CSA Integration Acceptance — November 14, 2026

The check was performed on temporary SQLite and demonstration profiles. The main user story was not used in the tests. After acceptance, the regular API was launched on the existing local database; migrations added new tables and an optional conditions field, without deleting records.

## Result

- 15 local NASA/CSA scientific cards are loaded by the API and are actually selected during the Qwen context assembly.
- RadLab: 84 DosTel1 points, ISS Columbus, 01–02.04.2022; absorbed dose power `µGy/hour`; all equivalent dose power values are missing and are not substituted.
- OSD-575 v3: 532 records, 4 anonymized participants, 28 samples, 19 analysts; missing values, original units, time points, and laboratory boundaries are preserved.
- Re-import adds 0 records. CSV hashes are checked before parsing.
- Manual measurement conditions survive creation, editing, reading, and analysis. Old records return unknown conditions.
- Scientific reference, device archive, researcher participants, synthetic and personal records are marked separately.
- Operational JSONL contains routes, codes, duration, model attempt, tokens, and import counters, but not complaint text or health values.

## Commands and Testimonies

```powershell
# backend
..\.venv\Scripts\python.exe -m pytest tests -q --tb=short
# 75 passed

..\.venv\Scripts\python.exe -X utf8 verify_space_chat.py
# 3/3 local_model:qwen3:8b; RadLab follow-up and OSD-575 include research citations

..\.venv\Scripts\python.exe -X utf8 verify_chat_browser.py --live
# 14/14 real qwen3:8b responses; each generation finished with attempt=1, category=ok, done_reason=stop

..\.venv\Scripts\python.exe -X utf8 verify_chat_browser.py
# 16 cards, 84 RadLab points, OSD-575 separated; profile drafts, answers, errors, and reloads isolated

# frontend
npm run build
# TypeScript and the Vite production build passed
```

Real model configuration: Ollama 0.32.5, `qwen3:8b`, local identifier `500a1f067a9f`, loopback `127.0.0.1:11434`, `num_ctx=8192`, `num_predict=600`, `temperature=0`, `think=false`, no more than two attempts.

During independent verification, a continuation defect was found and fixed: after a question about RadLab, the replica «These values relate personally to me?» lost archival context and could assign a series to a profile. Now the last `research:` source is moved into a limited context of the next move. Repeated real response: «No. These values do not relate personally to you. They represent environmental measurements by the device, not the personal dose of the crew».

Browser check also found that general CSS was hiding external links. Rule replaced: source links are visible, but opening them for application work is not required. RadLab time is shown as the original string without conversion, since CSV does not contain time zone.

## Boundaries

- EDA is not imported: for the selected series, the file, units, frequency, and exact device location are not confirmed.
- NLSP is not connected: specific free file and access conditions are not confirmed.
- DONKI is not used for personal output: a space weather event is not an individual dose, and an autonomous warning requires fresh data.
- CANS is presented only as a future adapter point: public stream and measurement scheme in the CSA article are absent.
- RadLab remains an archival context of the environment, OSD-575 — a separate research set. Neither of them has been converted into personal crew metrics.
- Statistical forecasts of ASTRA are preserved without changes: calculation is made by reproducible code, Qwen explains the result. Clinical validation is not claimed.

Metadata and links to the scientific sources themselves are preserved.
