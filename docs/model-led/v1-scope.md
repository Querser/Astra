# ASTRA: model version coverage 1

**Status:** Research coverage as of 2026-11-09. Cards in `knowledge_cards.json` are not connected to the product and are not an approved medical protocol.

## Priority 0: urgent messages

| Situation | Minimum Inputs | Acceptable Output |
| --- | --- | --- |
| External bleeding | location of the wound, nature/continuation of bleeding, already performed actions | Possible dangerous bleeding; immediate next step and change of urgency upon new facts |
| Head impact | time and mechanism, headache, dizziness, vomiting, consciousness, anticoagulants | Possible head injury/trauma, differentiation of denials and unknown |
| Dyspnea and low SpO₂ | symptoms, series of measurements, signal quality, environmental conditions | Possible hypoxemia and reasons for clarification, without diagnosis reasons based on one sensor |
| Pain after suspicious food | time, location/character of pain, stool, vomiting, temperature, possibility to drink | Possible foodborne infection, alternatives and clarifications |

## Priority 1: flight-specific features

| Risk | Available for prototype inputs | Output Boundary |
| --- | --- | --- |
| SANS and visual changes | repeated screen tests, complaints, baseline series | Detect deterioration relative to self; screen test itself does not confirm SANS |
| Musculoskeletal changes | mission, training, functional tests, personal baseline series | Risk of reduced function; steps/complaints do not measure bone density |
| Radiation exposure | personal/ambient dosimetry, mission events | Exposure and necessity for verification; dose cannot be guessed from nonspecific symptoms |
| Sleep and circadian rhythm | duration/quality of sleep, schedule, daytime sleepiness | Persistent sleep deficit or shift; do not prescribe medication |
| Cardiovascular adaptation | serial BP/pulse, body position, mission phase, personal series | Describe dynamics and Earth references with indication of measurement conditions |
| Atmosphere and CO₂ | environmental sensor, symptoms, time/place | Compatibility of symptoms with exposure; one complaint does not measure CO₂ |

## Priority 2

Abdomen, limbs, urinary symptoms, infectious complaints, mental state and other frequent reports are added by separate validated cards. Presence of a word in free text does not mean that the condition is already supported.

## Data Rules

- `unknown`, negation and absence of measurement — different states.
- For a normal profile, the list of diseases is empty. One single anomaly is described separately from a persistent trend.
- Personal baseline and measurement method are preserved per person and mission phase. Earth ranges are not declared as the norm for a specific astronaut.
- The forecast shows the horizon, baseline points, model error on an independent sample, and uncertainty interval. Treatment and "what if" are quantitatively modeled only after training on intervention and outcome data.
- Sources are available as a local registry for audit; during application runtime, the network is not used.

## Coverage Basis

NASA: https://www.nasa.gov/hrp/risks/ and https://www.nasa.gov/hhp/human-system-risks/; NASA Human Research Roadmap: https://humanresearchroadmap.nasa.gov/Risks/. For acute situations, the CDC, NICE, NIH, and Red Cross cards are used. The source for each specific card is indicated separately.
