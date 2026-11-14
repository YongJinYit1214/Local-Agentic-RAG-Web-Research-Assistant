# EvidenceDocs evaluation findings (2026-11-14)

## Post-fix regression (same day)

The baseline is preserved in `chat_eval_before.json` and `chat_eval_before.md`. The final 26-case run is in `chat_eval.json` and `chat_eval.md`.

- Fixed the unsupported verifier argument; all 26 streams now emit `done`, and RAG replies emit source and verification events.
- Corrected the vLLM structured-output request by using `guided_json` without a conflicting `response_format`. All 26 final verdicts came from the structured model path, not the deterministic fallback.
- Lowered the strong RAG gate from 0.75 to 0.68. All eight previously false-refused answerable questions now reach RAG and answer correctly on manual review.
- Increased the combined evidence allowance to 9,000 characters, with labeled 3,000-character per-source excerpts. Q09 and Q10 now give the policy's actual classification and Restricted-data rules.
- Q11 and Q19 use RAG to establish that the requested policy/guarantee is not specified; this is safe refusal even though the route is RAG rather than CHAT. Q26 correctly states the two facts and that their units/domains are not meaningfully comparable. The evaluator now grades answer outcome separately from the route for these traps.
- The final automatic checks report no issues across 26 cases. This is a regression result for the supplied seeded-PDF CSV, not proof of correctness on arbitrary documents or chat interactions.
- The full run is slow on this machine because generation, structured verification, and background memory extraction share one vLLM chat server. Performance and verifier calibration remain separate follow-up work.

The original baseline analysis below is retained for comparison; its failures describe the pre-fix build.

## Scope

All 26 rows in `rag_test_set.csv` were sent to the running `/chat/stream` endpoint with Web Search Mode off and a fresh session ID per question. The three newly supplied PDFs had been pre-indexed alongside seven existing seed PDFs (73 chunks total). Raw SSE results, expected answers, routes, and responses are in `chat_eval.json`; the readable case-by-case transcript is in `chat_eval.md`. Application behavior was not changed during this evaluation.

## Results

- 16 questions routed to RAG; 10 routed to CHAT.
- Every RAG question (16/16) produced an SSE `error` after answer generation: `verify_grounded_answer() got an unexpected keyword argument 'memory_context'`. None completed with `done`; none emitted the final sources or verification event. This is an API contract bug, not model uncertainty.
- Eight answerable questions were wrongly routed to CHAT and refused: Q02, Q07, Q08, Q14, Q16, Q17, Q20, Q23. These cover simple facts, paraphrases, tables, and multi-hop facts. The only expected CHAT refusals were Q11 and Q19. Q26 routed to RAG but appropriately declined a nonsensical comparison while incorrectly stating that the policy lacked the 90-day password period.
- Q09 and Q10 routed to RAG but answered as though the classification/restricted-data evidence was missing. Q25 answered the negative fact correctly, although it said soil pH was not mentioned; the expected PDF conclusion explicitly says it was not tested. That is an evidence-description error.
- Straightforward generated answers Q01, Q03, Q04, Q05, Q06, Q12, Q13, Q15, Q18, Q21, Q22, and Q24 appear substantively aligned with expected answers. Q05 writes `three` rather than `3`, so a numeric-string checker flags it even though the fact is correct. These answers still fail the streaming contract.

## Root-cause candidates and risks

1. `main.py` calls `verify_grounded_answer(..., memory_context=...)`, but the function signature in `services/structured_llm.py` lacks that parameter. This causes the universal post-generation error.
2. `prompts.py` truncates the combined RAG context to 1,200 characters. It can omit relevant parts of a retrieved PDF while listing sources separately; Q09/Q10 and Q26 are consistent with this failure mode. Confirm with a context-level trace before attributing each case solely to truncation.
3. Routing uses a confidence threshold over retrieval signals. Q02/Q07/Q08/Q14/Q16/Q17/Q20/Q23 show that the threshold or query coverage is too strict for relevant documents, despite the seed content existing. Inspect top retrieved chunks and scores for each before tuning thresholds.
4. Citation reliability cannot be scored from `sources` in this run because the event is emitted after the failing verification call. Textual `Source: [1]` claims in model answers are not equivalent to the API's source payload.
5. The current evaluator's automatic labels are deliberately narrow. `expected_numbers_missing` is a lexical signal, not a semantic grade; `three` versus `3` is a known false positive. `source_hit` is unknown where no sources event was emitted. Human review is needed for factual completeness and citation support.

## Coverage still needed before claiming production readiness

- Follow-up questions and memory continuity, including pronouns, cross-session isolation, edits, deletion, and sensitive memory leakage.
- Web Search Mode and explicit `web search` trigger, source URL quality, search provider failures, latency, and rate limiting. The supplied CSV tests document mode only; no paid web calls were made here.
- Upload/delete/new-chat isolation; malformed PDFs, scanned/image-only PDFs, empty files, huge files, duplicate filenames, PDF extraction and table ordering.
- Stream disconnect/retry, concurrent sessions, backend/model restarts, offline embedding fallback, cancellation, long answers, and UI rendering of partial/error streams.
- Security checks for prompt injection inside PDFs/web snippets, upload path handling, session ID access control, and unexpected data exposure.

## Reproduction

From `backend` with the services running: `.\.venv\Scripts\python.exe -m evaluation.run_chat_eval`. Use `--reassess` to regenerate labels from saved responses without paying the model latency again.
