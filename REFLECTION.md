# Reflection

## Overview

The goal was a production-flavored natural-language interface to the US Census
data on Snowflake: type a question, get a trustworthy answer in seconds, with
sensible behavior on bad or malicious inputs. Below are the decisions I'm
happiest with and the tradeoffs behind them.

## Development process

I built in vertical slices, validating each against ground truth before moving
on: (1) a bare Snowflake + Gemini connection smoke test; (2) single-table
text-to-SQL; (3) dynamic grounding across all 364 tables; (4) the orchestration
pipeline with guardrails and graceful degradation; (5) the Streamlit UI and
multi-turn context; (6) tests; (7) a clean cloud deploy. Checking results
against known figures (e.g. California's population) at each step is what
surfaced the join fan-out bug early.

I used AI coding tools heavily throughout -- to scaffold boilerplate, draft the
SQL-generation prompts, and reason about census-table semantics -- while keeping
the architecture, correctness checks, and prompt design under my own review.
The highest-leverage use was fast iteration on the grounding prompts and quickly
diagnosing the fan-out bug.

## Key design decisions

**1. Dynamic two-stage grounding instead of a hard-coded schema.**
The dataset has 364 tables. Hard-coding one table's columns would have been
quick but brittle and narrow. Instead I ground the model in the *live* catalog:
Stage 1 picks the relevant table(s) from the real 364-row catalog, and Stage 2
writes SQL using those tables' real field codes fetched from the metadata table.
This scales to the whole dataset while keeping each prompt small and specific,
which also helps latency and accuracy.

**2. Model choice: predictable latency over raw capability.**
`gemini-2.5-flash` returned 404 (retired for new accounts). `gemini-3-flash-preview`
honored `thinking_budget=0` inconsistently -- the same off-topic call ranged from
0.6s to 24s, which is unacceptable for an interactive UI. I settled on
`gemini-flash-lite-latest` with thinking disabled: every call is a consistent
2-4s, and because the grounding prompt does the heavy lifting, SQL quality stays
high. This is a deliberate latency-vs-capability tradeoff in favor of a
responsive product.

**3. Guardrail fused into retrieval.**
The same Stage-1 call that selects tables also returns `OFF_TOPIC` for non-US,
non-census, or injection-style inputs. Bad inputs are refused in ~0.5s with no
SQL generated and no database hit -- cheap and safe.

**4. Self-healing SQL.**
When Snowflake rejects a query, the error is fed back to the model for one
corrective retry. This turns many transient generation mistakes into successful
answers without any user involvement.

**5. Correctness and honesty.**

- *Fan-out bug:* my first county-name join matched on state FIPS alone, which --
  because the FIPS metadata table has one row per county -- inflated state totals
  ~58x. I caught it by validating California's population against the known
  figure (39,283,497) and fixed it with a "don't join for state totals" rule.
- *Medians:* block-group medians cannot be aggregated exactly. I approximate them
  with a universe-matched weighted average, always alias the column
  `APPROXIMATE_...`, and have the answer step explicitly flag the figure as an
  approximation.
- *Per-capita income*, by contrast, *is* exactly recoverable as a
  population-weighted average, so it is deliberately **not** labeled approximate.
  Being precise about what is and isn't exact matters for user trust.

## Challenges

- Model churn and inconsistent "thinking" behavior made latency the hardest thing to tame.
- Snowflake identifiers are case-sensitive in this dataset, so every table and column must be double-quoted.
- The subtle line between exact and approximate aggregations required real domain reasoning, not just prompt tweaking.

## Testing strategy

I chose a two-layer strategy that trades exhaustive coverage for confidence in
the parts most likely to break:

- *Unit tests* (no network, always run) cover the pure, deterministic logic: the table-number -> data-table mapping, SQL fence-stripping, and rate-limit detection. They are fast and pin down the helpers that would silently corrupt everything downstream if wrong.
- *Integration tests* (live, gated behind `RUN_LIVE_TESTS=1`) run the full pipeline against Snowflake + Gemini and assert on known-good numbers (California = 39,283,497; Harris County is Texas's largest), plausible ranges (per-capita income), the guardrail (non-US -> off-topic; injection -> refused), and the <60s latency budget.

The gate keeps the suite runnable on a machine without credentials while still
exercising the real system on demand. The main tradeoff: the integration tests
depend on live services and an LLM, so they are slower (~40s) and sensitive to
model nondeterminism -- I mitigated that by asserting exact values only where
the data is deterministic, and ranges / behaviors elsewhere.

With more time I'd add: a golden-question eval set with expected values run in
CI; mocked-LLM tests for the orchestration branches (no network); tests that
force each degradation path (SQL error, empty result, rate limit); and a check
that every generated statement is read-only.

## Edge cases & failure modes I did not fully address

- *Ambiguous / sub-county geographies:* the data is keyed to states, counties, and block groups, so a city or ambiguous place like "Springfield" cannot be resolved cleanly; the agent currently falls back to the guardrail / empty-result path rather than asking a clarifying question.
- *Underspecified or conflicting questions:* there is no explicit clarification turn yet -- the agent makes a best-effort interpretation instead of asking the user to disambiguate.
- *Trend / multi-year questions:* only the 2019 ACS snapshot is wired in, so "change over time" questions are out of scope.
- *Cost & concurrency:* each turn makes 2-3 Gemini calls and opens a fresh Snowflake connection; I did not add connection pooling, caching of repeated questions, or per-user rate limiting.
- *Streaming:* responses are fast enough that I show a spinner rather than token streaming; under a slow model this would still block (up to the 60s budget) with no incremental output.
- *Answer verification:* the synthesis step is instructed to use only the SQL result, but I do not programmatically verify the numbers in the prose against the returned rows.

## What I'd do next

- Persist table-selection and field-metadata caches across sessions to shave first-call latency.
- Support finer geographies (places / cities, tracts) and multi-state comparisons.
- Richer answers in the UI -- tables and charts, not just text.
- A larger automated evaluation set with expected values, wired into CI.
