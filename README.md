# Trading Operations Suite

![CI](https://github.com/RTorres1980/m1-trading-ops-suite/actions/workflows/ci.yml/badge.svg)

An end-of-day trading operations workflow for a retail brokerage, built on synthetic data. It reconciles the firm's trade records against broker confirmations, classifies every break, runs post-trade compliance surveillance, and produces an Excel report, a SQLite database and an interactive dashboard.

The data generator plants known problems (missing confirmations, quantity and price differences, wrong settlement dates, off-hours executions, fat-finger orders), and the tests check that the workflow finds every one of them.

## What it does

| Step | Module | Output |
|---|---|---|
| Generate a trading day | `src/generate_data.py` | `data/internal_trades.csv` (OMS executions), `data/broker_trades.csv` (confirmations with planted breaks), `data/restricted_list.csv` |
| Reconcile | `src/reconcile.py` | Every trade matched on `trade_id` and compared on account, symbol, side, quantity, price (±$0.01) and settlement date. Each break is labeled, and one trade can carry several. |
| Compliance surveillance | `src/compliance.py` | Exceptions for zero/negative quantity, restricted symbols, executions outside 09:30–16:00, settlement not T+1, notional ≥ $250k, and quantities over 10× the symbol's median |
| Analytics | `src/analytics.py` | Volume and notional by symbol, net position changes, hourly activity, break rate by symbol |
| SQL | `sql/` | Schema plus reconciliation, compliance and volume queries that run against the generated SQLite database and return the same results as the Python code |
| Report | `src/reporting.py` | `output/eod_ops_report.xlsx` with Summary, Breaks, Compliance, Volume and Break Rate sheets |
| Dashboard | `src/dashboard.py` | Streamlit app with headline metrics, a filterable break queue, the exceptions list and charts |

Break types: `MISSING_AT_BROKER`, `MISSING_INTERNAL`, `SIDE_MISMATCH`, `QTY_MISMATCH`, `PRICE_MISMATCH`, `SETTLE_DATE_MISMATCH`, `ACCOUNT_MISMATCH`, `SYMBOL_MISMATCH`.

## Run it

Requires Python 3.10+.

```bash
pip install -r requirements.txt

python -m src.main               # generate a day of trades and run the full workflow
streamlit run src/dashboard.py   # open the dashboard at http://localhost:8501
pytest -q                        # run the tests
```

Sample output from the default run:

```
trades_compared: 2001   matched: 1953   breaks: 48   match_rate_pct: 97.6
breaks_by_type: PRICE_MISMATCH 13, QTY_MISMATCH 13, MISSING_AT_BROKER 10,
                SETTLE_DATE_MISMATCH 6, SIDE_MISMATCH 5, MISSING_INTERNAL 1
Compliance exceptions: OUTSIDE_MARKET_HOURS 39, RESTRICTED_SYMBOL 13, LARGE_NOTIONAL 10,
                       FAT_FINGER_QTY 10, NON_POSITIVE_QTY 4
```

To query the database directly:

```bash
sqlite3 output/trades.db < sql/queries/daily_reconciliation.sql
```

Or with Docker:

```bash
docker build -t trading-ops . && docker run -p 8501:8501 trading-ops
```

## Tests

`tests/test_workflow.py` checks that:

- reconciliation finds exactly the breaks the generator planted, with no false positives
- the price tolerance is applied, and a trade with several problems reports each one
- each compliance rule flags the right trades, and a Friday trade settling Monday passes the T+1 check
- the SQL queries and the Python code agree
- the Excel report is written with all five sheets

CI runs lint, the tests and the full workflow on every push.

## License

MIT
