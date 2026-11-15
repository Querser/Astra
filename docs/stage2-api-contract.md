# Stage 2 API contract

Status: implemented for fictional local demonstration data only. The executable contract is the generated OpenAPI document at `/openapi.json`; this page records the intended compatibility rules for the frontend and future ingestion adapters.

## Scope and safety boundary

The API persists profiles, provenance, observations, symptom text, revisions and audit identifiers. It has no alert logic, clinical reference interval, risk score, diagnosis, treatment, forecast, LLM or external synchronization. All profiles must set `fictional: true`; the API rejects an attempt to set it to false.

`POST /api/v1/data-sources` creates provenance before an observation or symptom can reference it. Source types are `manual`, `synthetic`, `import`, and `sensor`. Stage 2 neither imports files nor connects a sensor.

## Core endpoints

| Resource | Routes | Mutation rule |
|---|---|---|
| Crew profile | `POST`, `GET`, `GET /{id}`, `PATCH`, `DELETE /api/v1/crew` | Delete archives a profile; history remains. Archived profiles reject new records. |
| Data source | `POST`, `GET /api/v1/data-sources` | A source is immutable in Stage 2 so observations preserve the stated provenance. |
| Observation | `POST`, `GET`, `GET /{id}`, `PATCH`, `DELETE /api/v1/observations` | Patch creates a new revision and links both IDs. Delete records a withdrawal timestamp and reason. |
| Symptom report | `POST`, `GET`, `GET /{id}`, `PATCH`, `DELETE /api/v1/symptoms` | Uses the same revision and withdrawal semantics as observations. |
| Audit | `GET /api/v1/audit-events` | Events contain action and object identifiers, no raw health values. |

`GET /observations` and `GET /symptoms` hide withdrawn entries by default. Use `include_withdrawn=true` for an auditable history. All list endpoints have a bounded `limit`; observations and symptoms can filter by `crew_member_id`.

## Observation contract

Each `observed_at` timestamp must include an offset. The service stores the UTC instant and the original `observed_offset_minutes`; response timestamps are UTC. It does not infer or convert units.

```json
{
  "crew_member_id": "b91808d9-6e2a-4d1d-92e1-9fd32504875d",
  "metric": "heart_rate",
  "value": { "kind": "scalar", "amount": 72 },
  "unit": "bpm",
  "observed_at": "2026-11-06T14:30:00+03:00",
  "source_id": "e25e538f-dc68-4019-af03-a670d7428b76",
  "synthetic": true,
  "quality_flags": ["demo"]
}
```

Only `metric: "blood_pressure"` accepts the alternate value shape:

```json
{ "kind": "blood_pressure", "systolic": 120, "diastolic": 80 }
```

The service validates structure, finite values, timezone presence, nonblank units and known source/profile identifiers. It intentionally does not validate clinical plausibility or decide whether any measurement is concerning; that requires the Stage 5 evidence and rule review gate.

## Storage and migration

On local server startup Alembic applies `backend/migrations/versions/0001_initial_schema.py` to `~/.astra/data/astra.sqlite3` unless `ASTRA_DATA_DIR` or `ASTRA_DATABASE_URL` is set. SQLite foreign keys are enabled per connection. The database and any future real data remain outside Git.

Before a frontend starts consuming a newer API version, compare its generated or typed client against `/openapi.json`, including the fixed metric/source enums and revision fields.
