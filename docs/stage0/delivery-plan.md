# Delivery and acceptance plan — Stage 0

This is a staged plan, not an implementation report. Root/lead owns integration, contract review, security review and final acceptance. Two developers work in separate directories with an agreed OpenAPI/schema boundary. All scenarios are fictional and visually labeled **SYNTHETIC DATA**.

## P0 acceptance and repeatable demo

1. On a clean local setup, the backend, SQLite store, UI and selected local assistant start without a cloud service. After setup, network-disabled smoke checks cover every P0 workflow. The UI explicitly reports when the local model is unavailable.
2. Two or more fictional crew IDs remain separated. Manual entry and seeded generation round-trip through one typed observation contract. Each record exposes unit, timestamp/zone, source, synthetic flag and quality state; corrections preserve history and audit reference.
3. Four fixed-seed scenarios: normal series; gradual descriptive change; missing/corrupt/conflicting input; operator-declared urgent handoff. Re-running a seed reproduces the same events. The urgent scenario does not claim a diagnosis or clinically inferred emergency.
4. The member view shows history table and chart with equivalent data access, visible freshness/quality labels and per-alert rule/input/source explanation. Form errors are field-associated; keyboard and screen-reader operation is checked. No unexplained risk score.
5. Deterministic rules return the same categorized facts/findings/guidance/hypotheses/unknowns for the same version and inputs. No clinical threshold or advice without the evidence gate. The LLM can summarize only those results, ask for missing measurements and abstain; prompt injection and missing-source cases are exercised.
6. API, analytics, seed reproducibility, access isolation and model-failure behavior have automated checks; UI/API smoke passes offline. Run commands and observed results are recorded when Stage 13 is reached. Stage 0 has not run these checks because no application exists.

## Work sequence and dependency gates

| Stage | Deliverable and gate before next stage | Priority |
|---|---|---|
| 0 | This requirements/architecture/evidence/plan baseline; decisions and unknowns visible. | P0 foundation |
| 1 | Local project skeleton, pinned dependencies, runnable service/UI shells; Windows setup without mandatory Docker. | P0 |
| 2 | Versioned typed schema, migration, fictional-profile/observation/symptom CRUD, revision/audit design, OpenAPI examples; A/B contract freeze. | P0 |
| 3 | Seeded scenarios and import adapter boundary; quality/provenance tests. File import is staged carefully and can remain limited to a documented P0 format. | P0 |
| 4 | Connected crew selector, entry form, member history and accessible chart. | P0 |
| 5 | Versioned deterministic analytics and evidence display; review clinical-rule gate. | P0 |
| 6 | Local LLM runtime benchmark, constrained explanation, abstention and failure behavior; P0 assistant acceptance. | P0 |
| 7 | Personal statistical baseline and cautious 24 h/72 h/7 d forecasts only after sufficient data and time-aware evaluation. | P1 |
| 8 | Reviewed psychology instrument, self-reports and environment context; privacy and source checks. | P1 |
| 9 | Explicitly assumptive what-if comparison. | P1 |
| 10 | Crew aggregates, human emergency handoff and mission-readiness information without automated clearance. | P1 |
| 11 | Auditable local ground-center sync simulator with queue, retry, idempotency, acknowledgement and conflict handling. | P1 |
| 12 | UX refinement and broader accessibility validation. | P1 |
| 13 | Integrated tests, offline packaging, documentation and repeatable demonstration. Run P0 end-to-end acceptance as soon as Stage 6 is ready; do not defer P0 verification until P1 finishes. | P0/P1 closeout |

P2 (3D body, rich animation, advanced physiological simulation) is a later independent extension and cannot gate P0.

## Two-person ownership and integration

| Developer A — data/analysis | Developer B — UI/demo | Shared integration point |
|---|---|---|
| Stages 1–3: `backend/`, migrations, typed schema, API, demo seeds, validation tests. | Stage 1: `frontend/` shell and local asset build. Stage 2: consume example OpenAPI contracts and fixture responses; no backend edits. | Lead approves enum/units, UTC/offset rules, error shape and fictional-data labels after Stage 2. |
| Stages 4–6: deterministic analytics, source references, local LLM adapter, backend tests. | Stages 4–6: entry/history/chart, evidence/quality panels, assistant UX, accessibility and UI tests. | Same-origin API smoke after Stage 4; analysis result fixture and abstention states after Stage 5; offline integrated run after Stage 6. |
| Stages 7–11: P1 modules and migrations only after P0 accepted. | Corresponding P1 UI, using versioned contracts. | Lead owns end-to-end security, synchronization and demo acceptance. |

Each developer owns only their tree during parallel changes. The lead owns root configuration, documentation and cross-boundary changes; contract changes require review before either side updates code.

## Risk register and open decisions

| Risk | Impact | Mitigation / decision owner |
|---|---|---|
| Unsupported medical thresholds or urgent claims | Harmful, misleading output | P0 limits rules to quality and descriptive changes; medical expert/source gate for clinical guidance. Lead + qualified reviewer. |
| Local model hallucination or prompt injection | Unsourced advice or false reassurance | LLM receives versioned result, outputs cited explanations only; refusal tests, human escalation and no rule authority. Lead. |
| Inadequate longitudinal astronaut data | Invalid forecasts or clinical-performance claims | P1 abstention, time-aware baselines, per-dataset provenance and no synthetic clinical metrics. A + lead. |
| Real health data leakage | Privacy breach | Fictional demo, local bind, minimized logs, user data outside repo, access threat model before real data. Lead. |
| Model weight/license/runtime mismatch | P0 assistant unavailable offline | Benchmark installed model first; check license and package any chosen weights deliberately; explicit unavailable state. A + lead. |
| Docker unavailable; Python 3.11+ absent | Setup friction | Native Windows setup; choose supported Python version and pin/test dependencies in Stage 1; Docker optional. Lead. |
| Data source access/terms mismatch | Blocked import or improper redistribution | Dataset-specific source ledger and acquisition gate; NASA data are not a P0 prerequisite. Lead. |
| Undefined NASA challenge or ground protocol | Cannot claim formal compliance | Ask for exact official brief/protocol before claiming it; leave P1 sync/handoff protocol as simulator. Product owner. |

**Smallest decisions needed before the affected work:** exact official challenge brief (if compliance is expected); approved clinical protocol/reviewer (before clinical rules); policy for real health data (before non-demo use); chosen P0 metric/unit subset and retention policy (before final Stage 2 contract). Stage 1 can proceed without resolving the first three, but under the master prompt it requires a separate authorization.
