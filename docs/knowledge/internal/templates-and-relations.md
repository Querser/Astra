# Types of Internal Documents, Templates, and Relationships

**Status:** `research_only`. This is a specification for future general records, not new executable rules or personal medical record.

## Selected Types

| ID | Content | Where it exists now / later | Prohibited Mixing |
|---|---|---|---|
| `M.*` — MeasurementDefinition | What is measured; direct/manual/computed; device/method; units; time/period; quality; access class | Research Markdown → validated JSON | Test description does not contain personal value |
| `C.*` — ContextDefinition | Flight phase, compartment, suit, load, sleep/shift, location, and interval | Markdown → JSON; specific event in SQLite | Context environment is not equal to personal exposure |
| `R.*` — ReferenceGuidance | Reference to publication, population, method, unit, context, meaning, and reference constraints, status | Markdown → JSON after validation; current 4 numbers are executed only in code | Not a personal base or universal orbital norm |
| `A.*` — RuleDefinition | Inputs, quality check and compatibility, output type, version, source, `enabled` | Described in documents; executed only by validated code | Model does not create rule itself |
| `E.*` — EvidenceRecord | Author/organization, title, URL, date/version, population, supported claims, constraints, rights, date of validation | [Registry](source-ledger.md) → JSON | Do not confuse with `DataSource` of specific input |
| `L.*` — Relationship | Typed relationship between ID from source, date, and the "association/causality" flag | [Links below](#types-of-links) → JSON | Do not convert coincidence into causation |
| `P.*` — Profile, Assessment, Observation, BaselineSeries | Specific results of one person, initial series, and history of review | SQLite; in the repository only schema, no personal data | Do not store in common documents and search index |

One common document may contain several related `M.*` or `C.*`, so the number of files is not equal to the number of definitions. Currently material is stored in Markdown for review; future JSON is needed for strict field and link checking. Database table is suitable for personal temporal records; editing common medical formulations directly in SQLite is not planned. [Previous ADR](../ADR-002-knowledge-architecture.md) has only historical status.

## Minimum fields of templates

```text
M.<stable_id>
  version, title, measured_quantity, acquisition_class[1..5]
  method, device_or_procedure, onboard_evidence, access_to_ASTRA_status
  value_type, canonical_unit, observed_at_or_interval, body_site_or_location
  collection_conditions, quality_flags, source_ids, applicability, limitations

C.<stable_id>
  version, context_kind, location_or_phase, interval_start/end, origin
  relation_to_person_or_habitat, source_ids, privacy_class, limitations

R.<stable_id>
  version, measurement_id, reference_kind, value_or_no_value
  unit, population, method, device, gravity_or_mission_context
  source_ids, source_date, review_status, limitations

A.<stable_id>
  version, input_ids, required_context, quality_gate, deterministic_logic_id
  output_kind[fact|finding|hypothesis|unknown], source_ids
  rationale, validation_status, enabled=false

E.<stable_id>
  version, title, publisher, url, publication_or_update_date, checked_at
  study_population, supported_claim_ids, unsupported_inferences
  rights_status, reviewer

L.<stable_id>
  from_id, relation_type, to_id, source_ids, evidence_status
  temporal_or_spatial_condition, limitations

P.Profile  [SQLite, not a shared document]
  crew_id, profile_version, permitted_attributes, consent_or_authority
  created_at, updated_at, access_class

P.Assessment  [SQLite]
  assessment_id, crew_id, mission_phase, performed_at, recorder_role
  observation_ids, context_ids, review_status, reviewer, revision

P.Observation  [SQLite]
  observation_id, crew_id, measurement_definition_id, value_or_report
  unit, measured_at_or_start/end, entered_at, timezone_offset
  method, device, body_site_or_location, collection_conditions
  provenance_source, quality_flags, synthetic_flag, revision

P.BaselineSeries  [SQLite]
  baseline_id, crew_id, measurement_definition_id, selected_observation_ids
  mission_phase, method_and_device, selection_rule, repeat_count
  summary_method, approved_by, approved_at, version, limitations
```

`value_or_no_value` in `R.*` allows `unavailable`. No new numerical reference or threshold is introduced by this document. Measurement time and recording time are different; UTC and original offset are preserved, and for environment — averaging period and sensor location. Unit is defined by code, and displayed signature is stored separately. Correction creates a new revision; old result and based-on output remain reproducible. Fields of method and device are needed for comparability check — this approach aligns with [HL7 FHIR Observation R4](https://hl7.org/fhir/R4/observation-definitions.html) and [FHIR Provenance](https://hl7.org/fhir/R4/provenance.html) (specification 2019, verified 2026-11-07); ASTRA is not yet a FHIR-compatible system.

## Personal baseline series and primary review

Recommended primary review — `P.Profile` with minimum needed attributes + `P.Assessment` as an event + separate `P.Observation` for each eye/indicator. `P.BaselineSeries` refers to ID of selected measurements and stores flight phase, device/method, conditions, number of repetitions, calculation method, version, time, and confirming. The first record is not declared as "normal". Ground and orbital series do not overwrite each other. External `R.*` is compared separately.

## Types of links

`measured_by` (observation → definition), `contextualized_by` (observation → phase/location), `compared_with_personal` (observation → original series), `compared_with_reference` (observation → applicable benchmark), `evaluated_by` (inputs → rule), `supported_by` (claim → source), `possible_association` (observations/context → possible explanation), `requires_confirmation` (signal → missing procedure). Only a source with sufficient basis can support a causal link; the mere proximity in time does not establish it.

```text
P.Observation → quality/unit/time/method → P.BaselineSeries and applicable R.*
               → A.* → fact / descriptive finding / unknown
               → possible association + E.* → optional local explanation
               → audit: input IDs, rule and knowledge versions, record source
```

The model sees only affirmed local fragments and results of deterministic analysis; it has no authority to choose a threshold, make a diagnosis, prescribe a medication, or change a signal level. The package is currently **not connected** to the model adapter.
