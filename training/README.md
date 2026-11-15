# ASTRA: pilot fine-tuning

The new author dataset of multi-turn cases and its limitations are described in [CASEBOOK_V2.md](CASEBOOK_V2.md). It is separated from the previous pilot and was not independently annotated by a doctor.

`pilot_sft.jsonl` contains 120 automatically composed **synthetic** examples of behavior based on local cards. It does not contain 24 pilot and 240 new control cases. Repetition of phrases and the absence of clinical review limit its application: suitable for checking QLoRA technique and response format, but not for claiming medical accuracy.

Historical training and evaluation JSONL/JSON cases retain their original Russian
dialogue and labels to preserve reproducibility. They are research artifacts, not
runtime instructions. The deployed assistant prompts and knowledge cards are in
English, while its input layer continues to understand Russian.

`train_qlora.py` runs a short LoRA/QLoRA pilot `Qwen/Qwen3-8B` with 4-bit weights, rank 8, one example per batch, and memory consumption control. The compressed model copy in Ollama is not a trainable checkpoint; original weights are downloaded separately. The adapter is saved with status `not_validated_not_deployed` and is not connected to the API without comparison on a frozen sample.

On the current PC, RTX 3070 Ti Laptop has 8 GB VRAM. If 8B does not fit even at 512 tokens, further work requires reducing the model or using a more powerful graphics card; memory error does not mean that the model is trained.

Current standalone Windows environment: `%LOCALAPPDATA%\ASTRA\training_env`; exact versions are recorded in [requirements.lock](requirements.lock). CUDA PyTorch is installed from the official PyTorch index. Original Qwen3:8B checkpoint is stored outside OneDrive in `%LOCALAPPDATA%\ASTRA\models\Qwen3-8B`. For a local file, run `python training/train_qlora.py --model <full path to Qwen3-8B>`. The script does not connect the adapter to ASTRA.

After the technical pilot: compare the old and new model on 24 cases and on a **truly independently reviewed** dataset, check separately for urgency misses, made-up facts, quality of numerical analysis, and repeated responses. Do not mix control cases with training and declare successful loss reduction as proof of medical accuracy.

**Threshold for connecting to the working chat:** compare the base model and adapter in the same engine, with identical cards, prompts, and generation parameters. The adapter must handle all 24 responses, not miss both urgent control cases, not degrade the accuracy of cards and urgency relative to the base model in this same environment, and not degrade the handling of normal and negative scenarios. Separately, the target Ollama/API path needs to be checked after exporting. These 24 cases are too small for a medical statement; the threshold only prevents obvious regression in the demo. The adapter failed this threshold after 120 steps (**0/2 urgent cases**), so it remains a research artifact.
