# Evaluation Protocol Before Training

**Status:** Pilot engineering evaluation, 2026-11-09.

## Datasets

- `eval_cases.json`: 24 manually written fictional scenarios; do not use in the future `train` or `validation`. There are multi-turn complaints, denials, normal series, single outliers, urgent situations, and cosmic risks here.
- Further frozen control dataset: no less than 200–300 **meaningfully different** scenarios. Duplicates and simple paraphrases of one scenario are not counted. Split by people, families of conditions, and sources of formulations. The reviewer should see sources and original data, but not the model's answer.
- Time series for forecasting are evaluated by a separate dataset; these 24 dialogues do not measure numerical accuracy of the forecast.

## Testing

`python backend/evaluate_model_baseline.py` launches unmodified local Qwen3:8b via loopback Ollama. The script selects up to six cards based on local word intersection, passes them to the model, and saves the raw response, obtained IDs, urgency, and time. This is **a separate research trace**, not a working chat API. The rules `chat_engine.py` and old pre-prepared diagnostic candidates are not included in the response.

Automatic checks: correct JSON, exact match of ID set, urgency, presence/absence of specified phrases, links only to passed cards. Matching IDs does not prove a correct medical conclusion; requirements for urgency and phrasing in this set are author's preliminary markup, not yet an expert standard. The script does not check all possible dangerous fabrications in free text.

## Criteria before Training and Deployment

Break down each error by type: fact extraction, negation, episode state, search, version selection, urgency, numerical justification, repetition. Only errors for which there is verified markup should be converted into training examples. After training, compare with the original model on the same frozen dataset and separately on new scenarios. No successful demonstration is considered proof of clinical accuracy.
