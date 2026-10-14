"""Generate synthetic trade data with known breaks for the reconciliation workflow.

Produces three files in data/:
  internal_trades.csv  - the firm's order management system (OMS) record of executions
  broker_trades.csv    - the executing broker's confirmations, with breaks injected
  restricted_list.csv  - symbols the compliance team has restricted
"""
import argparse
import os

import numpy as np
import pandas as pd

SYMBOLS = {
    "AAPL": 190.0, "MSFT": 410.0, "NVDA": 120.0, "AMZN": 185.0, "GOOGL": 170.0,
    "JPM": 205.0, "VTI": 270.0, "VOO": 500.0, "SCHD": 80.0, "TSLA": 240.0,
}
RESTRICTED = ["TSLA"]
ACCOUNTS = [f"ACC{n:04d}" for n in range(1, 41)]

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def settlement_date(trade_date):
    """T+1 in business days (US equities settle T+1 since May 2024; holidays ignored)."""
    return pd.Timestamp(np.busday_offset(trade_date.date(), 1, roll="forward"))


def make_internal_trades(n_trades, trade_date, rng):
    # The restricted symbol trades rarely, as it would after the restriction was published.
    weights = np.array([0.05 if s in RESTRICTED else 1.0 for s in SYMBOLS])
    symbols = rng.choice(list(SYMBOLS), size=n_trades, p=weights / weights.sum())
    base = np.array([SYMBOLS[s] for s in symbols])
    # Executions spread across the session, with a few outside 09:30-16:00 for compliance to catch.
    minutes = rng.integers(0, 390, size=n_trades)
    off_hours = rng.random(n_trades) < 0.02
    minutes[off_hours] = rng.choice([-45, -20, 400, 430], size=off_hours.sum())
    session_open = pd.Timestamp(trade_date) + pd.Timedelta(hours=9, minutes=30)

    df = pd.DataFrame({
        "trade_id": [f"T{trade_date:%Y%m%d}-{i:05d}" for i in range(1, n_trades + 1)],
        "account": rng.choice(ACCOUNTS, size=n_trades),
        "symbol": symbols,
        "side": rng.choice(["BUY", "SELL"], size=n_trades, p=[0.6, 0.4]),
        "quantity": rng.integers(1, 500, size=n_trades),
        "price": np.round(base * (1 + rng.normal(0, 0.01, size=n_trades)), 2),
        "exec_time": [session_open + pd.Timedelta(minutes=int(m)) for m in minutes],
    })
    df["trade_date"] = pd.Timestamp(trade_date).normalize()
    df["settle_date"] = settlement_date(pd.Timestamp(trade_date))
    # A handful of fat-finger quantities and zero-quantity bookings.
    fat = rng.random(n_trades) < 0.005
    df.loc[fat, "quantity"] = df.loc[fat, "quantity"] * 100
    zero = rng.random(n_trades) < 0.003
    df.loc[zero, "quantity"] = 0
    return df


def make_broker_trades(internal, rng):
    """Copy internal trades and inject realistic breaks. Returns (broker_df, injected_breaks)."""
    broker = internal.drop(columns=["exec_time"]).copy()
    n = len(broker)
    injected = []

    def pick(k, exclude):
        pool = np.setdiff1d(np.arange(n), list(exclude))
        return rng.choice(pool, size=min(k, len(pool)), replace=False)

    used = set()
    missing = pick(max(1, n // 200), used)
    used.update(missing)
    injected += [(broker.at[i, "trade_id"], "MISSING_AT_BROKER") for i in missing]

    qty = pick(max(1, n // 150), used)
    used.update(qty)
    broker.loc[qty, "quantity"] = broker.loc[qty, "quantity"] + rng.integers(1, 20, size=len(qty))
    injected += [(broker.at[i, "trade_id"], "QTY_MISMATCH") for i in qty]

    px = pick(max(1, n // 150), used)
    used.update(px)
    broker.loc[px, "price"] = np.round(broker.loc[px, "price"] * (1 + rng.choice([-1, 1], len(px)) * 0.004), 2)
    injected += [(broker.at[i, "trade_id"], "PRICE_MISMATCH") for i in px]

    side = pick(max(1, n // 400), used)
    used.update(side)
    broker.loc[side, "side"] = broker.loc[side, "side"].map({"BUY": "SELL", "SELL": "BUY"})
    injected += [(broker.at[i, "trade_id"], "SIDE_MISMATCH") for i in side]

    settle = pick(max(1, n // 300), used)
    used.update(settle)
    broker.loc[settle, "settle_date"] = broker.loc[settle, "settle_date"] + pd.offsets.BDay(1)
    injected += [(broker.at[i, "trade_id"], "SETTLE_DATE_MISMATCH") for i in settle]

    broker = broker.drop(index=missing)

    # A trade the broker booked that the OMS never recorded.
    extra = broker.iloc[[0]].copy()
    extra["trade_id"] = "BRK-UNKNOWN-0001"
    broker = pd.concat([broker, extra], ignore_index=True)
    injected.append(("BRK-UNKNOWN-0001", "MISSING_INTERNAL"))

    return broker.reset_index(drop=True), pd.DataFrame(injected, columns=["trade_id", "break_type"])


def generate(n_trades=2000, trade_date="2025-06-02", seed=42, out_dir=DATA_DIR):
    rng = np.random.default_rng(seed)
    trade_date = pd.Timestamp(trade_date)
    internal = make_internal_trades(n_trades, trade_date, rng)
    broker, injected = make_broker_trades(internal, rng)

    os.makedirs(out_dir, exist_ok=True)
    internal.to_csv(os.path.join(out_dir, "internal_trades.csv"), index=False)
    broker.to_csv(os.path.join(out_dir, "broker_trades.csv"), index=False)
    pd.DataFrame({"symbol": RESTRICTED, "reason": ["Pending corporate action"]}).to_csv(
        os.path.join(out_dir, "restricted_list.csv"), index=False)
    return internal, broker, injected


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--trades", type=int, default=2000)
    parser.add_argument("--date", default="2025-06-02", help="trade date, YYYY-MM-DD")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    internal, broker, injected = generate(args.trades, args.date, args.seed)
    print(f"Wrote {len(internal)} internal and {len(broker)} broker trades to {DATA_DIR}")
    print(f"Injected breaks: {injected['break_type'].value_counts().to_dict()}")
