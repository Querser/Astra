# ASTRA Synthetic Profiles

**Updated 2026-11-08.** Five fictional profiles contain 1134 synthetic measurements from October 12 to November 7, 2026: four with 216 and one with 270 records, including two measurements per day. Four complaints and ten environmental measurements are also entirely fictional. They test the program and are not a sample for medical validation.

| Profile | Mission | Expected Output |
|---|---|---|
| Stable | ISS, orbit | No significant deviations according to available rules of significant deviations. |
| Breathing Changes | Moon, fictional sealed module | Possible hypoxemia: last SpO₂ 94%, 93%, 91%. |
| Sleep and Load Changes | Mars, fictional sealed module | Possible sleep deficit: last periods 6.5; 6; 5.5; 5 hours. |
| Elevated Pressure | ISS, orbit | Possible arterial hypertension, stage 2 range; additionally possible sleep apnea due to complaint of loud snoring, observed breathing stops and daytime sleepiness. |
| Single Drop in SpO₂ | ISS, orbit | Last eight values: 91, 98, 98, 97, 99, 98, 97, 98 %. Output: single low reading and seven subsequent values 97–99 %, without sustained decline at the end of the series. |

General information about the mission location is taken from [NASA material about the ISS](https://www.nasa.gov/missions/station/iss-research/station-science-101-research-in-microgravity-higher-faster-longer/), [NASA Moon factsheet](https://science.nasa.gov/moon/facts/) and [NASA Mars factsheet](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/mars/). They are stored in [local location catalog](../backend/reference_docs/ASTRA_MISSION_LOCATIONS.json). Temperature and humidity values of the sealed module are **made-up educational measurements**, tied to a specific profile, not published NASA readings. Personal radiation dose, real conditions of lunar/martian base and mission medical norms are unknown.

Named versions are built only based on [executable rules catalog](../backend/reference_docs/ASTRA_DEMO_DIAGNOSTIC_CANDIDATES.json). [Actions and conditional scenarios catalog](../backend/reference_docs/ASTRA_DEMO_GUIDANCE.json) contains sources and does not promise a personal numeric treatment result. [NHLBI](https://www.nhlbi.nih.gov/health/sleep-apnea/symptoms) lists used sleep apnea features and indicates that a sleep study may be required for confirmation. Earth-based pressure and sleep criteria are not validated for a specific space mission.

Test case, separate from five profiles: two pressure measurements per each of two days — 146/94, 148/95 and 151/96, 149/94 mmHg; partner report of loud snoring and breathing stops, daytime sleepiness. Two versions are expected: **hypertension and sleep apnea**. Automatic test checks exact match; additional negative variants check single day pressure and complaint with symptom denial. This is a code compliance check, not a proof of clinical accuracy.

Separate regression case of the complaint "Headache. Hit it. Bleeding, nausea" should trigger a version of possible head injury, urgency mark, actions and qualitative scenario even without numeric measurements. Negative cases ("did not hit the head", "hit the foot") should not trigger this version.

The set is defined in [demo_seed.py](../backend/app/demo_seed.py). `python -m app.demo_seed` from `backend/` adds it only to an empty database. `python -m app.demo_seed --extend-existing` idempotently extends only five known fictional profiles, without deleting other records. A 27-day series allows separately testing forecasts for 24 hours, 72 hours, and 7 days, including error on delayed points. Numerical forecast shows the expected continuation of the signal under similar dynamics, not the effect of treatment.
