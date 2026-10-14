import os

import pandas as pd
import pytest

from src import analytics, compliance, db, reconcile
from src.generate_data import generate


@pytest.fixture(scope="module")
def day(tmp_path_factory):
    out = tmp_path_factory.mktemp("data")
    internal, broker, injected = generate(n_trades=1500, seed=7, out_dir=str(out))
    restricted = pd.read_csv(out / "restricted_list.csv")
    return internal, broker, injected, restricted


def _trade(**kw):
    base = {"trade_id": "T1", "account": "A1", "symbol": "AAPL", "side": "BUY", "quantity": 100,
            "price": 190.0, "trade_date": "2025-06-02", "settle_date": "2025-06-03",
            "exec_time": "2025-06-02 10:00:00"}
    base.update(kw)
    return base


def test_reconciliation_finds_every_injected_break(day):
    internal, broker, injected, _ = day
    found = reconcile.break_report(reconcile.reconcile(internal, broker))
    expected = set(map(tuple, injected[["trade_id", "break_type"]].values))
    actual = set(map(tuple, found[["trade_id", "break_type"]].values))
    assert actual == expected


def test_clean_trades_match(day):
    internal, _, _, _ = day
    recon = reconcile.reconcile(internal, internal.drop(columns="exec_time"))
    assert reconcile.summary(recon)["breaks"] == 0


def test_price_tolerance():
    i = pd.DataFrame([_trade()])
    b = pd.DataFrame([_trade(price=190.005)])
    assert reconcile.summary(reconcile.reconcile(i, b))["breaks"] == 0
    b = pd.DataFrame([_trade(price=190.05)])
    assert reconcile.summary(reconcile.reconcile(i, b))["breaks_by_type"] == {"PRICE_MISMATCH": 1}


def test_multiple_breaks_on_one_trade():
    i = pd.DataFrame([_trade()])
    b = pd.DataFrame([_trade(quantity=90, side="SELL")])
    types = set(reconcile.break_report(reconcile.reconcile(i, b))["break_type"])
    assert types == {"QTY_MISMATCH", "SIDE_MISMATCH"}


def test_compliance_rules():
    trades = pd.DataFrame([
        _trade(trade_id="ok"),
        _trade(trade_id="zero", quantity=0),
        _trade(trade_id="restricted", symbol="TSLA"),
        _trade(trade_id="early", exec_time="2025-06-02 09:15:00"),
        _trade(trade_id="late", exec_time="2025-06-02 16:00:00"),
        _trade(trade_id="t2", settle_date="2025-06-04"),
        _trade(trade_id="big", quantity=2000),
    ])
    hits = compliance.run_all(trades, restricted=["TSLA"])
    by_rule = hits.groupby("rule")["trade_id"].apply(set).to_dict()
    assert by_rule["NON_POSITIVE_QTY"] == {"zero"}
    assert by_rule["RESTRICTED_SYMBOL"] == {"restricted"}
    assert by_rule["OUTSIDE_MARKET_HOURS"] == {"early", "late"}
    assert by_rule["SETTLEMENT_CYCLE"] == {"t2"}
    assert by_rule["LARGE_NOTIONAL"] == {"big"}
    assert "ok" not in set(hits["trade_id"])


def test_friday_trade_settles_monday():
    trades = pd.DataFrame([_trade(trade_date="2025-06-06", settle_date="2025-06-09",
                                  exec_time="2025-06-06 11:00:00")])
    assert compliance.run_all(trades).empty


def test_sql_matches_python(day, tmp_path):
    internal, broker, _, restricted = day
    conn = db.load(str(tmp_path / "t.db"), internal, broker, restricted)
    sql_breaks = db.run_query_file(conn, "daily_reconciliation.sql")
    py_breaks = reconcile.reconcile(internal, broker)
    assert set(sql_breaks["trade_id"]) == set(py_breaks.loc[py_breaks["status"] == "BREAK", "trade_id"])

    sql_exc = db.run_query_file(conn, "compliance_checks.sql")
    py_exc = compliance.run_all(internal, restricted["symbol"])
    for rule in sql_exc["rule"].unique():
        assert set(sql_exc.loc[sql_exc["rule"] == rule, "trade_id"]) == \
            set(py_exc.loc[py_exc["rule"] == rule, "trade_id"])
    conn.close()


def test_net_positions_signs():
    trades = pd.DataFrame([_trade(trade_id="a", quantity=100), _trade(trade_id="b", side="SELL", quantity=30)])
    pos = analytics.net_positions(trades)
    assert pos.loc[0, "net_shares"] == 70


def test_report_written(day, tmp_path):
    from src import reporting
    internal, broker, _, restricted = day
    recon = reconcile.reconcile(internal, broker)
    path = reporting.export_report(
        str(tmp_path / "r.xlsx"), reconcile.summary(recon), reconcile.break_report(recon),
        compliance.run_all(internal, restricted["symbol"]), analytics.volume_by_symbol(internal),
        analytics.break_rate_by_symbol(recon))
    assert os.path.exists(path)
    expected = {"Summary", "Breaks", "Compliance", "Volume", "Break Rate by Symbol"}
    assert set(pd.ExcelFile(path).sheet_names) == expected
