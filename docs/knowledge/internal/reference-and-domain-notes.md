# Reference Benchmarks and Thematic Links

**Status:** `research_only`, 2026-11-07. Below are general benchmarks and acceptable questions for future analysis. This is not a diagnosis, assignment, medical clearance, anxiety thresholds in flight, or an executable protocol. Numbers already exist in `backend/app/reference_checks.py`; this page explains their origin and boundaries, not introduces new ones.

## Earth Benchmarks in the Current Demonstrator

| ID; Indicator | Code Value | Who or What the Source Applies To | What Cannot Be Concluded | Source |
|---|---|---|---|---|
| `R.heart_rate_earth`; Heart Rate | 60–10,000 `bpm` | Adult resting heart rate; `bpm` = beats per minute | No universal astronaut norm; without rest, method and flight phase, comparison is conditional | [NHLBI, How the Heart Beats](https://www.nhlbi.nih.gov/health/heart/heart-beats) |
| `R.spo2_earth`; SpO₂ | 95–100 `%` | Typical result for most healthy people during pulse oximetry | Pulse oximeter has errors; the number does not establish the cause of the symptom and does not set an orbital limit | [FDA, Pulse Oximeter Basics](https://www.fda.gov/consumers/consumer-updates/pulse-oximeter-basics) |
| `R.respiratory_rate_earth`; Respiratory Rate | 12–20 `breaths/min` | Adult at rest; number of breaths per minute | Load and method of counting change comparability; no mission threshold | [Kent Community Health NHS, Dysfunctional Breathing Pattern](https://www.kentcht.nhs.uk/leaflet/dysfunctional-breathing-pattern/) |
| `R.sleep_earth`; Sleep | At least 7 `h` per day | CDC recommendation for adults 18–60 years | A single short night does not prove a disease or future operator error | [CDC, About Sleep](https://www.cdc.gov/sleep/about/index.html/) |

Status of each `R.*`: **reference terrestrial, not validated for individual clinical decision-making in flight**. To be accepted into the future system, a method, unit, population, conditions, date, and expert assessment of applicability are needed. Current code knows the unit and source, but not all collection conditions; its output should be interpreted as conditional comparison. For pressure, temperature, vision, environment, dose, and self-assessment, there are **no numeric medical thresholds**.

## Topic Boundaries

- **Vital Signs.** Wearable [CSA Bio-Monitor](https://www.asc-csa.gc.ca/eng/sciences/bio-monitor.asp) shows technical possibility to measure multiple variables during a session. Joint changes in pulse, breathing, SpO₂, and self-feeling may justify repeated quality and condition checks; the source does not grant ASTRA the right to flow or diagnosis based on combination.
- **Vision.** [NASA SANS](https://humanresearchroadmap.nasa.gov/Risks/risk.aspx?i=105) describes repeated functional and structural evaluations. Screen-based assessment may detect change relative to a comparable baseline series, but a screen without calibration and eye exam does not confirm SANS.
- **Sleep, Fatigue, Load.** [NASA Standard Measures](https://ntrs.nasa.gov/citations/20210022783) considers repeated recordings in the context of a mission. Actigraphy, self-report, and schedule have different origins and accuracy. Joint dynamics describe load and self-feeling, but do not allow prediction of psychological crisis.
- **Atmosphere.** [NASA EDA](https://visualization.osdr.nasa.gov/eda/) contains environmental data, and [NASA CO₂ technical brief](https://www.nasa.gov/ochmo-tb-004-carbon-dioxide-2/) considers possible effects of CO₂. Coincidence of a series of environment and complaints is a reason to check location, time, device, and alternative causes, rather than proven personal exposure.
- **Radiation.** [NASA SRAG](https://srag.jsc.nasa.gov/spaceradiation/how/how.cfm) describes personal dosimeters. Recording personal dose, background from sensor environment, and immediate symptom — three different entities. Individual risk and time to illness cannot be calculated without a validated model.

## Five Examples of Future Links

All values below are **synthetic placeholders**, not demonstration of medical norms. Examples show the type of output that still requires an approved rule.

1. `P.Symptom(headache, <example_time>)` + `P.Observation(heart_rate, <example_value>, method=<example_method>)` → **fact:** two messages relate to the same time window; **unknown:** rest, repetition, cause of the symptom. The next step for the system is to request conditions, not to name a disease.
2. `P.VisionTest(<example_value>, eye=<example_eye>)` + affirmed `P.BaselineSeries` + `C.mission_phase` → **descriptive finding:** the result changed with a comparable method; **unknown:** cause. If the methods are not comparable, the output is `unknown`, not SANS.
3. `P.CabinCO2(<example_value>, location=<example_location>)` + messages of discomfort from several crew members → **hypothesis:** possible common environmental factor; **unknown:** individual exposure, sensor calibration, other explanations. A check of time and location is needed.
4. `P.SleepTiming(<example_value>)` + `P.FatigueReport(<example_value>)` + `C.workload(<example_value>)` → **descriptive finding:** coinciding dynamics of sleep, workload, and self-assessment; **unknown:** causality and subsequent events. No crisis predictions.
5. `P.PersonalDose(<example_value>, unit=<example_unit>)` + `P.CabinRadiation(<example_value>)` + complaint → **facts:** separate dose record, environment, and message; **unknown:** causal link and long-term individual risk. The system does not translate one into another without a model.

Each future output preserves the ID of input records, time window, rule version, source of the general assertion, and a separate list of unknowns. The model can explain such records locally, but does not create new medical rules.
