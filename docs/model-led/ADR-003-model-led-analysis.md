# ADR-003: model manages the content analysis of ASTRA

**Date:** 2026-11-09. **Status:** adopted as a development direction; integration and fine-tuning are not yet completed.

## Reason

The current chat invokes local `qwen3:8b`, but `smart_chat.py` first selects a topic from a small list, `analytics.py` determines findings, `diagnostic_candidates.py` outputs candidates, and `forecasting.py` calculates forecasts. If the model is unavailable, `chat_engine.py` returns a ready response. Therefore, the fact of invoking LLM does not mean that it directs the analysis.

## Solution

1. A unified local model orchestrator receives the current episode history, measurements, personal baseline series, mission context, and found **locally** knowledge cards. It selects essential facts, formulates differential versions, explanations, questions, actions, and final response. One complaint may relate to several conditions; the choice is not limited to four topics.
2. A neural network time series model is responsible for numerical forecasts. The orchestrator decides whether a forecast is needed and explains its applicability. Intervention scenarios receive numerical effects only when there are data on interventions and outcomes.
3. The code handles input, storage, local search, units, time, format, link reference control to existing knowledge records, audit and validation of physically impossible values. It does not replace substantive decision-making with a ready diagnosis. An emergency rule may only immediately draw attention to a person in the case of an obvious threat and does not declare a diagnosis.
4. In case of model failure, the interface reports the unavailability of analysis and saves the message for reprocessing; it does not output a model's output as a template. The model's output is marked with the version of weights, knowledge base, and used record IDs.
5. During the research phase, existing APIs and rules are preserved. Their replacement occurs after independent evaluation and integration tests; this ADR by itself does not mean that the new path is already working.

## Requirements Hierarchy

The latest requirement from the project owner regarding the leading role of the model replaces earlier project constraints about the prohibition of diagnostic versions of the model and the mandatory deterministic analytical core as the sole source of inference, as well as contradictory statements in `docs/model-training-plan.md`. The requirement for autonomous operation and the prohibition of unjustified claims remain. The application remains an educational prototype: a specific disease may be referred to as **preliminary version** with evidence, and clinical accuracy or treatment effect is not claimed without independent verification.

## Future Response Contract

Mandatory fields: `episode_id`, `facts` (value, time, source, negation), `candidates` (ID of state, facts for/against, degree of certainty), `missing_questions`, `urgency`, `immediate_actions` (ID of local basis), `forecast` (horizon, model, interval, applicability), `answer_ru`, `knowledge_ids`, `model_version`. Fabricated measurements, references to non-existent cards, and confirmed diagnosis without confirmation are prohibited. An empty list of candidates is allowed in a normal profile.

## Solution Verification

Before switching the product, compare the current stack and model candidate on a single immutable dataset: understanding of new facts in the course of the dialogue, negations, justification of a specific name, non-fabricated actions, absence of repetitions, numerical error in the forecast, and operation without a network. Deployment is not considered complete based on a single successful example.
