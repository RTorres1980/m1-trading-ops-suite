-- Shares and notional traded per symbol.
SELECT symbol,
       COUNT(*)                                          AS trades,
       SUM(quantity)                                     AS shares,
       ROUND(SUM(quantity * price), 2)                   AS notional,
       SUM(CASE WHEN side = 'BUY'  THEN 1 ELSE 0 END)    AS buys,
       SUM(CASE WHEN side = 'SELL' THEN 1 ELSE 0 END)    AS sells
FROM internal_trades
GROUP BY symbol
ORDER BY notional DESC;
