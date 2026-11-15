# ADR-001 — Local-first modular demonstration

**Status:** proposed, 2026-11-06. **Scope:** Stage 0 decision; no software has been built.

## Observed starting point

- At the time of the initial review, the Windows workspace contained a project specification but no application code, tests, Git repository or established documentation conventions.
- Intel Core i5-12500H (12 cores/16 logical processors), 16,870,260,736 bytes physical RAM (~15.71 GiB), NVIDIA RTX 3070 Ti Laptop GPU with 8,192 MiB VRAM per `nvidia-smi`, plus Intel Iris Xe. Windows' generic video-controller report showed ~4 GiB for NVIDIA; use the device-specific `nvidia-smi` reading for planning, then benchmark.
- Python 3.10.11 and 3.14 are installed; the suggested 3.11+ stable target is not installed. Node 24.16.0, npm 11.13.0, Ollama 0.32.5 and Docker CLI 29.4.3 exist. Docker's Linux daemon was unreachable during inspection; Docker must be optional.
- `ollama list` showed `qwen2.5vl:3b` (3.2 GB, 3.8B Q4_K_M) and `dolphin-llama3:latest` (4.7 GB, 8B Q4_0). No OLMo model appeared. The inspected Python environment had no `ai2-olmo`, `transformers`, `torch` or `llama-cpp-python` package. This is not a claim about every environment or directory on the machine.

## Decision and data flow

Use one local FastAPI process, SQLite database and static React/TypeScript client served from the same origin. Bind to `127.0.0.1` by default. A separate, narrow adapter calls Ollama on localhost for **explanation only**. No message broker, remote database or cloud LLM is needed for P0. Choose and pin dependencies in Stage 1 after checking current package compatibility; proposed FastAPI/Pydantic/SQLAlchemy/Alembic and React/Vite are candidates, not installed project dependencies.

```text
manual form / seeded generator / later file or sensor adapter
            -> typed ingest and validation
            -> append-only observations + source + audit in SQLite
            -> deterministic, versioned analysis
            -> facts | findings | guidance | hypotheses | unknowns + alert
            -> /api/v1 -> local UI and accessible history/chart
                         -> optional local LLM explanation of the same result
```

Rejected input enters a quarantine record with reason; it is never silently normalized into a valid measurement. Import files, documents and complaint text are untrusted data. UI and LLM output cannot modify rule results or inject new clinical protocols. Local model failure returns an explicit unavailable/insufficient-evidence state while data entry and analysis remain usable.

## Typed boundaries (proposed)

| Contract | Required fields / invariant |
|---|---|
| `CrewMember` | Opaque UUID, fictional-demo flag; minimal permitted baseline characteristics, no real names in demo. |
| `DataSource` | Stable ID, source type (`manual`, `synthetic`, `import`, later `sensor`), title/version, acquisition and usage metadata. |
| `Observation` | UUID, crew ID, metric kind, typed scalar or blood-pressure pair, canonical unit, `observed_at` UTC plus original offset, `recorded_at`, source ID, synthetic flag, quality flags, revision/supersedes ID. No implicit unit conversion. |
| `SymptomReport` | UUID, crew ID, text and structured self-report where supplied, observed/recorded times, source and synthetic flag; free text treated as untrusted. |
| `IngestionRecord` | Attempt ID, raw input reference, validity status and rejection reason; avoid logging sensitive values. |
| `AnalysisResult` | UUID, input observation IDs, rule-set version, timestamp, separate arrays for observed facts, deterministic findings, evidence-backed guidance, hypotheses and unknowns; each guidance item has vetted source title/section. |
| `Alert` | Result/rule/input IDs, rationale, uncertainty, human acknowledgement and immutable state history; no unreviewed clinical severity. |
| `AuditEvent` | Actor/action/object/timestamp and revision reference without raw health values. |

Units and metric enums need an explicit versioned schema in Stage 2; timestamps must be timezone-aware. Corrections append a superseding record and preserve prior history. A future CRUD `DELETE` means a documented withdrawal/tombstone workflow, subject to retention policy, rather than silent erasure. Store the SQLite file, logs and local model files in a user data directory outside the repository. No real health data in Git or demo exports.

Initial API surface: `/api/v1/crew`, `/api/v1/observations`, `/api/v1/symptoms`, `/api/v1/analysis`, `/api/v1/alerts`, `/api/v1/assistant/explain`. OpenAPI with example payloads is the A/B integration contract. P0 uses one local demo operator and fictional profiles; it must not claim secure multi-user isolation. A real deployment needs an approved identity, roles, encryption/retention and threat model. Same-origin delivery, explicit origin/CSRF protection for writes, narrow CORS and non-sensitive audit logs are Stage 2 design gates.

Suggested structure once implementation is authorized:

```text
backend/app/{api,contracts,ingest,storage,analytics,assistant,security}/
backend/migrations/  backend/tests/
frontend/src/{api,components,pages}/  frontend/tests/
demo/  docs/stage0/
```

## Analytics and model decision

Deterministic code owns schema/unit validation, freshness/conflict checks, traceable descriptive changes, alert rules and every critical calculation. Simple statistics are the first P1 forecast baseline. Trainable forecasting is considered only after enough real, consented, relevant longitudinal data exists. Evaluation uses time-ordered train/validation/test splits and rolling-origin evaluation; compares last-value and seasonal baselines; reports MAE and interval coverage with missingness/source breakdown; abstains from numeric 24 h/72 h/7 d forecasts when data are insufficient. Prevent leakage across time, subjects and synthetic scenario generation. Synthetic results establish no clinical performance.

The local LLM is a constrained explainer and clarification interface. First test the already installed `qwen2.5vl:3b` on structured, short, multilingual demo prompts; its local presence is **not** evidence of fitness for medical use. Do not select `dolphin-llama3` for the demo without license, safety and behavior review. OLMo is not installed. [Ollama's OLMo 2 listing](https://ollama.com/library/olmo2) lists a 7B package around 4.5 GB and 13B around 8.4 GB: 7B may fit 8 GiB VRAM only after measuring context/KV-cache and runtime overhead; 13B does not fit wholly in 8 GiB VRAM. A text-only [Qwen2.5 3B](https://ollama.com/library/qwen2.5) is a smaller alternative but is not installed and its exact model license must be checked. No weights are downloaded in Stage 0. [Ollama API](https://docs.ollama.com/api) is the proposed local adapter surface. Record actual latency, memory, grounding and abstention behavior before a Stage 6 model decision; no fine-tuning first.

## Lead reconciliation of four Stage 0 workstreams

Requirements/evidence review found no approved ASTRA clinical protocol or universal astronaut thresholds. Backend review therefore narrows P0 alert logic to data quality and descriptive change; the urgent scenario is an operator-declared synthetic handoff. ML review confirms a local runtime exists but model suitability is untested, so the assistant is a Stage 6 acceptance gate rather than a presumed capability. Frontend review turns those limits into visible quality, provenance, uncertainty and synthetic-data labels. The lead adopts one versioned analysis contract across backend and UI and requires integrated offline testing before calling P0 complete. All four reports were proposals; none implemented or validated an application.
