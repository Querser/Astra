# ASTRA requirements matrix — Stage 0

Status: proposed and unimplemented. Priority follows the master prompt. `A` is backend/data/analytics; `B` is UI/demo. Acceptance evidence describes a future check, not a check already passed. Every clinical rule requires a reviewed source or supplied protocol before activation.

| ID | Requirement | Priority | Dependencies | Proposed component | Acceptance evidence | Unresolved question |
|---|---|---|---|---|---|---|
| R01 | Core workflows run without internet after setup; no hosted inference at runtime | P0 | Local dependency/model acquisition | A runtime, B local assets | Network-disabled end-to-end run, including assistant | Model acquisition/redistribution terms and offline packaging? |
| R02 | Fictional crew profiles with stable IDs and separated histories | P0 | Schema, local access policy | A storage/API, B selector | CRUD tests, cross-profile isolation test | Who may inspect individual records in a real deployment? |
| R03 | Manual entry of supported vital signs, sleep/activity and symptoms, including partial input | P0 | R02, typed contracts | A ingestion/API, B forms | Round-trip tests for scalar, blood-pressure pair, symptom and missing values | Which P0 measurement types/units are essential? |
| R04 | Each observation retains unit, timestamp, source, quality and synthetic status | P0 | R03 | A contracts/storage, B history | API/schema tests and UI inspection of provenance | Retention and correction policy beyond demo? |
| R05 | Validate invalid, missing, stale, conflicting and outlier data without silent overwrite | P0 | R04, versioned rules | A validation/append-only revisions, B statuses | Boundary, conflict and revision tests; rejected-input review | Staleness window and defensible plausibility bounds per metric? |
| R06 | Deterministic, explainable findings/alerts independent of LLM | P0 | R04–R05, vetted rule scope | A analytics, B evidence panel | Same inputs produce same rule IDs, input IDs, facts and limits | Who approves any clinically consequential threshold? |
| R07 | Separate facts, findings, sourced guidance, hypotheses and unknowns | P0 | R06, source ledger | A analysis contract, B display | Contract tests and screen review for each category | Is any guidance protocol approved for P0? |
| R08 | Seeded synthetic scenarios: normal, gradual change, corrupt/missing, declared urgent | P0 | R03–R07 | A generator, B scenario switcher | Fixed seed yields same event set; synthetic labels everywhere | Which urgent workflow/protocol may be shown? |
| R09 | History, chart and accessible tabular equivalent | P0 | R02–R04 | B workspace | UI smoke plus keyboard/table inspection | Final visual design? |
| R10 | Local assistant explains precomputed analysis, asks clarification and abstains when unsupported | P0 | R06–R07, tested local model | A LLM adapter/guard, B panel | Offline tests for factual grounding, refusal/insufficient evidence and runtime failure | Which installed model meets quality/speed/safety criteria? |
| R11 | Automated tests and repeatable local setup/demo | P0 | R01–R10 | A/B tests, root integration | Fresh-machine setup instructions and offline smoke | Python target version and dependency lock choice? |
| R12 | Personal baseline and forecasts at 24 h/72 h/7 d only with sufficient data | P1 | R04–R06, time-aware evaluation | A statistics/forecasting, B uncertainty UI | Held-out rolling evaluation vs naive baselines; abstention tests | Minimum history and interval coverage by metric? |
| R13 | Brief psychological self-reports and trends | P1 | Consent/access design, instrument terms | A contracts, B private UI | Trend display, access tests, no crisis prediction | Which instrument and usage terms? |
| R14 | Environment, mission and crew-level association views | P1 | R02, environment provenance, access policy | A adapters/aggregation, B views | Group view hides individual data; associations labeled noncausal | Which sensor placement and mission metadata? |
| R15 | Transparent what-if comparison | P1 | R12/R14 or explicit noncausal model | A scenario engine, B controls | Assumptions and unsupported outputs shown | Which relationships have evidence? |
| R16 | Emergency handoff and ground-sync simulator | P1 | R06, approvals, event IDs/queue | A audit/queue, B workflow | Idempotency/retry/conflict tests and human handoff | Ground protocol, recipient, and authority? |
| R17 | 3D body and advanced physiological twin | P2 | Accepted P0/P1; validated model scope | Separate extension | Does not delay P0; explicit nonvalidated simulation label | Is there a useful, validated modeling use case? |
| R18 | Privacy, minimization, audit and protection from untrusted text | P0 foundation, broader P1 | R02–R04 | A local security/audit, B access messaging | No PHI in repo/logs; mutation audit; prompt-injection tests | Threat model and security requirements for real health data? |

## Medical interpretation gate

P0 can demonstrate data-quality flags and descriptive changes relative to a person's own observed series. Such changes do **not** establish clinical risk. No numeric disease probability, diagnosis, treatment, clearance, or clinical urgency threshold is accepted without a source, scope, validation evidence and qualified human review. The urgent demo scenario is an explicitly synthetic **operator-declared** handoff, not an inferred medical emergency.

The term “digital twin” initially means a statistical personal profile. It does not claim a validated physiological replica. Synthetic-data metrics can validate software behavior only, not clinical accuracy.
