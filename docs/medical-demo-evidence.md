# ASTRA demo: evidence register for initial comparisons

Status: implemented as conditional educational comparisons, checked 2026-11-07. This document replaces the earlier blanket statement that no reference comparison is possible. It is **not** a mission medical protocol. No source text is copied into the model's training corpus.

| Indicator | Rule in the demo | Source and applicability | Missing context |
|---|---|---|---|
| Resting heart rate | 60–100 bpm reference for an adult at rest | [NIH NHLBI: How the Heart Beats](https://www.nhlbi.nih.gov/health/heart/heart-beats) | Rest/exertion, age, fitness, medication, personal baseline |
| SpO₂ | 95–100% is typical for most healthy people | [FDA: Pulse Oximeter Basics](https://www.fda.gov/consumers/consumer-updates/pulse-oximeter-basics) | Device type, signal quality, cabin conditions, baseline, symptoms; pulse oximetry can be inaccurate |
| Respiratory rate | 12–20 breaths/min as a relaxed adult reference | [Kent Community Health NHS: Dysfunctional Breathing Pattern](https://www.kentcht.nhs.uk/leaflet/dysfunctional-breathing-pattern/) | Rest/exertion, method of counting, symptoms, altitude/cabin conditions |
| Sleep duration | At least 7 h per day for adults 18–60 | [CDC: About Sleep](https://www.cdc.gov/sleep/about/index.html/) | Age, sleep interval, quality, mission schedule |

Temperature is left unclassified until measurement site/method is recorded. Self-rated sleep quality and fatigue lack an explicit scale. Step count lacks a measurement period. Generic laboratory values lack analyte identity and reference interval. A missing rule yields **not assessed**, not **normal**.

The comparison uses the latest current record of each metric and checks the unit exactly. Values outside a reference generate a review finding. SpO₂ and respiratory-rate entries within 30 minutes may generate a *coincident readings* finding; this does not establish causation. Suggestions are limited to checking the measurement, recording missing context, and obtaining qualified review when a real concerning reading persists. No medicine, dose, diagnosis, disease probability, fitness decision or treatment-response forecast is generated.

NASA identifies spaceflight-specific risks including [bone and muscle changes, SANS, hypoxia, sleep disruption and radiation exposure](https://www.nasa.gov/hrp/risks/). The four public Earth-oriented references above have **not** been validated as astronaut mission limits. Those topics require different inputs such as bone imaging, ocular imaging, dosimetry, cabin telemetry and repeated measurements; the current eight demo observations cannot diagnose them.

Training-data gate: source URLs and short factual rule metadata may be used for traceability. Do not scrape or train on whole medical pages without checking licenses. In particular, the MedlinePlus A.D.A.M. encyclopedia pages inspected during research explicitly prohibit AI training and related use without permission; they are excluded from the proposed corpus.
