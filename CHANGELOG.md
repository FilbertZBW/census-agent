# Changelog

Factual, one-line-per-change log. No narrative, no reasoning — see
HANDOVER.md and REFLECTION.md for that.

## 2026-08-05

- Made gemini_generate() injectable: extracted retry/backoff into new GeminiLLM class (text_to_sql.py), gemini_generate(prompt, llm=None) now delegates to (llm or _default_llm).generate(prompt). Verified: 3 unit tests green (test_clean_sql_strips_markdown_fences, test_data_table_for_maps_prefix, test_is_rate_limit_detects_429), 6 live-integration tests skipped (RUN_LIVE_TESTS unset).
- Threaded `llm=None` through select_tables, generate_sql_grounded, generate_sql, run_query_with_retry (text_to_sql.py) and synthesize_answer, resolve_followup, ask (census_agent.py); each passes llm=llm into its gemini_generate/downstream call. Verified: 3 unit tests green (test_clean_sql_strips_markdown_fences, test_data_table_for_maps_prefix, test_is_rate_limit_detects_429), 6 live-integration tests skipped (RUN_LIVE_TESTS unset).
- Added injectable conn_factory seam: extracted Snowflake connect() into _real_conn_factory() (text_to_sql.py); threaded conn_factory=None through run_query, get_table_catalog, _catalog_text, _valid_table_numbers, get_table_fields, select_tables, generate_sql, run_query_with_retry, and census_agent.ask(). generate_sql_grounded, resolve_followup, synthesize_answer left untouched (no DB access). Verified: 3 unit tests green (test_clean_sql_strips_markdown_fences, test_data_table_for_maps_prefix, test_is_rate_limit_detects_429), 6 live-integration tests skipped (RUN_LIVE_TESTS unset).
- Added conftest.py (FakeLLM, FakeCursor/FakeConn, QueuedConnFactory, fake_llm/fake_conn_factory fixtures, autouse reset_module_caches) and two zero-network tests in test_agent.py (test_rate_limited_no_network, test_full_happy_path_no_network) exercising the llm/conn_factory seams end-to-end through census_agent.ask(). Installed pytest into ./venv (was missing, not in requirements.txt). Verified under real `pytest -v`: 5 passed (3 unit + 2 new fake-based), 6 live-integration skipped (RUN_LIVE_TESTS unset), 0 failed.

## 2026-08-12

- Fixed test_rate_limited_no_network (test_agent.py): it was hitting real Snowflake because select_tables() fetches the catalog before calling the LLM, and the test only injected fake_llm, not fake_conn_factory -- so a live-Snowflake outage produced status 'sql_gen_error' with FakeLLM called 0 times instead of 'rate_limited'. Fix: inject fake_conn_factory with a scripted catalog response, and assert len(fake_llm.prompts) == 1 and fake_conn_factory.call_count == 1 so the bug fails loudly if it recurs. Verified: `python -m pytest test_agent.py -v` -> 5 passed, 6 skipped (RUN_LIVE_TESTS unset), 0.02s, no network I/O.

## 2026-08-15

- Comment-only pass on text_to_sql.py and census_agent.py: added a docstring to every function lacking one (_build_config, GeminiLLM.generate, _catalog_text, _valid_table_numbers, _clean_sql, generate_sql_grounded, _real_conn_factory, run_query, synthesize_answer, resolve_followup), block comments on previously-unexplained code (select_tables' token-validation loop, get_table_fields' label-join loop, run_query_with_retry's retry loop, both __main__ smoke-test blocks), and a per-branch comment on each of the 8 `return` statements in census_agent.ask() stating the exact condition that produces it. No logic changed. Verified: `pytest -m "not integration"` -> 5 passed, 6 skipped (RUN_LIVE_TESTS unset), 198s.

## 2026-08-18

- REFLECTION.md, "Edge cases & failure modes" section, at user's explicit request (normally frozen): reordered to lead with the silent rows[:50] truncation / missing SQL LIMIT bug and the lack of a code-level SQL safety check (previously undocumented there), merged the two clarification-loop bullets (ambiguous geographies + underspecified questions) into one, dropped the streaming bullet as least significant, kept cost & concurrency. No code changed; doc-only.