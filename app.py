"""Streamlit chat UI for the US Census data agent.

Run locally:   streamlit run app.py

Features:
- Chat interface (st.chat_message / st.chat_input)
- Multi-turn conversation context (follow-ups are resolved against history)
- Per-response timing + status shown under each answer
- Collapsible view of the exact SQL that was executed
"""

import os

import streamlit as st


# --- secrets bridge --------------------------------------------------------
# The shared text_to_sql / census_agent modules read credentials from
# os.environ (locally populated by a .env file). Streamlit Community Cloud has
# no .env -- it provides secrets via st.secrets. Copy them into os.environ
# here, BEFORE importing census_agent, so the exact same code runs locally and
# when deployed.
def _load_secrets_into_env():
    keys = ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
            "SNOWFLAKE_WAREHOUSE", "GEMINI_API_KEY")
    try:
        secrets = st.secrets
    except Exception:
        return
    for key in keys:
        try:
            if key not in os.environ and key in secrets:
                os.environ[key] = str(secrets[key])
        except Exception:
            pass


_load_secrets_into_env()

from census_agent import ask

st.set_page_config(page_title="US Census Chat", page_icon="🧮")

st.title("🧮 US Census Data Chat")
st.caption(
    "Ask about US population & demographics, based on 2019 American Community "
    "Survey (US Census) data. "
    'Try: "What is the population of California?" then "What about Texas?"'
)

# --- sidebar ---------------------------------------------------------------
with st.sidebar:
    st.header("About")
    st.markdown(
        "This assistant answers questions about **US population & "
        "demographics**, using 2019 US Census (American Community Survey) "
        "data on Snowflake.\n\n"
        "**Try asking:**\n"
        "- Population of a state or county\n"
        "- Median household income / per-capita income\n"
        "- Housing, age, race, or food-stamp share\n\n"
        "**Good to know:**\n"
        "- Answers come only from Census data; off-topic questions are "
        "politely declined\n"
        "- Data is at state / county level (2019)\n"
        "- Ask follow-ups like *\"what about Texas?\"*"
    )
    if st.button("🗑️ Clear conversation"):
        st.session_state.messages = []
        st.rerun()

# --- conversation state ----------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []


def render_message(m: dict) -> None:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("meta"):
            st.caption(m["meta"])
        if m.get("sql"):
            with st.expander("Show SQL"):
                st.code(m["sql"], language="sql")


# render prior turns
for m in st.session_state.messages:
    render_message(m)

# --- handle new input ------------------------------------------------------
if prompt := st.chat_input("Ask a question about US Census data..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    render_message({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Working on it..."):
            history = st.session_state.messages[:-1]  # prior turns only
            result = ask(prompt, history=history, verbose=False)
        answer = result["answer"]
        st.markdown(answer)
        total = result.get("timings", {}).get("total", 0)
        meta = f"⏱️ {total}s · status: {result['status']}"
        st.caption(meta)
        sql = result.get("sql")
        if sql:
            with st.expander("Show SQL"):
                st.code(sql, language="sql")

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "meta": meta,
        "sql": result.get("sql"),
    })