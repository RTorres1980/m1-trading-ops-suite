"""Load the day's data into SQLite so the SQL in sql/queries/ can run against it."""
import os
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "sql", "schema.sql")


def load(db_path, internal, broker, restricted):
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    with open(SCHEMA) as f:
        conn.executescript(f.read())

    def prep(df):
        df = df.copy()
        for col in ("trade_date", "settle_date"):
            if col in df:
                df[col] = df[col].astype(str).str[:10]
        if "exec_time" in df:
            df["exec_time"] = df["exec_time"].astype(str)
        return df

    prep(internal).to_sql("internal_trades", conn, if_exists="append", index=False)
    prep(broker).to_sql("broker_trades", conn, if_exists="append", index=False)
    restricted.to_sql("restricted_list", conn, if_exists="append", index=False)
    conn.commit()
    return conn


def run_query_file(conn, name):
    import pandas as pd
    with open(os.path.join(ROOT, "sql", "queries", name)) as f:
        return pd.read_sql_query(f.read(), conn)
