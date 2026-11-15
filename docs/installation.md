# Installing and launching ASTRA

## What is included

The repository includes the backend, frontend, local knowledge base, database
migrations, research snapshots, setup scripts and launchers. Python, Node.js,
Ollama and model weights are external runtimes.

The setup scripts create `.venv`, install exact Python and npm dependencies,
initialize SQLite and reuse an existing Ollama model cache. On Windows, setup
can install Ollama through Windows Package Manager. On macOS and Linux, install
Ollama from its official download page before setup if the local assistant is
required.

## Windows

Requirements: Windows 10 or newer, Python 3.10-3.13, Node.js 22 or 24 LTS and
Windows Package Manager for automatic Ollama installation.

```powershell
.\Setup_ASTRA.cmd
.\Launch_ASTRA.exe
```

Use `.\Launch_ASTRA.cmd` if the executable is unavailable. Setup can run without
the model by using `.\scripts\setup.ps1 -SkipModel`.

## macOS and Linux

Requirements: Python 3.10-3.13, Node.js 22 or 24 LTS, npm and curl. Install
Ollama from <https://ollama.com/download> before setup to enable the assistant.

```bash
chmod +x scripts/setup.sh scripts/launch.sh launch_astra.sh
./scripts/setup.sh
./launch_astra.sh
```

## Runtime behavior

The launcher starts only loopback services, waits for the API and frontend,
then opens `http://127.0.0.1:5173/`. Press Ctrl+C in the launcher window to stop
services started by that launcher. It does not terminate services that were
already running.

If Ollama or the configured model is missing, ASTRA starts in offline mode.
Profiles, records, research views and statistical forecasts remain available;
the interface labels the local AI assistant as offline.

## Diagnostics

```powershell
.\.venv\Scripts\python.exe .\scripts\diagnose.py
```

```bash
./.venv/bin/python ./scripts/diagnose.py
```

The command reports versions, dependencies, database state, loopback URLs,
Ollama and model availability, and log locations. It does not print profile
records or secrets.

## Local files

- Database: `~/.astra/data/astra.sqlite3`
- Logs: `~/.astra/data/logs/`
- Python environment: `.venv/`
- npm packages: `frontend/node_modules/`
- Model: Ollama's platform-specific cache

Set `ASTRA_DATA_DIR` to place the database and logs elsewhere. Set
`ASTRA_OLLAMA_MODEL` to select another installed model.

## Troubleshooting

- Port 8000 must be available for the API.
- Port 5173 must be available for the frontend.
- Port 11434 belongs to local Ollama.
- Run `scripts/diagnose.py` and inspect `~/.astra/data/logs/` after a failure.
- Rerunning setup is safe: migrations are idempotent, npm uses its lock file and
  Ollama reuses cached model layers.

The launcher executable is not signed. Windows may show a reputation warning
for a newly built local executable. Production distribution should sign the
binary with the project publisher's code-signing certificate.
