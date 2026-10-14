"""Streamlit dashboard for the day's reconciliation and compliance results.

Run from the repository root:  streamlit run src/dashboard.py
"""
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import analytics, compliance, reconcile  # noqa: E402
from src.generate_data import DATA_DIR, generate  # noqa: E402
from src.main import load_inputs  # noqa: E402

st.set_page_config(page_title="Trading Ops Dashboard", layout="wide")
st.title("Trading Operations Dashboard")

if not os.path.exists(os.path.join(DATA_DIR, "internal_trades.csv")):
    generate()

with st.sidebar:
    st.header("Data")
    if st.button("Generate a new trading day"):
        seed = st.session_state.get("seed", 42) + 1
        st.session_state["seed"] = seed
        generate(seed=seed)
    tolerance = st.number_input("Price tolerance ($)", min_value=0.0, value=reconcile.PRICE_TOLERANCE, step=0.01)

internal, broker, restricted = load_inputs()
recon = reconcile.reconcile(internal, broker, price_tolerance=tolerance)
summary = reconcile.summary(recon)
breaks = reconcile.break_report(recon)
exceptions = compliance.run_all(internal, restricted["symbol"])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Trades compared", f"{summary['trades_compared']:,}")
c2.metric("Match rate", f"{summary['match_rate_pct']}%")
c3.metric("Open breaks", summary["breaks"])
c4.metric("Compliance exceptions", len(exceptions))

left, right = st.columns(2)
with left:
    st.subheader("Breaks by type")
    st.bar_chart(breaks["break_type"].value_counts())
with right:
    st.subheader("Exceptions by rule")
    st.bar_chart(exceptions["rule"].value_counts())

st.subheader("Break queue")
types = st.multiselect("Break type", sorted(breaks["break_type"].unique()))
st.dataframe(breaks[breaks["break_type"].isin(types)] if types else breaks, width="stretch")

st.subheader("Compliance exceptions")
st.dataframe(exceptions, width="stretch")

st.subheader("Notional by symbol")
st.bar_chart(analytics.volume_by_symbol(internal).set_index("symbol")["notional"])

st.subheader("Executions by hour")
st.bar_chart(analytics.hourly_activity(internal).set_index("hour"))
