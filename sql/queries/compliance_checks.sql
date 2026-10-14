-- Executions that hit a compliance rule. One row per trade per rule.
SELECT trade_id, 'NON_POSITIVE_QTY' AS rule, symbol, quantity, price, exec_time
FROM internal_trades WHERE quantity <= 0

UNION ALL
SELECT t.trade_id, 'RESTRICTED_SYMBOL', t.symbol, t.quantity, t.price, t.exec_time
FROM internal_trades t JOIN restricted_list r ON r.symbol = t.symbol

UNION ALL
SELECT trade_id, 'OUTSIDE_MARKET_HOURS', symbol, quantity, price, exec_time
FROM internal_trades
WHERE time(exec_time) < '09:30:00' OR time(exec_time) >= '16:00:00'

UNION ALL
SELECT trade_id, 'LARGE_NOTIONAL', symbol, quantity, price, exec_time
FROM internal_trades WHERE quantity * price >= 250000

ORDER BY 2, 1;
