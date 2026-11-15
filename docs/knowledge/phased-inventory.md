# ASTRA Knowledge Inventory: functions define the quantity

> **Historical draft, superseded 2026-11-07.** The tables below reflect the previous intent and are not the current scope or implementation plan. In particular, all proposals for biological sample research and related `T.*`, `K.*`, `R.*`, `A.*` are excluded. Current research package and phases: [internal/README.md](internal/README.md) and [internal/safety-and-roadmap.md](internal/safety-and-roadmap.md).

**Status:** project inventory, 2026-11-07. The numbers below are **proposed entries and templates**, not already created medical records. Source links and limitations are in [registry](evidence-and-risks.md). Rules are included separately after verification; the reference card itself does not diagnose anything.

## Counting and Bases

«Content Card» — version `T.*` (test/panel definition), `K.*` (knowledge about risk or syndrome) or `X.*` (context definition). `R.*` (criteria), `A.*` (rules) and `E.*` (sources) are considered **separate utility records**, not additional medical files. Instances of personal `P.*` and interface panels are not included in the fixed count.

| Phase | `T` | `K` | `X` | Content Cards Accumulatively | Criteria `R` | Rules `A` | Sources `E` | Why |
|---|---:|---:|---:|---:|---|---|---|---|
| Minimal Base P0 | 3 | 0 | 0 | **3** | 4 existing terrestrial benchmarks | 5 existing rule IDs | 4 sources | Describes current inputs and excludes unnamed laboratory results from medical comparisons. |
| Space MVP P1 | +9 | +10 | +3 | **25** | +0 until applicability to mission is checked | +4 candidates, initially disabled | minimum +10 sources, then by link count | Nine distinguishable methods/data sets, ten separate NASA risks and three types of context. Some records are reference until observations are available. |
| Expansion P2 | +8 | +5 base candidates, +0–3 additional | +0–1 | **38–42** when passed by base candidates | by number of approved test/lab intervals | only after separate verification | by number of actually used studies and tools | Linked panels and states are added only when input, source, and support are available. |

The minimal base results in **16 different types of common records** (3+4+5+4), but only **3 content cards**, and they may be grouped into fewer JSON files. For P1, the minimum number of common records is 16+22+4+10 = **52**; this is the lower bound of metadata, **not 52 medical files**. The count does not include an undefined number of personal results and future references. For P2, a conditional estimate is given, not a quota: if a candidate does not pass the [ADR](ADR-002-knowledge-architecture.md) criteria, it is not added and the actual count decreases.

**Mandatory and conditional.** For P0, three definitions of current input types, four existing comparisons, their sources, and the separation of rules from medical knowledge are mandatory. For the first space screen, `T-VISION-FUNCTION`, `T-HABITAT` and three `X.*` are needed; ten `K.*` may be reference, but do not activate diagnostics. Input `T-OCULAR-STRUCTURE`, `T-BONE`, `T-MUSCLE`, `T-ORTHOSTATIC`, `T-DOSIMETRY`, `T-RENAL-URINE`, `T-SELFREPORT` depends on available examinations, instruments, rights, and privacy. P2 is entirely conditional. Therefore, accumulative 25 and 38–42 — **upper projected completeness of selected functions**, not the obligation to release all records before demonstrating P0.

## Content cards: fields, links and boundaries

General fields of each record: `id`, `version`, `title`, `status`, `scope`, `source_ids`, `reviewed_at`, `reviewer`, `license_status`, `applicability`, `limitations`. The table lists **additional** fields. `T` contains protocol, units, and components; `K` — features/alternatives/missing data, but not executable diagnosis; `X` — context definition. `E-*` — requirement to the source with date, population, and license check. All `K` prior to clinical review have status `research_only`.

| ID and title | Type; purpose and additional fields | Links | Source and status | Phase; special protection |
|---|---|---|---|---|
| `T-VITALS` — vital signs | `T`; pulse, pressure, SpO₂, breathing, temperature; rest/position/method/device | `R-HR`, `R-SPO2`, `R-RR`; `A-REFERENCE` | `E-NHLBI-HR`, `E-FDA-SPO2`, `E-NHS-RR`; no universal temperature threshold | P0; conditions are mandatory for interpretation |
| `T-DAILY` — sleep, activity, fatigue | `T`; sleep/active period, scale definition | `R-SLEEP`, `K-SLEEP`, `X-WORKLOAD` | `E-CDC-SLEEP`; fatigue without validated scale is descriptive | P0; text is considered untrusted input |
| `T-SYMPTOM` — complaint | `T`; time, location, duration, author's words | `K.*` through typed links | Source for specific interpretation is selected later | P0; text is considered untrusted input |
| `T-VISION-FUNCTION` — screen vision test | `T`; eye, correction, screen/calibration, distance, raw responses | `K-SANS`, `A-VISION-TREND` | `E-NASA-SANS`, [NEI](https://www.nei.nih.gov/research-and-training/research-news/latest-amd) for individual grid | P1; screen score is not equal to diagnosis |
| `T-OCULAR-STRUCURE` — ocular examination | `T`; eye, OCT/ultrasound/image, method, date | `K-SANS` | `E-NASA-SANS`; only with real result | P1 conditional; do not simulate OCT from screen test |
| `T-BONE` — bone density/structure | `T`; DXA/QCT, site, method, initial and repeat | `K-BONE` | `E-NASA-BONE`; only with examination data | P1 conditional; do not output from steps |
| `T-MUSCLE` — muscle function | `T`; strength/function test, protocol and load | `K-MUSCLE` | `E-NASA-MUSCLE`; protocol must be known | P1 conditional; do not output from fatigue |
| `T-ORTHOSTATIC` — position/cardiac response | `T`; posture, transition time, pulse, pressure, symptoms | `K-ORTHO`, `X-MISSION` | `E-NASA-CARDIO`; thresholds not defined | P1 conditionally; comparability of phases/postures |
| `T-HABITAT` — atmosphere and environment | `T`; CO₂/O₂/temperature/humidity/noise, sensor, location, interval | `K-CO2`, `K-HYPOXIA`, `X-LOCATION` | `E-NASA-EDA`, `E-NASA-CO2` | P1; environmental sensor not equal to personal exposure |
| `T-DOSIMETRY` — personal dose | `T`; dose type, unit, device, interval and location | `K-RADIATION`, `X-MISSION` | `E-NASA-RADIATION`; only during real dosimetry | P1 conditionally; do not mix dose rate and dose |
| `T-RENAL-URINE` — urine and renal data | `T`/panel; sample, method, components, laboratory/ultrasound | `K-RENAL` | `E-NASA-RENAL`; laboratory interval from report | P1 conditionally; without analyte no comparison |
| `T-SELFREPORT` — brief voluntary self-assessment | `T`; exact text of question, scale, version, consent | `K-BEHAVIOR`, `K-SLEEP`, `X-WORKLOAD` | `E-NASA-BEHAVIOR`; licenses of others' questionnaires separately | P1; individual access limited |
| `K-SANS` — neuro-ocular risk | `K`; visual changes, structural signs, alternatives, needed examinations | `T-VISION-FUNCTION`, `T-OCULAR-STRUCTURE` | `E-NASA-SANS` | P1; screen test only signals change |
| `K-BONE` — bone changes | `K`; dynamics of studies, limitations | `T-BONE`, `X-MISSION` | `E-NASA-BONE` | P1; do not predict fracture without model |
| `K-MUSCLE` — muscle deconditioning | `K`; function, load, alternatives | `T-MUSCLE`, `X-WORKLOAD` | `E-NASA-MUSCLE` | P1; fatigue is nonspecific |
| `K-ORTHO` — orthostatic changes | `K`; symptoms upon posture change, test data | `T-ORTHOSTATIC`, `T-VITALS` | `E-NASA-CARDIO` | P1; different conditions on Earth/orbit |
| `K-SLEEP` — sleep and circadian rhythm | `K`; duration, time, schedule, possible disturbances | `T-DAILY`, `T-SELFREPORT`, `X-WORKLOAD` | `E-NASA-SLEEP`, `E-CDC-SLEEP` | P1; no causal conclusion about mood |
| `K-HYPOXIA` — oxygenation | `K`; SpO₂, environment, complaints, device, alternatives | `T-VITALS`, `T-HABITAT` | `E-NASA-HYPOXIA`, `E-FDA-SPO2` | P1; low sensor does not determine cause |
| `K-CO2` — possible influence of CO₂ | `K`; temporary link between atmosphere and complaints, location | `T-HABITAT`, `T-SYMPTOM`, `X-LOCATION` | `E-NASA-CO2` | P1; link does not prove exposure/causation |
| `K-RADIATION` — radiation risk | `K`; type and dose accumulation, uncertainty | `T-DOSIMETRY`, `X-MISSION` | `E-NASA-RADIATION` | P1; risk not considered without individual dose |
| `K-RENAL` — kidney stones/urinary risks | `K`; symptoms, analyses, alternatives | `T-RENAL-URINE`, `T-SYMPTOM` | `E-NASA-RENAL` | P1; pain does not confirm a stone |
| `K-BEHAVIOR` — behavioral well-being | `K`; sleep/stress/load, support | `T-SELFREPORT`, `X-WORKLOAD` | `E-NASA-BEHAVIOR` | P1; no psychiatric conclusions |
| `X-MISSION` — phase and gravity | `X`; pre/mid/post, duration, gravity | `T.*`, `R.*`, `K.*` | NASA Standard Measures, `E-NASA-MISSION` | P1; context, not health outcome |
| `X-LOCATION` — location and interval in environment | `X`; compartment, time interval, uncertainty | `T-HABITAT`, `T-SYMPTOM` | `E-NASA-EDA` | P1; does not prove individual dose |
| `X-WORKLOAD` — schedule/load | `X`; shift, duration, period | `T-DAILY`, `K-SLEEP`, `K-BEHAVIOR` | `E-NASA-SLEEP`, `E-NASA-BEHAVIOR` | P1; store separately from self-report |
| `T-CBC` — complete blood count | `T`/panel; individual components with codes, sample, method | `K-ANEMIA`, `K-INFECTION` | `E-LOINC`, lab result and interval | P2; no universal intervals |
| `T-CHEMISTRY` — electrolytes/metabolic panel | `T`/panel; components, sample, method | `K-HYDRATION`, `K-RENAL` | `E-LOINC`, lab report | P2; do not duplicate components from CBC |
| `T-HEPATIC` — hepatic panel | `T`/panel; components and method | `K-BILIARY`, `T-SYMPTOM` | `E-LOINC`, lab report | P2; pain + deviation ≠ diagnosis |
| `T-ENDOCRINE` — selected endocrine tests | `T`/panel; only actually available analytes | `K-HYDRATION` and future records | Specific lab source is mandatory | P2 conditional; do not collect "just in case" |
| `T-NUTRITION` — nutrition/mass/hydration | `T`; period, mass method, actual diet/liquid | `K-HYDRATION`, `K-BONE` | `E-NASA-NUTRITION` | P2; sensitive data to minimum |
| `T-VESTIBULAR` — balance/coordination | `T`; protocol, phase transition, repetitions | `K-VESTIBULAR` | `E-NASA-SENSORIMOTOR` | P2; activity does not replace test |
| `T-HEARING` — hearing | `T`; method, ear, sound/period | `K-HEARING`, `T-HABITAT` | `E-NASA-ACOUSTICS` | P2; when test is available |
| `T-SKIN-WOUND` — skin/wound | `T`; localization, event, examination | `K-INJURY` | `E-NASA-INFLIGHT`; source for specific examination before activation | P2; image/text sensitive |
| `K-INFECTION` — infection assessment | `K`; symptoms, CBC, alternatives | `T-CBC`, `T-SYMPTOM` | `E-NASA-IMMUNE` + verified clinical source | P2; temperature alone does not prove infection |
| `K-ANEMIA` — hematological changes | `K`; CBC, comparison and alternatives | `T-CBC`, `X-MISSION` | `E-SPACE-ANEMIA` | P2; CBC is disabled |
| `K-HYDRATION` — hydration/nutrition | `K`; consumption, mass, lab data | `T-NUTRITION`, `T-CHEMISTRY` | `E-NASA-NUTRITION` + lab source | P2; causes are not derived from mass |
| `K-VESTIBULAR` — sensorimotor changes | `K`; balance, symptoms, phase | `T-VESTIBULAR`, `X-MISSION` | `E-NASA-SENSORIMOTOR` | P2; without validated test, reference |
| `K-INJURY` — injury/skin | `K`; event, examination, alternatives | `T-SKIN-WOUND`, `T-SYMPTOM` | `E-NASA-INFLIGHT`; source by event type is mandatory | P2; does not replace examination |
| `K-DENTAL` — dental problem | `K`; localization, symptoms, examination | future `T-DENTAL` only when input is available | `E-NASA-INFLIGHT`; protocol still to be selected | P2 conditional; do not create without input |
| `K-HEARING` — hearing changes | `K`; sound/test/symptoms | `T-HEARING`, `T-HABITAT` | `E-NASA-ACOUSTICS` | P2 conditional; do not derive from sound |
| `K-BILIARY` — possible biliary problem | `K`; localization/time of pain, lab, alternatives and needed ultrasound | `T-HEPATIC`, `T-CBC`, `T-SYMPTOM` | `E-NIDDK-GALLSTONES` | P2 conditional; blood and pain do not confirm stones |
| `X-SOCIAL` — voluntary need for support | `X`; only clear purpose, consent and storage period | `K-BEHAVIOR` as context | `E-NASA-TEAM`; rights of questionnaire to be checked | P2 conditional; do not ask about specific colleagues |

`T-DENTAL` in line `K-DENTAL` — **not an approved card of this inventory**, but potential dependency. If a real dental protocol is selected, its addition will change P2 count and require a new version of the inventory. This is better than implicitly considering a non-existent test.

## Service Records and Personal Templates

| ID / Template | Type, Fields and Relationships | Phase and Requirement |
|---|---|---|
| `P.Profile`, `P.Assessment`, `P.Observation`, `P.BaselineSeries` | Personal Templates: ID, time, source, method, conditions, relationship to original results, versions | P0 schema, P1 migration; instances are not limited by the number of cards; private |
| `R-HR`, `R-SPO2`, `R-RR`, `R-SLEEP` | Criteria: boundaries/unit/population/method/context/source; relationships with `T-*` | P0: current four conditional anchors, [registry](../medical-demo-evidence.md); not to be used outside the domain |
| `R.*` (new) | One criterion per really distinguishable combination of test, population, and method; laboratory interval may come with a personal report | P1/P2 only after source and applicability check; number is not set in advance |
| `A-QUALITY`, `A-UNIT`, `A-REFERENCE`, `A-SERIES`, `A-COINCIDENT-O2-RR` | Five existing IDs: quality, units, external reference, descriptive dynamics, coincidence SpO₂/RR; inputs and rule version | P0; engineering rule is not issued as a clinical criterion |
| `A-CONTEXT-MATCH`, `A-VISION-TREND`, `A-EXPOSURE-CORRELATION`, `A-SLEEP-FATIGUE` | Four candidates: phase/method comparability, repeated vision change, temporally-spatial coincidence of environment/complaints, joint dynamics of sleep/fatigue | P1, initially `enabled=false`; only descriptive conclusions after data verification |
| `E-NHLBI-HR`, `E-FDA-SPO2`, `E-NHS-RR`, `E-CDC-SLEEP` | Four current sources linked with `R.*` | P0; URL/date/license/population in registry |
| `E-NASA-*`, `E-LOINC` and specific clinical sources | Sources for new `T/K/R/A`; one study may support multiple records | P1/P2; minimum ten NASA/primary sources for ten P1 risks, exact number after selection |

**Cut-off Criterion:** A record is not included in the delivery only for the purpose of topic coverage. For each new ID, a separate user question, necessary inputs, or honestly stated future test, source with usage rights, verifiable relationship with other entities, and owner of update are required. If this is not fulfilled, the topic remains in the candidate list, not in the active library.
