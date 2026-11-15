# ASTRA knowledge: sources, connections, risks and implementation plan

> **Historical review, superseded 2026-11-07.** Previous examples, including biological sample studies, are not included in the current scope. Current sources, cautious connections and stages: [internal/source-ledger.md](internal/source-ledger.md), [internal/reference-and-domain-notes.md](internal/reference-and-domain-notes.md), [internal/safety-and-roadmap.md](internal/safety-and-roadmap.md).

**Status:** Research registry and plan, 2026-11-07. All links below are verified for the stated thesis; "verified" means the date of review, not the publication date. If the publication date was not established, it is marked as `not established`. Content of sources is paraphrased, not copied into the curriculum. Rights to include source texts in delivery or training **are not verified**; until this verification, only links, metadata and own brief formulations are used. Data from OSDR/EDA are not loaded.

## Evidence Registry and Applicability

| ID | Primary Source; Date | What confirms for ASTRA | Does not confirm / Limitation |
|---|---|---|---|
| `E-NASA-SANS` | [NASA Human Research Roadmap: SANS](https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=105), page updated 2025; verified 07.11.2026 | Visual and structural changes; monitoring before, during and after flight with OCT and other studies | A single screen test does not set SANS |
| `E-NASA-BONE` | [NASA: bone changes](https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=77), page 2025; verified 11.07.2026 | Bone changes — a separate space risk; specific measurements are needed | Steps and complaints do not measure bone density |
| `E-NASA-MUSCLE` | [NASA: physical fitness risk](https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=180), page 2025; verified 11.07.2026 | Muscle function and physical fitness deserve a separate protocol | Self-assessment of fatigue does not measure muscle strength |
| `E-NASA-CARDIO` | [NASA: cardiovascular risk](https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=179), page 2025; verified 11.07.2026 | Context of posture and adaptation is important for cardiovascular changes | Earth-based pulse reference is not an orbital threshold |
| `E-NASA-SLEEP` | [NASA: inadequate sleep and irregular schedules](https://www.nasa.gov/reference/risk-from-inadequate-sleep-and-irregular-schedules), date n/a; verified 11.07.2026 | Sleep, schedule, and fatigue — a mission-specific risk | One sleep duration does not establish a disorder |
| `E-NASA-HYPOXIA` | [NASA: hypoxia risk](https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=173), page 2025; verified 11.07.2026 | Hypoxia risk depends on atmosphere and physiological data | One SpO₂ does not explain the cause |
| `E-NASA-CO2` | [NASA: carbon dioxide technical brief](https://www.nasa.gov/ochmo-tb-004-carbon-dioxide-2/), date n/a; verified 11.07.2026 | Atmosphere CO₂ and symptoms should be analyzed with exposure conditions | General sensor is not equal to personal dose; link with headache does not prove cause in humans |
| `E-NASA-RADIATION` | [NASA Space Radiation Analysis Group: dosimetry](https://srag.jsc.nasa.gov/spaceradiation/how/how.cfm), date n/a; verified 11.07.2026 | For exposure assessment, dosimetry, instrument, and interval are needed | Dose in the room is not equal to individual disease risk |
| `E-NASA-RENAL` | [NASA: renal stone risk](https://humanresearchroadmap.nasa.gov/risks/risk.aspx?i=81), page 2025; verified 11.07.2026 | Urinary/renal risks have separate symptoms and investigations | Pain does not confirm a stone |
| `E-NASA-BEHAVIOR` | [NASA behavioral-health risk record](https://www.nasa.gov/wp-content/uploads/2025/09/hsrb-behavioral-health-risk-record-rev-d-web-final-sd.pdf), approved 25.07.2024; verified 07.11.2026 | Behavioral state and load require separate attention | Self-assessment 0–10 is not a psychiatric diagnosis |
| `E-NASA-TEAM` | [NASA team risk](https://www.nasa.gov/directorates/esdmd/hhp/team-risk/), 11.03.2025; verified 07.11.2026 | Team interaction — separate mission risk | Does not justify collection of assessments of specific colleagues in MVP |
| `E-NASA-MISSION` | [NASA Standard Measures](https://www.nasa.gov/reference/standard-measures/), date n/a; verified 07.11.2026 | Repeated measurements pre/post/during mission | Does not set a single universal baseline |
| `E-NASA-EDA` | [NASA Environmental Data Application](https://visualization.osdr.nasa.gov/eda/), date n/a; verified 07.11.2026 | ISS telemetry of CO₂, temperatures, humidity, and radiation exists as context | Is not a medical record of a specific astronaut; do not use without verification of specific set |
| `E-NASA-NUTRITION` | [NASA Nutritional Biochemistry](https://www.nasa.gov/directorates/esdmd/hhp/nutritional-biochemistry/), date n/a; verified 07.11.2026 | Nutrition and biochemistry may be a standalone domain | Does not prove availability of any lab test onboard |
| `E-NASA-IMMUNE` | [NASA immune risk](https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=85), page 2025; verified 07.11.2026 | Immune/infectious changes — research domain | Temperature alone does not define infection |
| `E-SPACE-ANEMIA` | [Trudel et al., Nature Medicine](https://www.nature.com/articles/s41591-021-01637-7), published 2022; verified 07.11.2026 | Longitudinal study of space anemia in astronauts justifies a separate research topic | Small cohort and specific methods do not provide ASTRA with a universal threshold or diagnosis without CBC and context |
| `E-NASA-INFLIGHT` | [NASA: in-flight medical conditions](https://www.nasa.gov/directorates/esdmd/hhp/risk-of-adverse-health-outcomes-and-decrements-in-performance-due-to-inflight-medical-conditions/), date n/a; verified 07.11.2026 | Injuries and dental events belong to planning of medical care in flight | Is not a ready protocol for autonomous treatment |
| `E-NASA-SENSORIMOTOR` | [NASA sensorimotor risk](https://humanresearchroadmap.nasa.gov/risks/risk.aspx?i=88), page 2025; verified 07.11.2026 | Balance and coordination require separate testing | General activity does not replace testing |
| `E-NASA-ACOUSTICS` | [NASA acoustics/hearing risk](https://www.nasa.gov/directorates/esdmd/hhp/risk-of-hearing-loss-and-performance-decrements-due-to-acoustics-issues-in-space/), date n/a; verified 07.11.2026 | Noise and hearing — related, but separate domain | Noise complaint does not prove hearing loss |
| `E-NIDDK-GALLSTONES` | [NIH NIDDK: diagnosis of gallstones](https://www.niddk.nih.gov/health-information/digestive-diseases/gallstones/diagnosis), date n/a; verified 07.11.2026 | Pain, history, laboratory and visualization are considered together; ultrasound is necessary to find stones | Symptoms and analyses without visualization do not confirm stones |
| `E-HL7-FHIR` | [HL7 FHIR R4 Observation](https://hl7.org/fhir/R4/observation-definitions.html), version 4.0.1 (2019); verified 07.11.2026 | Method, device, sample and different contextual intervals — different fields | ASTRA does not yet implement full FHIR |
| `E-LOINC` | [LOINC User Guide](https://loinc.org/kb/users-guide/introduction), verified 07.11.2026; [license](https://loinc.org/license) | Panel and separately reported components have different identifiers | Do not import full dictionary and third-party questionnaires without checking rights |
| `E-NLM-LABS` | [MedlinePlus/NLM: understanding lab results](https://medlineplus.gov/lab-tests/how-to-understand-your-lab-results/), updated 04.09.2025; verified 07.11.2026 | Laboratory intervals depend on method/laboratory; value within interval does not prove absence of disease | Do not take universal interval from this page |
| `E-CLSI-EP28` | [CLSI EP28](https://clsi.org/shop/standards/ep28/), date n/a; verified 07.11.2026 | Establishing and verifying laboratory reference intervals require methodology | Standard does not provide ASTRA ready intervals |
| `E-PROMIS-LICENSE` | [HealthMeasures PROMIS terms](https://www.healthmeasures.net/images/PROMIS/PROMIS_Terms_and_Conditions_v8.2_08312016.pdf), 31.08.2016; [translations](https://healthmeasures.net/promis-basics/available-translations/); verified 07.11.2026 | Rights to exact text and translation of the questionnaire need to be evaluated before implementation | Current 0–10 questions ASTRA do not become a validated scale |
| `E-NASA-OSDR-TERMS` | [NASA OSDR terms](https://science.nasa.gov/reference/osdr-help-terms-and-conditions/) and [FAQ](https://science.nasa.gov/reference/osdr-faq/); publication date not established, reviewed 2026-11-07 | Datasets have separate metadata and citation terms | Hosting by NASA does not establish that a dataset contains human data or is suitable for training |

The four Earth-based sources already in use and their limitations are listed separately in the [current comparison registry](../medical-demo-evidence.md). They are insufficient to establish orbital clinical thresholds. Before loading a selected OSDR dataset, record its ID/version, species and population, variables, collection method, rights, missingness, limitations, and intended use. For example, the [OSDR FAQ](https://science.nasa.gov/reference/osdr-faq/) describes a **mouse** study; a portal title alone does not make it astronaut data.

## Four Cross-Domain Examples

| Inputs and Links | What ASTRA Can Show | What Remains Unknown |
|---|---|---|
| Right abdominal pain (`T-SYMPTOM`) + `T-CBC` component with lab flag + `T-HEPATIC` → `K-BILIARY` (`possible_association`, `E-NIDDK-GALLSTONES`) | Matched symptoms and results requiring clarification; show original reports, lab intervals, and need for examination/visualization from the source | Presence of stones, cause of pain, and significance of deviation without method/ultrasound. [NIDDK](https://www.niddk.nih.gov/health-information/digestive-diseases/gallstones/diagnosis) |
| Repeated screen test of one eye (`T-VISION-FUNCTION`) + personal series → `A-VISION-TREND` → `K-SANS` | Persistent change in function **under comparable conditions**; suggest verification and link to NASA SANS as a possible risk | Structural features of SANS without OCT/examination. [NASA](https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=105) |
| Rise in CO₂ (`T-HABITAT`, location/interval) + similar complaints from multiple people at close times (`T-SYMPTOM`) → `A-EXPOSURE-CORRELATION` → `K-CO2` | Possible common environmental factor requiring sensor and location verification | Personal exposure and proven cause of complaints. [NASA](https://www.nasa.gov/ochmo-tb-004-carbon-dioxide-2/) |
| Shortened sleep (`T-DAILY`) + increased fatigue (`T-SELFREPORT`) + workload (`X-WORKLOAD`) → `A-SLEEP-FATIGUE` → `K-SLEEP` | Joint dynamics and question about conditions/schedule | Cause of changes, psychiatric diagnosis. [NASA](https://www.nasa.gov/reference/risk-from-inadequate-sleep-and-irregular-schedules) |

In all four examples, the rules are first disabled until input data and error scenarios are checked; the names `K.*` are **reference candidates**, not clinical conclusions.

## Risks and Protection

| Risk | Observation in the current project | Measure and criterion |
|---|---|---|
| Splitting into tens of files / giant "map of diseases" | Previous plan named exactly 20 files | Add by independent method, connected panel or isolated proven risk; generate navigation index, do not assign logic |
| False comparison and anxiety | `unit` is a free line; no method, posture and phase | Code unit, control compatibility, status `not_assessed`; tests for incomparable conditions |
| Replacement of personal baseline with reference | `/baselines` takes all records | Selected series by phase/instrument, confirmation and version history; external `R.*` separately |
| Outdated or inappropriate sources | Four Earth landmarks in code | Package version, owner and review date, blocking outdated criterion, check applicability to mission |
| Unreliable model output | Experimental Ollama already gave fabricated identifier and English text | Model explains only calculation/local tolerances; verification of ID, numbers and references; calculated review as backup |
| Spurious causality | CO₂, complaints, sleep and stress may coincide | Type of connection `possible_association`, control of time/place and alternatives; no automatic diagnosis |
| Leakage of personal information | Individual GET self-assessments are still without roles; logs and small team are sensitive | Until real collection — roles, minimization, storage period, access log without values; general panel without raw self-reports and without small aggregations |
| Unreliable extrapolation of data set | OSDR contains both animal models and telemetry | Check each set before loading; synthetic cases are not considered clinical evidence |

For a small crew, even an anonymized average mood can reveal information about an individual; therefore, psychological and social responses are not shown in the general panel. This is a project measure of minimization, not a statement about the legal status of ASTRA. [HHS: residual re-identification risk](https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html) (checked 07.11.2026). Social survey in P2 is permissible only when there is clear benefit, voluntariness, role access selection, and storage duration; specific colleague evaluations are not collected.

## Migration Plan Without Interruption P0

| Step | Change | Checked Criterion |
|---|---|---|
| 0. Approve Taxonomy | Agree on available tests, introduced context and roles; existing UI/API remain | Inventory and sources have owner, status, and boundaries |
| 1. P0 Data Contract | Add optional `test_id`, `method`, `device`, `specimen`, `mission_phase`; keep old records as `context_unknown` | Migration without loss of 8 test measurements; `lab_value` is not interpreted without analyst |
| 2. Knowledge Bundle | Validated JSON, single bundle hash, registry `E/R/T`, transfer of four current criteria without changing their meaning | Old comparisons give the same result; FTS5 index is rebuilt from JSON; offline test without network |
| 3. Personal Baseline Series | `P.Assessment` and `P.BaselineSeries` with versions and selection of comparable records | Earth/orbit are not mixed; correction does not erase old version |
| 4. Space Topics P1 | Prioritized `T/K/X`, knowledge without diagnostic rule where data is missing | Each output indicates measurements, source, and missing examinations; new rules are disabled until testing |
| 5. Vision and Connections | Calibrated repeated screen test, graph, separate right/left eye; then check rules `A.*` | Screen change/distance blocks comparison; SANS is not confirmed by screen test |
| 6. Behavioral Data and P2 | Choose licensed questionnaire and role policy, then add lab panels if tests are available | No individual responses in crew dashboard; panel results are linked to components and lab intervals |

Before each activation, the rules are fixed: source and rights, population and method, input set, expected false alarms and misses, version, reviewer and boundary/missing data tests. Individual P1/P2 capabilities are not a condition for maintaining P0 functionality.

## Unresolved Solutions Requiring Minimal User Input

1. What **real data types** are planned for demonstration after manual vital measurements: visual screen test, blood/urine analysis, atmospheric data, or only their fictional examples? This determines which `T.*` transition from reference to active.
2. What device and distance will be used for the repeated vision test? Without this, it is impossible to design a comparable screen score.
3. Who can view the individual self-assessment and who approves the original series? Until roles are defined, the social block remains disabled for real people.

These answers clarify implementation priorities; they are not needed for the approval of the taxonomy itself.
