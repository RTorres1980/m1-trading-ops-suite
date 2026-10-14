"""Post-trade compliance surveillance on internal (OMS) executions.

Each rule returns the trades that hit it; run_all() combines them into one exceptions list.
"""
import numpy as np
import pandas as pd

MARKET_OPEN = pd.Timedelta(hours=9, minutes=30)
MARKET_CLOSE = pd.Timedelta(hours=16)
LARGE_TRADE_NOTIONAL = 250_000
LARGE_QTY_MULTIPLE = 10  # quantity this many times the symbol's median is flagged as a likely fat finger


def _prep(trades):
    t = trades.copy()
    t["exec_time"] = pd.to_datetime(t["exec_time"])
    t["trade_date"] = pd.to_datetime(t["trade_date"]).dt.normalize()
    t["settle_date"] = pd.to_datetime(t["settle_date"]).dt.normalize()
    t["notional"] = t["quantity"] * t["price"]
    return t


def non_positive_quantity(t):
    return t[t["quantity"] <= 0], "Quantity must be greater than zero"


def restricted_symbols(t, restricted):
    return t[t["symbol"].isin(set(restricted))], "Symbol is on the restricted list"


def outside_market_hours(t):
    tod = t["exec_time"] - t["exec_time"].dt.normalize()
    return t[(tod < MARKET_OPEN) | (tod >= MARKET_CLOSE)], "Executed outside 09:30-16:00 regular session"


def wrong_settlement_cycle(t):
    expected = pd.to_datetime(np.busday_offset(t["trade_date"].values.astype("datetime64[D]"), 1, roll="forward"))
    return t[t["settle_date"].values != expected.values], "Settlement date is not T+1"


def large_notional(t, threshold=LARGE_TRADE_NOTIONAL):
    return t[t["notional"] >= threshold], f"Notional at or above ${threshold:,.0f} needs supervisory review"


def fat_finger_quantity(t, multiple=LARGE_QTY_MULTIPLE):
    median = t.groupby("symbol")["quantity"].transform("median")
    return t[(t["quantity"] > 0) & (t["quantity"] > multiple * median)], \
        f"Quantity is over {multiple}x the symbol's median (possible input error)"


def run_all(trades, restricted=()):
    """Return a DataFrame of exceptions: trade_id, rule, detail, plus key trade fields."""
    t = _prep(trades)
    rules = [
        ("NON_POSITIVE_QTY", non_positive_quantity(t)),
        ("RESTRICTED_SYMBOL", restricted_symbols(t, restricted)),
        ("OUTSIDE_MARKET_HOURS", outside_market_hours(t)),
        ("SETTLEMENT_CYCLE", wrong_settlement_cycle(t)),
        ("LARGE_NOTIONAL", large_notional(t)),
        ("FAT_FINGER_QTY", fat_finger_quantity(t)),
    ]
    frames = []
    for rule, (hits, detail) in rules:
        if len(hits):
            frames.append(hits.assign(rule=rule, detail=detail))
    cols = ["trade_id", "rule", "detail", "account", "symbol", "side", "quantity", "price", "notional", "exec_time"]
    if not frames:
        return pd.DataFrame(columns=cols)
    return pd.concat(frames, ignore_index=True)[cols]
