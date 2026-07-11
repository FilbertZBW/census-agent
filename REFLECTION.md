# Reflection

## Overview

The goal was a production-flavored natural-language interface to the US Census
data on Snowflake: type a question, get a trustworthy answer in seconds, with
sensible behavior on bad or malicious inputs. Below are the decisions I'm
happiest with and the tradeoffs behind them.

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

## What I'd do next

- Persist table-selection and field-metadata caches across sessions to shave first-call latency.
- Support finer geographies (places / cities, tracts) and multi-state comparisons.
- Richer answers in the UI -- tables and charts, not just text.
- A larger automated evaluation set with expected values, wired into CI.
