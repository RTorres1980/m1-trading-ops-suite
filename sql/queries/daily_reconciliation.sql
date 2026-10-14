-- Trades that do not match between the OMS and the broker, with the reason.
-- SQLite has no FULL OUTER JOIN before 3.39, so this unions a left join in each direction.
SELECT i.trade_id,
       CASE
           WHEN b.trade_id IS NULL            THEN 'MISSING_AT_BROKER'
           WHEN i.side <> b.side              THEN 'SIDE_MISMATCH'
           WHEN i.quantity <> b.quantity      THEN 'QTY_MISMATCH'
           WHEN ABS(i.price - b.price) > 0.01 THEN 'PRICE_MISMATCH'
           WHEN i.settle_date <> b.settle_date THEN 'SETTLE_DATE_MISMATCH'
       END AS break_type,
       i.symbol, i.quantity AS qty_internal, b.quantity AS qty_broker,
       i.price AS price_internal, b.price AS price_broker
FROM internal_trades i
LEFT JOIN broker_trades b ON b.trade_id = i.trade_id
WHERE b.trade_id IS NULL
   OR i.side <> b.side
   OR i.quantity <> b.quantity
   OR ABS(i.price - b.price) > 0.01
   OR i.settle_date <> b.settle_date

UNION ALL

SELECT b.trade_id, 'MISSING_INTERNAL', b.symbol, NULL, b.quantity, NULL, b.price
FROM broker_trades b
LEFT JOIN internal_trades i ON i.trade_id = b.trade_id
WHERE i.trade_id IS NULL

ORDER BY 2, 1;
