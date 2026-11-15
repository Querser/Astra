# ASTRA: Model Analysis and Fine-tuning Plan

**Updated:** 2026-11-09. The old plan, in which LLM did not take substantive decisions, has been replaced by [ADR-003](model-led/ADR-003-model-led-analysis.md). This is a change in requirements, not a statement about completed fine-tuning.

1. Fix the coverage of the first version and the model response contract — [coverage](model-led/v1-scope.md).
2. Prepare local verifiable knowledge cards — [research package](model-led/knowledge_cards.json). Internet is not needed during the operational phase.
3. Create an independent evaluation before training — [pilot set](model-led/eval_cases.json) and [package of 240 cases for review](model-led/review_240_assessment.md). The package of 40 patterns × 6 variants does not yet replace 200–300 independently verified scenarios; external qualified review remains open.
4. Measure the initial quality of Qwen3:8b without old template responses — [pilot results](model-led/baseline-assessment.md).
5. Then prepare a labeled training corpus, perform local pilot QLoRA, test on a frozen sample, train the numerical time series model, and only after passing the evaluation connect the model path to the application.

The initial weights Qwen3 in Ollama are not equal to the trained adapter ASTRA. There is no such adapter, training corpus, and clinically validated set of metrics in the repository yet. Numerical predictions of interventions require observations of interventions and outcomes; without them, it is not possible to claim accurate dynamics of "after treatment".
