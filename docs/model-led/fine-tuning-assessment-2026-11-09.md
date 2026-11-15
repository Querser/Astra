# ASTRA: Result of Local Fine-tuning Qwen3-8B

Date: 2026-11-09. Status: engineering experiment; adapters are not connected to API and are not a medically validated model.

## What Was Trained

- Original model: Qwen/Qwen3-8B, verified by SHA-256 original checkpoint. The local Ollama `qwen3:8b` remains in the working chat.
- Method: 4-bit QLoRA (NF4), LoRA rank 8 on `q_proj` and `v_proj`, 120 consecutive steps at 512 tokens on RTX 3070 Ti Laptop 8 GB. Only assistant response tokens were trained.
- Corpus: 120 synthetic records (60 positive, 60 negative), automatically composed from 10 local cards. 24 and 240 control cases were not used in training. The corpus is not independently annotated by a clinician and contains repeated formulations.
- Average training error for the first 10 steps: 1.28; for the last 10: around 0.001. Reduction in training error indicates absorption of this small corpus, not improvement in clinical inference.

## Frozen Check on 24 Cases

All three runs below used the same cards, prompt, sampling and generation method for Transformers with 4-bit loading. This comparison is of the adapter effect; separately run Ollama uses a different stack and is presented in [readiness report](demo-readiness-2026-11-09.md).

| Metric | Base Model | 8-Step Adapter | 120-Step Adapter |
| --- | ---: | ---: | ---: |
| Valid JSON | 24/24 | 2,4/24 | 24/24 |
| Exact Card Set Match | 12/24 | 12/24 | 17/24 |
| Urgency Match | 14/24 | 14/24 | 16/24 |
| Recognized Urgent Cases | 1/2 | 1/2 | **0/2** |
| Mandatory Details in Text | 20/24 | 20/24 | 15/24 |
| No Forbidden Statements | 23/24 | 22/24 | 23/24 |
| IDs Limited to Provided Cards | 23/24 | 24/24 | 23/24 |

The most significant regression: multi-step case with gushing bleeding, the base model labeled `emergency` and selected the bleeding card, while the adapter after 120 steps responded `routine` and left the card list empty. The case with alarming signs after head trauma, both versions assessed only as `prompt_review`, although the control annotation requires `emergency`. For a stable solution of urgency these results are insufficient.

Full adapter more often leaves `candidate_ids=[]` and `routine`: this aligns with excessive absorption of template negative examples. Also, in one case it generated a non-existent ID `ASTRA.K.OXYSON`. This observation is about model outputs, not a proven error mechanism.

## Solution and Next Steps

Adapter should not be exported to Ollama and should not be included in the working chat. The current product remains suitable for controlled demonstration of fictional profiles as a research prototype; it cannot be presented as a reliable triage or medically accurate diagnosis.

To verify real improvement, diverse multi-turn examples, negations, changes in urgency, and numerical series, annotated by specific local sources and independently reviewed by medical specialists, are needed first. Training and hyperparameter tuning should be conducted on separate training and validation datasets; the final test should be frozen until experiments. Errors in missing urgent cases should be evaluated separately from overall accuracy, then the verification should be repeated in the actual API and on data similar to the target environment. For claims of medical accuracy, a broader clinical evaluation and error risk analysis will be required.

## Reproducibility

- Corpus: `training/data/pilot_sft.jsonl`, SHA-256 `285bf7565eb5063044393ad1779f3958463e624bb5a83db6b2117064bd417804`.
- Scripts: `training/build_pilot_corpus.py`, `training/train_qlora.py`, `training/evaluate_adapter.py`; package versions: `training/requirements.lock`.
- Adapters and full responses of control cases: `training/artifacts/qwen3-8b-pilot/`, `training/artifacts/qwen3-8b-120step/`; original comparative run: `training/artifacts/qwen3-8b-base-eval.json`. Artifact folder is excluded from Git.
- Original weights: `%LOCALAPPDATA%\ASTRA\models\Qwen3-8B`; hash verification: `training/verify_weights.py` and `training/qwen3-8b-weights-manifest.json`.
