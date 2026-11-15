# 240 Case Bundle: Results of the Review

**Date:** 2026-11-09. **Status:** prepared for independent review; **not confirmed by a clinical reviewer**.

## What was Created

- [Original Set](review_cases_240.json): 240 fictional cases, 10 directions × 4 clinical patterns × 6 conditions or measurements. Each has replicas, expected candidates, urgency, literal fact fragments, author's basis, reference to official source, and review status. The replicas of one pattern cannot be considered 240 independent clinical stories.
- [Blind Review Package](review_cases_240_blind.json): 240 replicas with opaque IDs, **without** author labels, pattern names, and model results. [ID Mapping Table](review_cases_240_blind_mapping.json) is stored separately; it should not be sent to the reviewer until the responses are submitted.
- [Structural Validator](../../backend/verify_review_cases.py) checked 240 unique IDs and texts, 40 patterns with 6 variations, presence of fact fragments in replies, references to existing local cards, HTTPS domains of official sources, and absence of verbatim copies of 24 previous pilot cases.

## Blind Machine Checks

Model `qwen2.5vl:3b` received only replies and corresponding local cards, without expected labels. [All 240 responses](review_cases_240_model_check.json) are saved. Match with author's markup: candidates **103/240**, urgency **82/240**, both fields **64/240**. [176 disagreements](review_disagreements.json) await analysis. Disagreement itself does not prove an error in either the author or the model.

Additionally, `qwen3:8b` blindly checked one example of each of the 40 patterns: candidates **18/40**, urgency **27/40**, both fields **11/40**. The two models matched on candidates in 35/40, on urgency only in 10/40. Therefore, their votes cannot be considered as independent medical opinions or grounds to automatically accept disputed labels.

## Sources and Boundaries

Acute situations rely on official materials [Red Cross](https://production.redcross.org/take-a-class/learn-fa-bleeding-life-threatening-external.html), [NICE](https://www.nice.org.uk/guidance/NG232/chapter/recommendations), [CDC](https://www.cdc.gov/food-safety/signs-symptoms/) and [NIH MedlinePlus](https://medlineplus.gov/lab-tests/pulse-oximetry/). Cosmic risks are described in [NASA Human Research Roadmap](https://humanresearchroadmap.nasa.gov/Risks/). Each case's specific reference is indicated in its record. Verification with publications was conducted at the pattern and card level, **not as individual expert review of each case**.

The current set does not meet the original criterion of "200–300 independently checked cases": there are 240 machine-checked records from 40 patterns, but no independent qualified reviewer and resolution of 176 disagreements. These 240 labels cannot be used for a claim about medical accuracy of ASTRA or as a final model exam.

## How to Close Independent Review

1. Send only `review_cases_240_blind.json` and local cards with original sources to a qualified reviewer. Author's markup and model results remain hidden.
2. Obtain for each candidate ID, urgency, cited facts, source, justification, name/qualification, and date; mark ambiguous cases.
3. Compare answers with author tags, resolve discrepancies, and correct or exclude controversial cases. Add truly new patterns, if after exclusion and merging of options there remain less than 200 independent scenarios.
4. Freeze the final version and its hash **before** training, do not transfer these cases to train/validation.
