-- SQLite schema for the trading operations workflow.
DROP TABLE IF EXISTS internal_trades;
DROP TABLE IF EXISTS broker_trades;
DROP TABLE IF EXISTS restricted_list;

CREATE TABLE internal_trades (
    trade_id    TEXT PRIMARY KEY,
    account     TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    side        TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity    INTEGER NOT NULL,
    price       REAL NOT NULL,
    exec_time   TEXT NOT NULL,
    trade_date  TEXT NOT NULL,
    settle_date TEXT NOT NULL
);

CREATE TABLE broker_trades (
    trade_id    TEXT PRIMARY KEY,
    account     TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    side        TEXT NOT NULL,
    quantity    INTEGER NOT NULL,
    price       REAL NOT NULL,
    trade_date  TEXT NOT NULL,
    settle_date TEXT NOT NULL
);

CREATE TABLE restricted_list (
    symbol TEXT PRIMARY KEY,
    reason TEXT
);
