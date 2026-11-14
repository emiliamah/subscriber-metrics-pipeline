-- Staging: the loading dock. Raw events land here exactly as they arrive.
-- No constraints on purpose, so bad rows get in and the DQ checks can catch them.

CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS staging.subscription_events (
    event_id     TEXT,
    user_id      TEXT,
    event_type   TEXT,
    plan_id      TEXT,
    event_ts     TIMESTAMP,
    price_usd    NUMERIC(10, 2),
    country      TEXT,
    source_file  TEXT,                      -- which CSV this row came from
    loaded_at    TIMESTAMP DEFAULT now()    -- when we loaded it
);