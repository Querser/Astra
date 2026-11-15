# Stages 4–7 delivery notes

## Stage 4 — connected local interface

The React interface now consumes the loopback API at `http://127.0.0.1:8000/api/v1` by default. It creates fictional profiles and manual sources, accepts scalar observations, runs seeded scenarios, shows history as an SVG chart plus an equivalent table, and displays explicit synthetic/provenance labels. Development CORS permits only `http://127.0.0.1:5173`; production should serve UI and API from one local origin before handling real data.

The UI uses keyboard-operable native forms, field labels, a live status message, text labels instead of color-only states, and a table alternative for its chart. Blood-pressure pair entry and file-import UI are intentionally deferred; their API contracts already exist.

## Stage 5 — deterministic analysis

`POST /api/v1/analysis/run` processes only current, non-withdrawn, non-superseded observations. It writes a versioned `AnalysisResult` that keeps observed facts, findings, source-linked checks, hypotheses and unknowns separate. The first conditional public adult references and their limitations are in [the evidence register](medical-demo-evidence.md); they are not a NASA mission medical protocol.

The implemented rules are deliberately limited:

- each recorded metric receives a descriptive snapshot: latest value, count, provenance, and when comparable, observed range, median and difference from the previous value;
- a one-point metric is explicitly marked as insufficient for within-person change comparison;
- provenance labels such as `synthetic_ui_entry` do not create quality alerts; other declared quality flags are grouped by flag;
- inconsistent units within one metric create a **unit consistency review** item and prevent numeric comparison;
- the latest pulse, SpO₂, respiratory rate and sleep duration are conditionally compared with cited public adult reference points; out-of-reference readings create review findings, and nearby SpO₂/breathing deviations may create a co-occurrence finding;
- with six scalar entries for one metric, a robust modified-z descriptive comparison may create a **descriptive series review** item;
- no rule establishes a confirmed disease, prescribes medicine or predicts treatment effects. A zero-signal result is never displayed as proof that values are normal or safe.

Alerts record the rule ID, exact explanation and acknowledgement state. Rule calculations live in `backend/app/analytics.py`, not in the language model.

## Stage 6 — local assistant

`POST /api/v1/assistant/explain` returns a calculated overview of the saved analysis by default. The Ollama wording adapter is experimental and activates only with `ASTRA_ENABLE_EXPERIMENTAL_LLM=1`; it sends a saved deterministic analysis, an optional bounded question and the local `ASTRA Evidence Rules` document to Ollama on loopback. It never uses a cloud API. Its default candidate is the installed `qwen2.5vl:3b`; configure another local model through `ASTRA_OLLAMA_MODEL`.

The experimental adapter requires JSON with a short Russian summary, the exact local-source citation and `not_a_diagnosis: true`; it also rejects text containing selected prescription markers. Rejected output returns the calculated overview when measurements are available. The installed model was observed adding an invented profile identifier and English wording, so its free-text output is excluded from the normal UI until a benchmark and review are complete.

## Stage 7 — statistical profile and forecast

`GET /api/v1/baselines/{crew_id}` reports scalar count, median and MAD by metric as a descriptive personal profile. It is not a clinical baseline.

`POST /api/v1/forecasts/run` creates entries for 24, 72 and 168 hours. It refuses numeric output unless one metric has at least eight current scalar observations, a seven-day history span and a single unit. When sufficient, it uses rolling time-ordered holdouts to compare a linear trend with persistence, stores the selected method, held-out MAE, empirical interval coverage and an uncertainty interval. Synthetic scenario output tests code paths only; it does not establish medical or astronaut-health forecasting accuracy.
