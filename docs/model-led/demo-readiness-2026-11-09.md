# ASTRA: Readiness for Display and Medical Accuracy Boundaries

**Verified on 2026-11-09.** This is a snapshot of the current product and started training pilot, not a conclusion about clinical suitability.

| Area | What was checked | Conclusion |
| --- | --- | --- |
| Local Demonstration | Backend tests passed, `npm run build` successfully builds UI; local smoke run passed six replicas through API and Qwen3:8b. Re-check after training: API `/api/v1/health` returned `ready`, interface on `127.0.0.1:5173` — HTTP 200. | Suitable for controlled display of fictional profiles and chat. |
| Actual Model Role | `smart_chat.py` calls Qwen3:8b, but candidates and numerical forecasts are prepared by code; in case of failure, it responds via `chat_engine.py`. | Model is connected, but it does not yet guide the entire analytics; ADR-003 — direction, not yet implementation. |
| Model Output Quality | On 24 fictional cases, the model without old templates selected expected cards 14/24, urgency 16/24, `emergency` 0/2. | Cannot demonstrate it as a reliable sorting of dangerous cases. |
| Knowledge Base | 10 local research cards with primary sources; a package of 240 fictional records was composed from 40 patterns × 6 variants. | Coverage is narrow; 240 cases do not have independent clinical reviews. |
| Forecasts | Current API works with statistical forecasts of measurements; there is no trained numerical model or data on intervention outcomes. | Can be shown as an exploratory assessment of signal dynamics; cannot claim accuracy of treatment scenarios. |
| Fine-tuning | QLoRA for Qwen3-8B passed 120 synthetic examples. In the same Transformers environment, the original model got 12/24 on cards, 14/24 on urgency, 1/2 on urgent cases; adapter — 17/24, 16/24 and 0/2 respectively. | Part of regular responses improved, but urgent case with bleeding became mistakenly labeled as `routine`. Adapter is not connected. Details: [Fine-tuning Assessment Report](fine-tuning-assessment-2026-11-09.md). |
| Multiturn Training v2 | 42 new author cases were prepared, including 29 multiturn; 32 were used in QLoRA, 10 were held back. In the same short format on previous 24 cases, the original model got 10/24 on cards and 17/24 on urgency, adapter — 10/24 and 15/24. External medical review: 0/42. | Second adapter is also not connected: no improvements in cards, urgency worsened. Details: [v2 Report](multiturn-v2-assessment-2026-11-09.md). |
| Class balance and weighted urgency | V3 balanced 72 prompts, V4 increased the contribution of urgency token. On ten deferred cases, the best card result — 10/10, but only 1/3 `emergency` was recognized versus 2/3 by the original model. | Both adapters were rejected; synthetic retraining on the same 32 scenarios was halted. [Report v3/v4](curriculum-v3-v4-assessment-2026-11-09.md). |

## How to show honestly

Use only marked fictional profiles; check autonomous Ollama run in advance; show a normal series, change in metric, and multi-turn complaint. Explain where model output, where statistical calculation, and where local knowledge card. Do not claim that the product confirms a diagnosed condition or predicts the effect of a treatment course. For accuracy questions, show real results of the control run, including errors.

## What is needed for a justified claim of medical accuracy

Need independent qualified reviewers and a source of truth for each test; sufficient number of really different cases and patients; frozen samples without leakage from training; pre-announced metrics for each condition and urgency with confidence intervals; testing on target population data and mission conditions; separate results for predictions and for advice; analysis of harm of errors and clinical evaluation. These requirements align with the WHO approach to developing evidence base for medical AI: https://www.who.int/publications/i/item/9789240038462. Synthetic dataset and reduction of training loss do not replace such verification.
