"""Match internal (OMS) trades to broker confirmations and classify every break."""
import pandas as pd

KEY = "trade_id"
COMPARE = ["account", "symbol", "side", "quantity", "price", "settle_date"]

# Price differences within this tolerance are rounding, not breaks.
PRICE_TOLERANCE = 0.01

BREAK_ORDER = [
    "MISSING_AT_BROKER", "MISSING_INTERNAL", "SIDE_MISMATCH", "QTY_MISMATCH",
    "PRICE_MISMATCH", "SETTLE_DATE_MISMATCH", "ACCOUNT_MISMATCH", "SYMBOL_MISMATCH",
]


def _normalize(df):
    df = df.copy()
    df["settle_date"] = pd.to_datetime(df["settle_date"]).dt.normalize()
    df["price"] = df["price"].astype(float)
    df["quantity"] = df["quantity"].astype(int)
    return df


def reconcile(internal, broker, price_tolerance=PRICE_TOLERANCE):
    """Return one row per trade_id with the side-by-side values and a list of break types.

    A trade can have more than one break; `breaks` holds all of them and
    `status` is MATCHED or BREAK.
    """
    internal = _normalize(internal)
    broker = _normalize(broker)
    merged = internal[[KEY] + COMPARE].merge(
        broker[[KEY] + COMPARE], on=KEY, how="outer", suffixes=("_int", "_brk"), indicator=True)

    breaks = pd.Series([[] for _ in range(len(merged))], index=merged.index)
    only_int = merged["_merge"] == "left_only"
    only_brk = merged["_merge"] == "right_only"
    both = merged["_merge"] == "both"

    for i in merged.index[only_int]:
        breaks[i] = ["MISSING_AT_BROKER"]
    for i in merged.index[only_brk]:
        breaks[i] = ["MISSING_INTERNAL"]

    checks = {
        "SIDE_MISMATCH": merged["side_int"] != merged["side_brk"],
        "QTY_MISMATCH": merged["quantity_int"] != merged["quantity_brk"],
        "PRICE_MISMATCH": (merged["price_int"] - merged["price_brk"]).abs() > price_tolerance,
        "SETTLE_DATE_MISMATCH": merged["settle_date_int"] != merged["settle_date_brk"],
        "ACCOUNT_MISMATCH": merged["account_int"] != merged["account_brk"],
        "SYMBOL_MISMATCH": merged["symbol_int"] != merged["symbol_brk"],
    }
    for name, mask in checks.items():
        for i in merged.index[both & mask]:
            breaks[i] = breaks[i] + [name]

    merged["breaks"] = breaks
    merged["status"] = merged["breaks"].map(lambda b: "BREAK" if b else "MATCHED")
    merged["qty_diff"] = merged["quantity_brk"] - merged["quantity_int"]
    merged["notional_int"] = merged["quantity_int"] * merged["price_int"]
    merged["notional_brk"] = merged["quantity_brk"] * merged["price_brk"]
    merged["notional_diff"] = (merged["notional_brk"].fillna(0) - merged["notional_int"].fillna(0)).round(2)
    return merged.drop(columns="_merge")


def break_report(recon):
    """One row per (trade, break type), sorted by severity then notional impact."""
    rows = recon[recon["status"] == "BREAK"].explode("breaks").rename(columns={"breaks": "break_type"})
    rows["severity_rank"] = rows["break_type"].map({b: i for i, b in enumerate(BREAK_ORDER)})
    rows["abs_notional_diff"] = rows["notional_diff"].abs()
    rows = rows.sort_values(["severity_rank", "abs_notional_diff"], ascending=[True, False])
    cols = ["trade_id", "break_type", "account_int", "account_brk", "symbol_int", "symbol_brk",
            "side_int", "side_brk", "quantity_int", "quantity_brk", "price_int", "price_brk",
            "settle_date_int", "settle_date_brk", "notional_diff"]
    return rows[cols].reset_index(drop=True)


def summary(recon):
    total = len(recon)
    n_breaks = int((recon["status"] == "BREAK").sum())
    counts = recon.loc[recon["status"] == "BREAK", "breaks"].explode().value_counts()
    return {
        "trades_compared": total,
        "matched": total - n_breaks,
        "breaks": n_breaks,
        "match_rate_pct": round(100 * (total - n_breaks) / total, 2) if total else 0.0,
        "breaks_by_type": {k: int(v) for k, v in counts.items()},
        "net_notional_diff": round(float(recon["notional_diff"].sum()), 2),
    }
