# ADR-002 — Types of "Cards" and Boundaries of Medical Data in ASTRA

> **Historical project solution, replaced on 2026-11-07.** Mentions of biological sample research and stages of their inclusion below are no longer valid. Current types, source of truth on the documentation stage, and implementation boundaries are defined in [internal/README.md](internal/README.md) and [internal/templates-and-relations.md](internal/templates-and-relations.md). Old proposals are not executable protocols.

**Status:** Project solution under consideration, 2026-11-07. Does not implement a medical library and does not change the working P0.

## What was found in the project

In the code `card` — only the CSS class of the interface panel [`frontend/src/styles.css`](../../frontend/src/styles.css); there is no medical entity `Card`. [`Observation`](../../backend/app/models.py) stores the value, unit, time, source, quality, and history of corrections. [`Metric`](../../backend/app/schemas.py) is limited to ten types of data; `lab_value` does not name the analytical. [`reference_checks.py`](../../backend/app/reference_checks.py) contains four conditional terrestrial landmarks. [`GET /baselines/{crew_id}`](../../backend/app/api.py) calculates the median and MAD of all scalar records of the indicator: this is descriptive statistics, **not an endorsed personal norm**. `PsychologicalAssessment` and `EnvironmentalMeasurement` exist, but do not have a complete context schema needed for medical interpretation. `AnalysisResult` stores the version of rules and input IDs, but not yet the version of medical knowledge package.

## Definition and Taxonomy

"Card" in conversation means a convenient block of knowledge or screen. In the schema we use precise types to avoid turning personal history into a general reference book.

| Type / ID | Content | Source of Truth | Can have multiple instances? |
|---|---|---|---|
| `P.Profile`, `P.Assessment` | Minimum data of a person and associated primary examination | Personal SQLite | Yes, by people and examinations |
| `P.Observation`, `P.PanelResult`, `P.Context` | Result, complaint, self-report or context in time | Personal SQLite | Yes, without a set limit |
| `P.BaselineSeries` | Selected comparable baseline results, version, and confirmation | Personal SQLite | Yes, by person, indicator, and phase |
| `T.*` | Definition of a single test or connected panel: components, method, units, sample/specimen | Versioned common JSON | Yes, by protocols and panels |
| `R.*` | Reference or landmark with population, context, method, and source | Versioned common JSON | Yes, several per one `T.*` |
| `K.*` | Knowledge about risk/syndrome: possible signs, alternatives, needed investigations and limitations | Versioned common JSON | Yes, by evidence-based distinct topics |
| `A.*` | Executable deterministic rule, version, inputs, and allowed type of output | Code + versioned manifest | Yes, but each requires validation |
| `E.*` | Primary source, version, date of validation, rights, and applicability | Common registry JSON | Yes, one source may support different records |
| `X.*` | Mission phase definition, location, load, or voluntary context | General JSON | Yes |
| UI-card / "general overview" | Presentation of facts, findings, hypotheses, and unknowns | Calculated from listed entries | Yes; no own medical logic |

The basis for separating result, method, device, and contextual reference is [HL7 FHIR R4 Observation](https://hl7.org/fhir/R4/observation-definitions.html) (version 4.0.1, 2019; verified 2026-11-07). FHIR here serves as a guide for structure, not as a promise of full compatibility. [LOINC](https://loinc.org/kb/users-guide/introduction) differentiates individual measurable components and panels; [UCUM](https://ucum.org/) is a candidate for normalized units. Their use requires verification of exact version and license before transferring dictionaries.

Existing `DataSource` denotes the origin of a **specific record** (manual entry, import, sensor). `E.*` denotes published evidence of a **rule or reference statement**. The same Russian word "source" should not confuse these relationships in the database or interface.

## Primary Review and Personal Base

It is recommended to use **profile + associated primary review episode + individual typed results**. The profile contains only an identifier and minimal information needed for selected comparisons. The review links results of vision, blood, pressure, and other tests with date, device, method, performer, and source. Correction creates a new version of the result, not deleting the old one. From a confirmed series of comparable results, you can separately create `P.BaselineSeries`; the first single record does not automatically become one.

Earth, early orbital, and stable orbital series have different contexts and can exist simultaneously. The system shows comparison with personal series and comparison with applicable external reference **separately**. For laboratory results, the interval from a specific report with the laboratory and method is preserved; the general interval is substituted only upon confirmed compatibility. [MedlinePlus/NLM](https://medlineplus.gov/lab-tests/how-to-understand-your-lab-results/) (page update 2025-09-04; verified 2026-11-07) describes differences in intervals between laboratories; [CLSI EP28](https://clsi.org/shop/standards/ep28/) describes their establishment and verification.

### Example Schema Without Made-Up Values

```json
{
  "reference_criterion": {
    "id": "R.example", "test_id": "T.example", "kind": "reference_interval",
    "lower": null, "upper": null, "unit_ucum": null,
    "population": {"age_range": null, "relevant_physiology": null},
    "specimen_or_body_site": null, "method": null, "laboratory_id": null,
    "mission_phase": null, "source_ids": [], "validation_status": "unavailable",
    "version": "draft"
  },
  "personal_baseline": {
    "crew_member_id": "<uuid>", "test_id": "T.example", "mission_phase": "preflight",
    "device_id": null, "method": null, "conditions": {},
    "input_observation_ids": [], "sample_count": 0,
    "summary": null, "dispersion": null, "review_status": "pending", "version": 1
  },
  "current_observation": {
    "id": "<uuid>", "test_id": "T.example", "component_id": null,
    "value": null, "unit_ucum": null, "observed_at": null,
    "source_id": null, "method": null, "device_id": null,
    "specimen_or_body_site": null, "quality_flags": [], "synthetic": true
  }
}
```

`A.*` with a project analytic threshold has separate `rationale`, `source_ids`, `validation_status` and `enabled`; such a threshold is **not called** a reference interval. If the application conditions of `R.*` are unknown, the result is `reference_unavailable`, not "norm".

## Links and Data Flow

Allowed types of links: `T has_component T`, `P.Observation measured_by T`, `T applicable_reference R`, `K relevant_measurement T`, `K possible_association X/T/symptom`, `A evaluates T/P.Observation`, `R/K/A supported_by E`. Each link has a version, purpose, and source; `possible_association` never automatically becomes `causes`.

```text
raw input → schema/unit/time/method/quality validation
          → P.Observation + provenance + correction history
          → applicability of R and comparability with P.BaselineSeries
          → A.*: facts → descriptive findings → hypotheses/unknowns
          → confirmed signal for review + audit log
          → optional local K/T/E retrieval → LLM explanation
          → UI cards, charts, and links to source IDs/versions
```

The model does not select clinical thresholds, does not calculate disease risk, and does not change rule conclusions. It only sees permitted fragments of the **local** library and already calculated results. The explanation refers to the ID and version of the original measurement, rules, criteria, and source. The absence of a card means the absence of suitable knowledge in the library, not the absence of a disease.

## Representation and Single Source of Truth

The selection of the source of truth is based on the size of the assumed library and the current Python/Pydantic/SQLite stack:

| Option | Pros | Costs | Solution |
|---|---|---|---|
| Markdown as the main format | Convenient for humans | Difficult to check units, links, and field versions; text is easily mistaken for an executable rule | Only derivative documentation |
| YAML in Git | Readable and structured | Requires a new parser and careful handling of ambiguous types | Not needed for the first library |
| JSON in Git | Strict types, Pydantic validation, change review | Less convenient for long text; compensated by generating a readable page | **Authoritative common reference** |
| Only SQLite records | Convenient for searching | Harder to review and reproduce the original package; migration may mix common and personal data | Only personal records and derived index |

General definitions — structured JSON in Git, validated by schema/Pydantic; grouping of files is determined by connected domains, **not the rule of 'one card — one Markdown file'**. Clinical text and structural fields of a single record are versioned together. Reference Markdown pages and local SQLite FTS5 index are compiled from the approved JSON package and are not edited manually. The index is rebuilt by package hash; in analysis, `knowledge_bundle_hash` and versions of used records are preserved. Personal SQLite is not included in the general index. [SQLite FTS5](https://www.sqlite.org/fts5.html) (verified 2026-11-07).

Current four criteria in `reference_checks.py` remain the only working copy until migration; then they are translated into JSON and the function reads **only the approved package**, to avoid two diverging sets of numbers. A preliminary visual screening test is planned as a separate `T.*`; its change is a reason to compare repeated results and request an examination, not a basis to confirm SANS. [NASA SANS](https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=105) (verified 2026-11-07).

## When to add a record

**Include**, if there is a specific function ASTRA, distinguishable from existing data type or risk, verifiable source and usage rights, defined inputs/context, described output boundaries and responsible for updating. **Do not include**, if the record duplicates a panel or analysis, has only a nice name without inputs, relies on synthetic data as clinical evidence, lacks an applicable source or would require a non-existent examination for an active rule. The last allows for **inactive reference record** with a list of missing data.

Panel card combines clinically related tests; each component result remains a separate typed record. This avoids dozens of files for analyses and one huge 'disease card'. Disease navigation index is generated from `K.*` and does not contain its own medical rules.

## Alignment of four independent reviews

A review of space risks confirmed the priority of vision/SANS, bones, muscles, cardiovascular adaptation, sleep, atmosphere, and radiation, but pointed out the absence of many necessary examinations in ASTRA. Therefore `K.*` may explain **missing test**, and the rule based on it remains disabled. A review of measurements required separating the panel from its components, laboratory interval from personal series, method and phase from the number itself. A review of behavior separated sleep, voluntary self-assessment, and team context and identified the absence of role control over individual viewing. An independent architectural audit rejected the fixed quota of 20 files and proposed JSON as a single source of general knowledge. These proposals are summarized in [inventory](phased-inventory.md) and [risk register](evidence-and-risks.md); none of the reviews proposed to include a new diagnostic threshold without source and verification.
