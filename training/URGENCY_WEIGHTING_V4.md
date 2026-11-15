# ASTRA: Urgency weighting v4

Experiment v3 improved the accurate selection of cards on ten delayed cases from 7/10 to 10/10, but recognized only 1/3 of the previously labeled `emergency`. The standard language-model loss averages the error across the entire response, so several tokens in the `urgency` field have a small contribution compared to `answer_ru`.

The parameter `train_qlora.py --urgency-weight 8` multiplies the loss of tokens with values `routine`, `prompt_review` or `emergency` by eight. The boundary value is searched only after the assistant's response starts in actual tokenization; training is interrupted if it is not found. The remaining tokens and response format are preserved. This is still neural network training, but the error priority is explicitly set.

The same balanced corpus v3 is used to isolate the effect of the loss function. The threshold remains unchanged: 3/3 urgent cases on ten v2, existing IDs in 10/10 and no regression of cards/urgency relative to the base model. Only the passed checkpoint can be tested on the previous 2,4 cases. This experiment does not replace an independent medical review.
