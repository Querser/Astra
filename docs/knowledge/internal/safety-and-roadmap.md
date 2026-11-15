# Safety Boundaries, Privacy and Phases

**Status:** `research_only`. Internal documents help design explainable decision support; they are not a diagnostic, treatment, medication prescription, or work access protocol. Current rules and local model do not gain authority from this text automatically.

## Excluded and Not Confirmed

The current active package does not include **blood tests, urine tests, any laboratory panels, and other biological sample analyses**. They do not have here definitions of measurement, result schemes, examples, or rules. Discussion of their potential value is permissible only in a separate future project after confirmation of methodology, equipment, rights, and medical evaluation. The inherited `Metric.LAB_VALUE` in the code — is a technical residue; it does not belong to the accepted matrix and current input interface.

Also not considered available are ASTRA: live Bio-Monitor stream, telemetry from the station or suit, personal dosimetry, OCT images, research actigraphy, and operational mission logs. For each integration, separately needed are **a specific mission and device, resolution, documented interface, fields/units, frequency, latency, gaps, quality, and on-site testing**. The public NASA archive does not confirm local integration. Screen-based vision check without calibration is not SANS diagnostics; NASA describes specialized assessments [SANS](https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=105).

Numerical benchmarks [reference notes](reference-and-domain-notes.md) relate to the general Earth population and do not become mission thresholds. When context or source is unknown, future analysis should return `unknown`/`not_assessed`, preserving the measured fact. No individual probabilities, disease progression timelines, therapy assignments, or causation claims without validated model and clinical verification.

## Risk and Required Protection

| Risk | Condition before applying real data or including a rule |
|---|---|
| Random personal "normal" | Selected comparable series, method, flight phase, conditions, repeatability, version, and confirmation; current median `/baselines` — only a description of history. |
| Instrument or context error | Keep unit, location/method, source, measurement and input time, quality flags; do not compare incompatible records. [FDA](https://www.fda.gov/consumers/consumer-updates/pulse-oximeter-basics) describes limitations of SpO₂. |
| False environmental cause | For environment, need sensor/location/interval; for human — possible time/location of exposure. Coincidence — hypothesis, not established cause. [NASA EDA](https://visualization.osdr.nasa.gov/eda/), [NASA CO₂ brief](https://www.nasa.gov/ochmo-tb-004-carbon-dioxide-2/). |
| Unauthorized access to self-reports | The current API reads individual psychological records without role-based restrictions. Until real records — roles, audit of reading, minimization of fields, storage period, and access policy; free text and small group summaries require a separate solution. [HHS](https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html) — a reference for risk of re-identification, not a conclusion about applicability of HIPAA. |
| Fabricated medical statement by the model | Only offline-packet of approved sources and deterministic rule outputs are allowed; preserve input IDs, version, and source. Check for fabricated diagnoses, medications, thresholds, forecasts, and references before any inclusion. |
| Unauthorized copying | Links and brief descriptions are acceptable for this research work; license of full text, questionnaires, images, translations, and training data is checked for each source separately. |

## Stages without arbitrary quota of "cards"

1. **Currently — documentation.** Matrix, definitions, registry, and safe examples are checked by a person. No new screens, executable medical rules, or connection of a local model to this package. The accepted record should answer a specific question, have a path of acquisition, direct source, population, boundaries, and responsible for review.
2. **Manual pilot.** Clarify forms/schemas for method, device, conditions, phase, units, and quality; select applicable core inputs from [matrix](availability.md). Store the original series separately from current records and the reference. Check privacy and permissions before collecting real self-reports. Earth comparisons should be shown as conditional references, without a diagnosis.
3. **Repeated non-invasive examinations.** When calibrating and with an approved method, add functional checks of vision, exercises, and other one-time tests for which real results are available. Comparison is done only when methods and phases are comparable; do not output structural disease from a screen test.
4. **Integration of mission data.** For each aligned device, prove a local interface and quality. Add historical import of environment/dose separately from personal observations, then check temporal/spatial links. No "universal sensor" for all ships or suits.
5. **Approved local knowledge package.** Transfer previously reviewed general records into a valid JSON with version and hash; create a local index for explanations. Conduct independent medical, engineering, privacy, and legal reviews, as well as tests for gaps, contradictions, and hallucinations. Only after this consider the inclusion of individual rules.

A new record is rejected if it duplicates an existing one, lacks a verifiable acquisition path and source, is too broad, violates rights, or promises a conclusion without sufficient data. No record is included solely to reach a file count.
