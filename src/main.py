"""Run the end-of-day trading operations workflow.

  1. Generate (or load) the day's OMS trades and broker confirmations
  2. Reconcile them and classify breaks
  3. Run compliance surveillance on executions
  4. Load everything into SQLite and write an Excel report

Usage:
    python -m src.main                 # generate fresh synthetic data, then run
    python -m src.main --use-existing  # run on the CSVs already in data/
"""
import argparse
import json
import os

import pandas as pd

from src import analytics, compliance, db, reconcile, reporting
from src.generate_data import DATA_DIR, generate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(ROOT, "output")


def load_inputs(data_dir=DATA_DIR):
    internal = pd.read_csv(os.path.join(data_dir, "internal_trades.csv"), parse_dates=["exec_time"])
    broker = pd.read_csv(os.path.join(data_dir, "broker_trades.csv"))
    restricted = pd.read_csv(os.path.join(data_dir, "restricted_list.csv"))
    return internal, broker, restricted


def run(use_existing=False, output_dir=OUTPUT_DIR):
    if not use_existing:
        generate()
    internal, broker, restricted = load_inputs()

    recon = reconcile.reconcile(internal, broker)
    breaks = reconcile.break_report(recon)
    recon_summary = reconcile.summary(recon)
    exceptions = compliance.run_all(internal, restricted["symbol"])
    volume = analytics.volume_by_symbol(internal)
    break_rates = analytics.break_rate_by_symbol(recon)

    os.makedirs(output_dir, exist_ok=True)
    conn = db.load(os.path.join(output_dir, "trades.db"), internal, broker, restricted)
    conn.close()
    breaks.to_csv(os.path.join(output_dir, "breaks.csv"), index=False)
    exceptions.to_csv(os.path.join(output_dir, "compliance_exceptions.csv"), index=False)
    report = reporting.export_report(os.path.join(output_dir, "eod_ops_report.xlsx"),
                                     recon_summary, breaks, exceptions, volume, break_rates)

    print(json.dumps(recon_summary, indent=2))
    print(f"Compliance exceptions: {exceptions['rule'].value_counts().to_dict()}")
    print(f"Report written to {report}")
    return recon_summary, exceptions


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--use-existing", action="store_true", help="skip data generation")
    run(parser.parse_args().use_existing)
