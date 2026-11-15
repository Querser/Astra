# ASTRA: balanced training curriculum v3

Status: engineering experiment on the same author annotation v2. External medical review is still not completed; repeating examples does not increase the number of independent cases.

`python training/build_balanced_curriculum_v3.py` takes only 32 training episodes v2 and creates 72 presentations: 24 for `routine`, `prompt_review` and `emergency`. All original episodes are preserved; rare classes are repeated more often. New ten validation and previous 24/240 cases are not read by the script. Repetitions are marked by fields `curriculum.urgency` and `curriculum.repeat`.

The experiment uses QLoRA rank 8, learning rate `4e-5` and trains `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`. Checkpoints are saved after 36 and 72 steps. Selection is allowed only based on already frozen ten cases v2: mandatory 3/3 `emergency`, existing IDs in 10/10 and absence of degradation in card accuracy and urgency relative to the original model. After selection, testing is required on previous 24 cases according to criteria from [CASEBOOK_V2.md](CASEBOOK_V2.md). Failure of any filter means `not_deployed`.

This experiment checks the impact of class balance and LoRA coverage. It does not fix the absence of independent annotation, small coverage of states, or dependence of training examples on the same ten cards.
