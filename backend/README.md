# ASTRA API

Stages 4–13 provide a locally runnable FastAPI service backed by SQLite, connected local UI, deterministic descriptive and source-linked reference comparison, a guarded local Ollama adapter, statistical profiles, cautious forecasts, self-reports, environmental context, what-if records, human handoff and an offline sync simulator. It supports fictional crew profiles, provenance records, observations, revision history and audit events. The reference comparisons are conditional and not validated astronaut mission limits; no confirmed diagnosis or medication course is generated.

## Windows setup

Run from this directory with Python 3.10–3.13:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --requirement requirements.lock --editable ".[dev]"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --no-access-log
```

On startup the service applies the repository migration and imports the bundled NASA research snapshots idempotently. The default database location is `~/.astra/data/astra.sqlite3`, outside the repository. Set `ASTRA_DATA_DIR` to choose a different local data directory or `ASTRA_DATABASE_URL` to set an explicit SQLite URL for tests/development. The import uses only local CSV files and checks their SHA-256 values.

Structured diagnostic logs are written to `~/.astra/data/logs/astra.jsonl` (or `ASTRA_DATA_DIR/logs/astra.jsonl`). The file rotates at 2 MB with four backups. Entries include request ID, method, route template, status, duration, startup/shutdown, error type and bounded browser event codes. Request bodies, query strings, symptom text and measurement values are excluded. `X-Request-ID` lets you match a browser failure to the server log. Database mutation history remains in the separate `audit_events` table. The `--no-access-log` option prevents Uvicorn from printing full request URLs to its default access log.

Open `http://127.0.0.1:8000/api/v1/health` for the health response or `http://127.0.0.1:8000/docs` for the API documentation. The service deliberately binds only to loopback by default. Stop it with `Ctrl+C`.

The explanation endpoint returns a calculated Russian overview by default. Set `ASTRA_ENABLE_EXPERIMENTAL_LLM=1` only while evaluating local Ollama wording; `ASTRA_OLLAMA_BASE_URL` must be HTTP loopback with an explicit port. The model may only select a precomputed statement, and its output does not change the structured report. See [the analysis integration guide](../docs/health-analysis-integration.md).

`DELETE` routes archive a crew profile or withdraw a health record; they never silently remove history. The manual UI calls `POST /api/v1/manual/observations` without a source ID; the API creates and assigns a manual provenance source. `value` is either `{ "kind": "scalar", "amount": 72 }` or, only for `blood_pressure`, `{ "kind": "blood_pressure", "systolic": 120, "diastolic": 80 }`. Optional `measurement_context` records method, device, site, activity state, posture, mission phase, habitat, subjective status, baseline-series status and notes. All `observed_at` values must include a timezone offset. Analysis uses current observation revisions, not the separate audit events. The source-based legacy creation, CSV import and synthetic scenario endpoints return 403 by default; set `ASTRA_ENABLE_AUTOMATED_INGESTION=1` when developing future adapters. The packaged research import is a separate operation and needs no automated-ingestion flag.

See `../docs/stage3-ingestion-and-scenarios.md` for the synthetic-scenario and CSV-import contracts, `../docs/stages4-7.md` for analysis/assistant/forecast contracts, and `../docs/stages8-13.md` for P1 and demo contracts. Synthetic records are visibly marked in the API contract; no generated value is clinically validated.

Run tests:

```powershell
python -m pytest
```

## Local chat and reference index

From the catalog `backend` run `python -m app.chat_retrieval` to view old sections of the dialog reference index. The new set `reference_docs/ASTRA_SPACE_SCIENCE.json` is indexed by the function `retrieve_space_science()` and is available at `GET /api/v1/reference/space-science`. After changing the cards, restart the API. Chat selects no more than two science-related cards relevant to the reply and saves their stable IDs in the response links.

Archival data is available at `GET /api/v1/research/radlab` and `GET /1/api/v1/research/osd-575`. Manual re-import of local snapshots:

```powershell
python import_research_snapshots.py --database C:\path\to\disposable.sqlite3
```

For normal startup, this command is not needed. Metadata and limitations are described in `../docs/research-snapshots.md`.

The chat uses the model `qwen3:8b` through local Ollama, by default on `127.0.0.1:11434`. A window of 8192 tokens is allocated per request, including a maximum of 600 tokens in the response. Before sending, the application limits message content to 7200 bytes UTF-8. For the Qwen tokenizer, this upper bound is conservative. The remaining window is reserved for system tokens. The last replica and its associated question are saved first, then new facts, reference fragments, other active facts, and relevant profile measurements. If the user's replica exceeds the budget itself, the chat suggests splitting it into parts. For reviewing metrics, summary values of the profile are requested.

Each generation attempt records `chat_generation_attempt` in the JSON log. The request identifier links the initial attempt with retries: up to two for repeated responses or ambiguous duration and up to one for other correctable errors. Records contain input bytes, available Ollama token counters, reason for termination, check category, and result. For fields that Ollama did not return, `unavailable` is recorded.

## Protection of Local API

The API limits the request body to 4 MiB, rejects browser requests to change data from a different Origin, and sends headers no-store, nosniff, and X-Frame-Options. By default, the interface is accessible with http://127.0.0.1:5173; local tool requests without Origin are allowed. This does not replace authentication when opening the API outside the local computer. Requests to the local model do not use a proxy and do not follow redirects. Data in the model context is marked as untrusted; this reduces the risk of instruction substitution, but does not guarantee protection against all attacks.
