# Initial Evaluation of Qwen3:8b

**Run:** 2026-11-09. Team: `python backend/evaluate_model_baseline.py`. Model: installed local `qwen3:8b`, without ASTRA adapter. Base: `knowledge_cards.json` v0.1.0-research. Set: 24 fictional scenarios v0.1.1-pilot. Full machine results: [baseline-results.json](baseline-results.json).

| Check | Result |
| --- | ---: |
| JSON parsed | 24/24 |
| Expected set of card IDs | 14/24 |
| Expected urgency | 16/24 |
| Control mentions | 19/24 |
| Forbidden phrases are absent | 24/24 |
| All used IDs were in locally found cards | 24/24 |
| Local search included all expected cards | 24/24 |
| Urgent cases were correctly marked `emergency` | 0/2 |

## Critical Errors

- The model described fontanellar blood and worsening after head trauma as serious with words, but output `prompt_review` instead of the expected `emergency` in both cases. The formulation of the response itself does not compensate for the incorrect structured urgency field.
- Stable vision, stopped bleeding, single high BP, and a single short sleep were sometimes marked by the model as relevant cards as candidates. This is a mix of **topic of conversation** and **confirmed signs of condition**.
- Abdominal pain after a side hit was incorrectly attributed to food infection, despite the mention of no food intake. During a radiological event without dosimetry, it added a head trauma card due to headache without a hit.
- In the SpO₂ series `91, 98, 98, 97, 99, 98, 97, 98` the model did not declare sustained hypoxemia, nor did it name the single value of 91%; instead, it responded that everything was normal and unexpectedly mentioned the absence of bleeding. This is an insufficient numerical justification and contamination of the response with an irrelevant card.
- During prolonged reduction of functional test, along with the muscle card, a bone card was added without bone examination. With a normal mixed profile, the list of candidates was empty, but the response still spent part of the text excluding irrelevant conditions.

## What the measurement does not prove

This is 24 cases, written by one author, without independent clinical annotation. The evaluation does not measure accuracy on new patients, on real astronauts, treatment quality, learning ability, and quality of numerical prediction. A full set of 200–300 reviewed scenarios remains necessary before making a substantive claim about quality. Do not declare 14/24 as "medical accuracy".
