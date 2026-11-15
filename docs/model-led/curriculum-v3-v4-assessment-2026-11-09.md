# ASTRA: experiments v3 and v4 with urgency

Date: 2026-11-09. Decision: both adapters remain research artifacts and are not connected to the product.

## Hypothesis Under Test

In v2 corpus there were 21 `routine`, 7 `prompt_review` and 4 `emergency`. V3 checked whether errors of urgency were caused by class imbalance and too narrow LoRA. The script `training/build_balanced_curriculum_v3.py` created 72 presentations of the same 32 training scenarios: 24 of each class. These are controlled repetitions, not new independent cases. LoRA rank 8 trained all main projections (`q/k/v/o`, `gate/up/down`) with learning rate `4e-5`; checkpoints were saved after 36 and 72 steps.

V4 used the same data, order, model and parameters, but multiplied the loss token value `urgency` by eight. The goal is to check whether the critical field is lost in the overall language loss of long responses. The implementation stops training if the token value is not found in the assistant's response part.

## Ten Deferred Author Cases

| Model | Exact Card Set | Urgency Match | Urgent Cases | Grounded ID |
| --- | ---: | ---: | ---: | ---: |
| Original Qwen3-8B | 7/10 | 6/10 | 2/3 | 10/10 |
| V3, 36 steps | 9/10 | 7/10 | **1/3** | 10/10 |
| V3, 72 steps | **10/10** | 7/10 | **1/3** | 10/10 |
| V4, 36 steps | 8/10 | 7/10 | **1/3** | 10/10 |
| V4, 72 steps | 9/10 | 6/10 | **1/3** | 10/10 |

V3 learned to select thematic cards more accurately, but became worse at recognizing `emergency`. Both of its checkpoints missed head trauma with vomiting/repeated speech disorder and repeated SpO₂ 90–87% with marked dyspnea. V4 did not fix these two misses. On step 72, it also returned an extra card in one ordinary functional case and did not improve overall urgency.

The preliminary threshold required 3/3 urgent, existing IDs in 10/10 and absence of deterioration of cards and urgency relative to the original model. None of the checkpoint thresholds were passed. Therefore, v3/v4 were not tested on the old 24 cases as candidates for deployment and were not exported to Ollama. Previously, v3 without weighting was still run on the previous 24 cases: 10/24 cards without improvement, urgency 15/24 versus 17/24 of the original model in the same format; this further confirms the decision to not deploy.

## Conclusion for Next Work

Class imbalance was not the only cause of errors. Repeating 32 author's plots improved recognition of themes, but did not form a stable boundary of urgency. Increasing loss of one token redistributed errors, without eliminating dangerous misses. Continuing synthetic epochs on these same cases is not advisable: this would increase memorization without new clinical differences.

The next iteration of training requires external validation of labeling and new independent contrasting episodes: same condition with different urgency; same complaint with denial/confirmation of red flag; change of urgency in the next utterance; different methods and quality of measurements. Until such data is obtained, the working version remains local `qwen3:8b` with existing product limitations.

## Artifacts

- V3: `training/data/multiturn_sft_v3_balanced.jsonl`, SHA-256 `eb6ad32a7ef0cbf6ce723ecc0c19a864066b634a663504b53eb2a1f07ce077a1`; description — `training/CURRICULUM_V3.md`; adapters and responses — `training/artifacts/qwen3-8b-v3-balanced/`.
- V4: implementation — `training/train_qlora.py --urgency-weight 8`; description — `training/URGENCY_WEIGHTING_V4.md`; adapters and responses — `training/artifacts/qwen3-8b-v4-urgency-weighted/`.
- Both artifact directories are excluded from Git and have status `not_validated_not_deployed` in training metadata.
