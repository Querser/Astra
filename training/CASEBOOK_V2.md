# ASTRA: Multi-turn Set v2 and Medical Review

**Status:** 42 fictional cases, preliminary author markup. Independent clinical review has not been conducted. The set serves engineering validation of context, denials, and urgency changes, not medical accuracy assessment.

The results of the first training and validation are recorded in [report v2](../docs/model-led/multiturn-v2-assessment-2026-11-09.md): the adapter did not pass the deployment filter.

## Composition and Split

`python training/build_casebook_v2.py` creates:

- `training/data/casebook_v2.json` — 42 cases from ten thematic groups with original dialogues, suggested ID card, urgency, answer, brief link to the source, and review status.
- `training/data/multiturn_sft_v2.jsonl` — only 32 training cases; 19 of them are multi-turn. The file does not read the old 24 and 240 control cases.
- `training/data/validation_v2.json` — ten separate scenarios, one per thematic group. All ten are multi-turn; three have the preliminary label `emergency`.
- `training/data/clinical_review_blind_v2.json` — the same original episodes without author labels and model answers. Reviewer fields are empty; they should be filled by a qualified specialist. `python training/check_clinical_review_v2.py` checks completeness and shows discrepancies, but does not automatically 'confirm' the author markup.

The split is made based on the original text of the episodes, not by random line shuffling. Several training and validation cases reflect the same medical features; ten validation cases assess transfer to alternative formulations, but they are not an independent evaluation of clinical effectiveness. The old 24 cases remain a frozen control set and are not used for epoch selection by v2.

## Scenario Basis

Signs of life-threatening external bleeding and direct pressure are aligned with [Red Cross](https://www.redcross.org/take-a-class/resources/learn-first-aid/bleeding-life-threatening-external), signs after head injury — with [NICE NG232](https://www.nice.org.uk/guidance/NG233/chapter/recommendations), severe gastrointestinal symptoms — with [CDC](https://www.cdc.gov/food-safety/signs-symptoms/), limitations of pulse oximetry and low repeated readings — with [NIH MedlinePlus](https://medlineplus.gov/lab-tests/pulse-oximetry/) and [FDA](https://www.fda.gov/medical-devices/products-and-medical-procedures/pulse-oximeters). For flight-related risks, materials from NASA on [SANS](https://www.nasa.gov/reference/risk-of-spaceflight-associated-neuro-ocular-syndrome-sans/), [bones](https://www.nasa.gov/reference/risk-of-spaceflight-induced-bone-changes/) and [sleep](https://www.nasa.gov/directorates/esdmd/hhp/risk-of-performance-decrements-and-adverse-health-outcomes-resulting-from-sleep-loss-circadian-desynchronization-and-work-overload/); for repeated blood pressure measurements — [American Heart Association](https://www.heart.org/en/health-topics/high-blood-pressure/understanding-blood-pressure-readings/monitoring-your-blood-pressure-at-home). A link and brief rationale are written for each case. The presence of the original source does not make the author's interpretation medically verified.

## Evaluation Order

1. Train on 32 cases with a short, identical format for training and testing of four local cards. Choose the number of steps only based on ten scenarios v2; keep the original model as a control in the same Transformers environment. Preliminary threshold for selecting an adapter: correct format and existing IDs in 10/10 cases, all 3/3 urgent cases marked as `emergency`, and the match between cards and urgency not worse than the original model. If both checkpoints pass, choose based on the sum of card matches and urgency on these ten cases.
2. After selecting the adapter, evaluate it once on the old 24 cases together with the original model in exactly the same format. Check separately both previous urgent cases, ungrounded IDs and free text. Threshold for moving to API: both urgent cases are marked as `emergency`, and the match of cards, urgency, and checked text details is not worse than the original model. The threshold is an engineering filter for explicit regression, not an assessment of medical accuracy.
3. Export the adapter to the local Ollama/API path only if the threshold for urgent cases and absence of regressions has been passed. After exporting, check multi-turn chat via API; results from a separate script are not equal to product testing.
4. Before declaring medical accuracy, obtain independent annotation, resolve discrepancies, create a significantly larger frozen set of different patients/scenarios, and conduct clinical error evaluation. Do not use author annotations as if they were an expert standard.
