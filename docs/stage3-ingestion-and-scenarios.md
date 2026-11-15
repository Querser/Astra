# Stage 3 ingestion and synthetic scenarios

Status: implemented for local, fictional demonstration data. This stage adds no clinical interpretation, threshold, alert or claim of physiological realism.

## Reproducible scenarios

`POST /api/v1/synthetic-scenarios/runs` accepts a fictional `crew_member_id`, a scenario, a non-negative `seed`, and an offset-aware `start_at`. Its default start is the fixed UTC instant `2030-01-01T00:00:00Z`, so the same scenario, seed and start produce the same `event_fingerprint`. Database IDs and provenance-source IDs are intentionally new for each run.

| Scenario | Generated output | Meaning |
|---|---|---|
| `normal` | Three explicitly synthetic scalar observations | Demonstration flow only; no assertion of clinical normality. |
| `gradual_change` | Four synthetic observations with a visible progression | Demonstration of future trend handling; no medical conclusion. |
| `missing_or_corrupt` | A quarantined ingestion record, no valid measurement | Demonstration of incomplete/corrupt data handling. |
| `operator_declared_urgent` | Synthetic observation and symptom report with `operator_declared_urgent_demo` flag | Demonstration of an operator-declared handoff. It is not inferred from values and does not diagnose an emergency. |

Every generated event has `synthetic: true`, a synthetic `DataSource`, a generator version and a scenario-run record. The generator is deterministic Python code using a local seed; it does not call a model or an external service.

## CSV adapter

`POST /api/v1/imports/csv` accepts CSV text in a JSON request. The import applies only to the one stated fictional crew profile and creates an `import` provenance source. Required CSV columns are:

```text
metric,value_kind,amount,systolic,diastolic,unit,observed_at,synthetic,quality_flags
```

`value_kind` is either `scalar` (uses `amount`) or `blood_pressure` (uses `systolic` and `diastolic`). `synthetic` must be `true` or `false`; `quality_flags` uses `|` between flags. Timestamps need timezone offsets. The parser processes at most 1,000 rows.

Rows passing the existing typed observation contract are stored with source provenance. Structural failures create an `IngestionRecord` with the filename, row number, generic reason and SHA-256 fingerprint. Quarantine records never retain the raw CSV cell values. Retrieve them using `GET /api/v1/ingestion-records` or filter by `source_id`.

Imported text is untrusted data. It cannot alter API rules, database schema, scenario behavior or clinical policy. The local import endpoint is a demo boundary; before real health data use, retention, access, encryption, consent and format controls require an approved security review.
