"""Operational metrics for the trading day."""
import pandas as pd


def volume_by_symbol(trades):
    t = trades.assign(notional=trades["quantity"] * trades["price"])
    out = t.groupby("symbol").agg(
        trades=("trade_id", "count"),
        shares=("quantity", "sum"),
        notional=("notional", "sum"),
        buys=("side", lambda s: int((s == "BUY").sum())),
        sells=("side", lambda s: int((s == "SELL").sum())),
    )
    out["notional"] = out["notional"].round(2)
    return out.sort_values("notional", ascending=False).reset_index()


def net_positions(trades):
    """Net share change per account and symbol from the day's executions."""
    signed = trades["quantity"].where(trades["side"] == "BUY", -trades["quantity"])
    return (trades.assign(net_shares=signed)
            .groupby(["account", "symbol"], as_index=False)["net_shares"].sum()
            .query("net_shares != 0")
            .sort_values(["account", "symbol"])
            .reset_index(drop=True))


def hourly_activity(trades):
    hour = pd.to_datetime(trades["exec_time"]).dt.hour
    return trades.groupby(hour).size().rename_axis("hour").reset_index(name="trades")


def break_rate_by_symbol(recon):
    sym = recon["symbol_int"].fillna(recon["symbol_brk"])
    out = recon.assign(symbol=sym, is_break=recon["status"] == "BREAK").groupby("symbol").agg(
        trades=("trade_id", "count"), breaks=("is_break", "sum"))
    out["break_rate_pct"] = (100 * out["breaks"] / out["trades"]).round(2)
    return out.sort_values("break_rate_pct", ascending=False).reset_index()
