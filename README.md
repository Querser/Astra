# ASTRA

ASTRA is a local-first demonstration of a health dashboard for astronaut missions.
It combines manually entered measurements, a profile-specific assistant, a local
medical knowledge base, mission context and statistical forecasts. The interface
is in English and accepts symptom reports in English or Russian.

ASTRA is a hackathon prototype. Its medical assessments and forecasts have not
been clinically validated and must not be used as a substitute for medical care.

## Quick start

After cloning the repository on Windows, run:

```powershell
.\Setup_ASTRA.cmd
.\Launch_ASTRA.exe
```

The setup command creates the Python environment, installs locked backend and
frontend dependencies, initializes SQLite, installs Ollama through Windows
Package Manager when necessary, and downloads the configured local model once.
Later launches reuse the installed runtime and model cache.

On macOS or Linux, install Ollama from its official download page if the local
assistant is required, then run:

```bash
chmod +x scripts/setup.sh scripts/launch.sh launch_astra.sh
./scripts/setup.sh
./launch_astra.sh
```

The launcher waits for both services and opens the browser automatically. See
[the installation guide](docs/installation.md) for offline mode, diagnostics,
logs, manual startup and executable-building details.

## Features

- Create and switch between crew profiles, each with its own measurements,
  conversation and medical history.
- Enter health measurements manually and explore their history on the dashboard.
- Describe symptoms in the assistant chat. The local model receives a bounded
  selection of profile data, conversation context and relevant knowledge cards.
- View an anatomical illustration with interactive regions and indicators based
  on available records. The illustration was created with **generative artificial
  intelligence** using a user-provided reference image; it is marked in the UI.
- Explore mission and environment context, locally packaged research data and
  source links.
- Review statistical forecasts for 24 hours, 72 hours and 7 days when enough data
  is available. Forecasts describe measured signals; they are not predictions of
  treatment outcomes.

## How it works

The React interface communicates with a FastAPI service on the same computer.
The API stores profiles and records in SQLite, calculates measurement summaries
and statistical forecasts, and retrieves relevant excerpts from the local
knowledge base. The chat sends the relevant context to a model served by local
Ollama; the model writes the response. Forecast calculations are performed by
application code and interpreted by the model.

After dependencies and the model have been installed, normal operation does not
require an internet connection. Source links are optional external references.
Research datasets are kept separate from personal profile measurements.

## Requirements

- Windows 10 or newer, macOS or Linux; Python 3.10–3.13; Node.js 22 or 24 LTS; npm.
- Ollama with the configured local model for the assistant. The rest of ASTRA
  remains available when Ollama is offline.
- Internet access for the initial installation and model download, if needed.

The steps below use two PowerShell terminals. They assume the current directory
is the project root. If a service is already running on a listed port, reuse it
or stop it before starting another instance.

## Manual launch

### 1. Prepare the local model

Start Ollama and check the installed models:

```powershell
ollama list
```

If `qwen3:8b` is missing, download it once:

```powershell
ollama pull qwen3:8b
```

The default Ollama endpoint is `http://127.0.0.1:11434`.

### 2. Start the API

In the first terminal, from the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock -e "./backend[dev]"
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

On startup, the API applies database migrations and imports the packaged research
snapshots. Check its status at <http://127.0.0.1:8000/api/v1/health> and its API
documentation at <http://127.0.0.1:8000/docs>.

### 3. Start the interface

In the second terminal, from the project root:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open <http://127.0.0.1:5173/>. Stop each server with `Ctrl+C` in its terminal.

## Local data and configuration

By default, the database is stored at `~/.astra/data/astra.sqlite3` and rotating
diagnostic logs are stored under `~/.astra/data/logs/`. Keep these files private:
they can contain profile records and operational information. The diagnostic log
is designed not to include message bodies or measurement values.

Existing Russian profile names, complaints, and chat messages stay unchanged and
remain readable. To preview an optional translation of only known fictional demo
fixtures, run `python backend/translate_demo_records.py --database <path-to-astra.sqlite3>`.
Add `--apply` to create a database backup and update those exact synthetic fixture
fields. This command does not translate personal records or chat history.

Environment variables are read by the API process; `.env.example` documents
them but is not loaded automatically. Set a variable in the API terminal before
starting the server when a different value is needed:

| Variable | Purpose | Default |
| --- | --- | --- |
| `ASTRA_DATA_DIR` | Directory for the local database and logs | `~/.astra/data` |
| `ASTRA_DATABASE_URL` | Explicit database URL, useful for isolated tests | Not set |
| `ASTRA_OLLAMA_BASE_URL` | Local Ollama endpoint | `http://127.0.0.1:11434` |
| `ASTRA_OLLAMA_MODEL` | Model used by the chat | `qwen3:8b` |
| `ASTRA_CHAT_MODEL_ENABLED` | Set to `0` for offline rule testing | `1` |
| `ASTRA_ENABLE_AUTOMATED_INGESTION` | Enable experimental ingestion endpoints | `0` |

The default browser origin and API bind address are restricted to loopback. The
API has no user authentication; do not expose it to a network as a production
service without adding authentication and reviewing its security configuration.

## Test and build

From the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
Set-Location frontend
npm run build
```

For isolated browser checks, install dependencies as above, ensure Chrome is
installed, then run from the project root:

```powershell
.\.venv\Scripts\python.exe backend/verify_chat_browser.py
```

The browser check uses a temporary database and a controlled model response.
Add `--live` to exercise the locally running model. More details are in
[the chat acceptance guide](docs/chat-acceptance.md).

## Project layout

```text
backend/app/             API, analysis, chat and forecast implementation
backend/reference_docs/  Local reference and knowledge documents
backend/tests/           Backend tests
frontend/src/            React interface and assets
docs/                    Architecture, research and acceptance notes
training/                Model training and evaluation experiments
```

The training experiments are research artifacts; their adapters are not the
model currently configured for the running chat. See [backend setup](backend/README.md),
[frontend setup](frontend/README.md) and [research data](docs/research-snapshots.md)
for more detail.

## License and attribution

Original ASTRA project code, documentation and other project-owned materials are
released under the [Apache License 2.0](LICENSE). The repository also includes an
AI-generated anatomical illustration; its creation is disclosed in the interface.
The image used as a reference for its composition is not included in this repository.

External libraries, the separately installed local model and runtime, referenced
medical and space-science publications, and the two packaged NASA research CSVs
retain their own terms. ASTRA's license does not relicense those materials or any
user-entered records. Their origins and applicable acknowledgements are listed in
[third-party notices](THIRD_PARTY_NOTICES.md) and the
[research snapshot manifest](backend/data/research/manifest.json).
