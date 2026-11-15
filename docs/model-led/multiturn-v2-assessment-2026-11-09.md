# ASTRA: Second Experiment with Multi-Turn Cases

Check Date: 2026-11-09. Decision: Adapter Qwen3-8B v2 **is not deployed**. This is an engineering test on fictional author cases, not a clinical evaluation.

## What Was Done

42 new cases were composed across ten areas of the local knowledge base. In 29 cases, multiple replicas were included; among them, the appearance of a new dangerous sign, negations, a single measurement outlier, and comparison with a personal series were included. For each case, a preliminary response and a link to the original source were preserved. 32 cases were included in training, ten separate scenarios were left for checkpoint selection. The previous 24 and 240 cases were not included in training. There are no exact message matches between the new corpus and the previous control files.

Created `training/data/clinical_review_blind_v2.json` without author labels and model responses. The check `training/check_clinical_review_v2.py` currently reports **0/42 completed reviews**. Source descriptions have been verified, but no results have been independently confirmed by a physician. Instructions and limitations of the dataset: `training/CASEBOOK_V2.md`.

Qwen3-8B was trained locally with 4-bit QLoRA on 32 examples in two passes: 64 steps, sequence length up to 640 tokens, learning rate `2e-5`, LoRA rank 8 on `q_proj` and `v_proj`. Adapters were saved after 32 and 64 steps. Average training loss for the first eight steps: 2,009; for the last eight: 1,347. This is a training metric, not a measure of medical accuracy.

## Ten New Validation Dialogues

The base model and both adapters were run in the same Transformers environment with the same four abbreviated local cards and generation parameters. The labels are preliminary author annotations.

| Check | Base | After 32 Steps | After 64 Steps |
| --- | ---: | ---: | ---: |
| Correct JSON | 10/10 | 10/10 | 10/10 |
| Exact Card Set | 7/10 | 7/10 | 7/10 |
| Urgency Match | 6/10 | 6/10 | 6/10 |
| Emergency Cases Marked `emergency` | 2/3 | 2/3 | 2/3 |
| All IDs Taken from Provided Cards | 10/10 | 10/10 | 10/10 |

All versions rated the case of repeated vomiting and difficulty speaking after a head injury as `prompt_review`, although the author label is `emergency`. After 64 steps, the model upgraded the case with blood in stool, which has an author label of `prompt_review`, to `emergency`, and removed unnecessary urgency in the stable functional series, while simultaneously adding several extra cards. The checkpoint selection threshold (all 3/3 urgent cases and no regression) has not been reached.

## Previous 24 Frozen Cases

To evaluate the training effect, both versions were re-evaluated with **the same** short prompt and v2 cards. These numbers cannot be directly compared with the previous report on long context: the prompt and card size there are different.

| Check | Original Qwen3-8B | Adapter after 64 steps |
| --- | ---: | ---: |
| Correct JSON | 24/24 | 24/34 |
| Exact card set match | 10/24 | 10/24 |
| Urgency match | **17/24** | **15/24** |
| Urgent cases marked as `emergency` | 2/2 | 2/2 |
| Mentioned specified details | 15/24 | 18/24 |
| No specified forbidden statements | 24/24 | 23/24 |
| All IDs taken from passed cards | 24/24 | 24/24 |

Both degradation cases in urgency for the adapter relate to radiation cases: a message after an event without personal dosimetry and a registered event where the dosimetry was reduced from `prompt_review` to `routine`. In the case where a head injury was explicitly denied, the adapter violated the specified free-text restriction. Card matching did not improve. Therefore, the adapter failed the previously announced filter on the test set and was not exported to Ollama.

## Product Check and Output Limit

The working API still uses local Ollama `qwen3:8b`; the trained adapter is not loaded into it. After the experiment, a test multi-turn dialogue of six replicas passed through the actual API with the engine `local_model:qwen3:8b`; backend tests passed, `/api/v1/health` returned `ready`, interface on `127.0.0.1:5173` — HTTP 200.

The next justified step is to obtain independent annotation of 42 cases from a qualified specialist, resolve discrepancies, and expand the corpus with content-rich stories to the next training. It is not possible to convert an error relative to the author's label into a "clinical" error without such verification. For a future claim about medical accuracy, a larger frozen sample, error impact analysis, and clinical evaluation in the target environment are needed; this aligns with the [WHO guideline on the evidence base for medical AI](https://www.who.int/publications/i/item/9789240038462).

## Repetition

- Generator and corpus: `training/build_casebook_v2.py`, `training/data/casebook_v2.json`, `training/data/multiturn_sft_v2.jsonl`; SHA-256 of training JSONL: `d14e6461acf7d12d47563eac3d2dd681ed88df5ed158fc8b69f686e05cd70430`.
- Training: `training/train_qlora.py` with `--corpus training/data/mult,turn_sft_v2.jsonl --max-steps 64 --max-length 640 --learning-rate 0.00002 --save-every 32`.
- Evaluation: `training/evaluate_adapter.py --compact-v2` with files `training/data/validation_v2.json` and `docs/model-led/eval_cases.json`.
- Full responses, metrics, and adapters: `training/artifacts/qwen3-8b-v2-compact/` (ignored by Git). The original checkpoint Qwen3-8B is stored locally outside the repository in `%LOCALAPPDATA%\ASTRA\models\Qwen3-8B`.
