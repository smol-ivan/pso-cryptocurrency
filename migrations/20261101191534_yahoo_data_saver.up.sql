CREATE TABLE market_prices (
    symbol TEXT NOT NULL,
    timestamp BIGINT NOT NULL,
    open NUMERIC NOT NULL,
    high NUMERIC NOT NULL,
    low NUMERIC NOT NULL,
    close NUMERIC NOT NULL,
    adjclose NUMERIC NOT NULL,
    volume BIGINT NOT NULL,

    PRIMARY KEY (symbol, timestamp)
);

-- To generate updates, we should use insert ... ON conflict, 
-- so we dont have duplicates
