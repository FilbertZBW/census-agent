# US Census Data Chat Agent

A natural-language chat agent that answers questions about US population and
demographics. It turns plain-English questions into Snowflake SQL over the 2019
American Community Survey (US Census) dataset, executes them, and returns
grounded, conversational answers -- with guardrails, self-healing retries, and a
Streamlit web UI.

**Live demo:** https://census-agent-j9khcnvgbj5397k2zcwvfk.streamlit.app/

## Features

- Natural language -> Snowflake SQL -> grounded natural-language answer
- Dynamic schema grounding over 364 census tables (nothing hard-coded)
- Guardrails: off-topic and prompt-injection questions are politely refused
- Self-healing SQL: a failed query is retried with the Snowflake error fed back to the model
- Graceful degradation: every failure returns a clean status + message; the pipeline never crashes
- Multi-turn context: follow-ups like "what about Texas?" are resolved against history
- Per-response timing and a collapsible view of the exact SQL executed
- Fast: typical responses in 8-15s, well under the 60s target

## How it works

The pipeline has three layers:

1. `text_to_sql.py` -- the text-to-SQL engine, using two-stage dynamic grounding:
   - Stage 1 (`select_tables`): a single Gemini call that acts as both guardrail and retriever -- it refuses off-topic / injection inputs, or picks the 1-3 most relevant tables from the live 364-table catalog.
   - Stage 2 (`generate_sql_grounded`): generates Snowflake SQL using only the real field codes of the chosen tables.
   - Execution with a self-healing retry (`run_query_with_retry`).
2. `census_agent.py` -- orchestration: follow-up rewrite -> guardrail + SQL -> execute with retry -> grounded answer. Adds per-stage timing, rate-limit handling, and graceful degradation.
3. `app.py` -- Streamlit chat UI: multi-turn history, timing / status caption, a "Show SQL" expander, and a secrets bridge so the same code runs locally (.env) and on Streamlit Cloud (st.secrets).

## Dataset

- `US_OPEN_CENSUS.PUBLIC` on Snowflake (2019 American Community Survey)
- Census-block-group granularity, keyed by a 12-character FIPS string `CENSUS_BLOCK_GROUP`
- 364 data tables; the metadata table `2019_METADATA_CBG_FIELD_DESCRIPTIONS` drives the dynamic grounding

## Tech stack

- Python 3.12
- Streamlit (UI + Community Cloud hosting)
- snowflake-connector-python
- Google Gemini via `google-genai` -- model `gemini-flash-lite-latest`, "thinking" disabled for low, predictable latency

## Local setup

Create and activate a virtual environment, then install dependencies:

    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt

Create a `.env` file in the project root:

    SNOWFLAKE_ACCOUNT=HJUPJPZ-QQ15240
    SNOWFLAKE_USER=your_user
    SNOWFLAKE_PASSWORD=your_password
    SNOWFLAKE_WAREHOUSE=COMPUTE_WH
    GEMINI_API_KEY=your_key

Run the app:

    streamlit run app.py

## Testing

Unit tests (no network required):

    python -m unittest test_agent -v

Full suite including live integration tests (needs a populated .env):

    set RUN_LIVE_TESTS=1 && python -m unittest test_agent -v

`stress_test.py` is an interactive script that fires 10 tricky / adversarial
questions -- hard aggregations, per-capita, county-level median ranking, non-US
geographies, ambiguous city names, and a prompt-injection attempt -- to observe
behavior at the edges:

    python stress_test.py

## Deployment

Deployed on Streamlit Community Cloud. In the cloud, credentials come from the
app's Secrets (TOML) instead of a .env file; `app.py` copies `st.secrets` into
`os.environ` before importing the agent, so one codebase runs both locally and
when deployed.

## Project structure

    app.py                  Streamlit chat UI
    census_agent.py         pipeline orchestration
    text_to_sql.py          dynamic grounding + SQL generation + Snowflake exec
    test_agent.py           unit + integration tests
    stress_test.py          interactive tricky / adversarial probe
    requirements.txt        dependencies
    .streamlit/config.toml  hides the Streamlit dev toolbar for a clean demo

## Example questions

- What is the total population of California?
- Which 5 counties in Texas have the largest population?
- What is the per capita income in Texas?
- What percentage of households in California receive food stamps?
- ...then a follow-up: "What about Florida?"
