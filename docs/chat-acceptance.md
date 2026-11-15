# Acceptance of Local Dialog ASTRA

Independent checks are run on a temporary SQLite. The browser accesses Vite and FastAPI on random local ports. For each profile, 224 synthetic measurements are loaded. In a controlled run, the model's response delays the test gateway. In a live run, the request is handled by the installed Ollama with `qwen3:8b`.

| Requirement | Criterion | What is checked during acceptance |
|---|---|---|
| R1 | A1 | After sending A, switch to B. Compare the analysis table of B, messages, draft, and field availability. After completion, check the history of A through API and after reload. |
| R1, R5 | A2 | Simulate generation failure. The error record appears only for A. Reload and restore by ID do not create duplicates. |
| R1 | A3 | Alternate A/B during the request, check headers with names, different drafts, history, and pending send. Check separately single-character input and exit from restoration upon conflict HTTP 409. |
| R2 | A4 | A 'no' response to the question about vomiting is recorded with the user ID and the delivered question. The question is resolved. Also check restoration after creating a new API instance. |
| R2, R4 | A5 | After a question with two options, a single 'no' does not set the pain dynamics. The final reply in a live scenario should request clarification. |
| R3, R4 | A6 | After explicit denial of associated symptoms with qualitatively elevated pressure, Qwen asks for both values and the time of measurement. |
| R2, R4 | A7 | 'Pain is passing' requires specified clarification. Check both the Qwen response and memory state. |
| R2 | A8 | Check the difference in number, ratings, negation, and unknown, the replacement label and source of each fact, new topic, and absence of complaint records during normal rewriting. |
| R3 | A9 | Compare links to real sections for different needs, check the assembly of short 'question–answer' pair and upper input limit. |
| R4 | A10 | The numerical duration is checked separately as the recommendation duration and as a description of the event time. The preserved source and direction of time are taken into account. |
| R5 | A11 | Two controlled generations check the failure after repetition and recovery. Correlation, category, UTF-8 volume, tokens, reason for termination, repetition, absence of dialogue content, and number of attempts are compared. The model failure, connection break, timeout, truncation, format error, and budget overrun are modeled separately. |
| R1–R5 | A12 | The original six user messages are taken from the local archive for read-only use. The next eight replicas are constructed for correction, new measurement, topic change, summary, ambiguity, and "no" response. The actual engine, profile states, responses, and log are checked. |

## Results on 13 November 2026

All 12 criteria passed. An independent pytest group contains 14 successful tests. Controlled browser checks ended with code 0. After success and modeled failure, A had respectively two and four unique records. B's history was empty, the draft and overview were preserved. The controlled conflict 409 completed the request recovery.

In the original archive conversation, the sixth replica ended with a model error. In the last run, all 14 responses were obtained through the application from `local_model:qwen3:8b` on the first attempt. The log reported `stop` for each response and from 137 to 521 input tokens. Searching for original replicas in the log did not yield matches.

On the sixth step, the model took into account the explicit negation. Then it accepted the corrected pain assessment and new indications with the specified time, changed the topic, took into account new negations, and formulated the requested summary. After returning to the first topic, the ambiguous phrase caused clarification, and the one-word "no" selected from two options led to a request to choose an option. The meaning of steps 6–14 was manually verified. At times, the model repeats the user's words in the first or third person. The assessment concerns the dialogue operation and the preservation of facts in the checked scenarios.

Used `http://127.0.0.1:11434/api/chat`, `qwen3:8b`, `num_ctx=8192`, `num_predict=600`, temperature 0, `think=false`, `stream=false`. During step assembly, a UTF-8 limit of 7200 bytes was applied. Real token measurements were obtained from the Ollama field `prompt_eval_count`.

On early runs, the check rejected results due to repeated question, refusal on clarification and incorrect interpretation of negation. On subsequent runs, echo with altered punctuation, mixing of pain with BP, repetition of the same clarification when answering 'no' and unjustified mention of pressure numbers were separately identified. Fixes were rerun through the browser across the entire chain. Separately, it was found that the log was disabled upon starting Alembic. The final test checked real records of attempts after migration.

## Commands from the root of the project

```powershell
.venv\Scripts\python.exe -m pytest backend/tests/test_conversation_acceptance.py backend/tests/test_conversation_generation_acceptance.py -q
.venv\Scripts\python.exe backend/verify_chat_browser.py
.venv\Scripts\python.exe backend/verify_chat_browser.py --live --replay-db "$env:USERPROFILE\.astra\data\astra.sqlite3"
```

For the browser, Chrome and the Playwright package are required, installed via the command `npm install` in the `frontend` directory. For non-standard package location, the variable `ASTRA_PLAYWRIGHT` defines the path to it. For manual semantic checking, you can temporarily set `ASTRA_QA_INSPECT=1`. In this mode, the test outputs answers to the current console. A regular run prints only metadata. Absence of the original archive allows for a synthetic run without `--replay-db`.
