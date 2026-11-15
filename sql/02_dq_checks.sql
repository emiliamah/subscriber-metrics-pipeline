-- Data quality checks on staging. Every check should return 0 failed rows.
SELECT 'missing_user_id' AS check_name,
       COUNT(*) AS failed_rows
FROM   staging.subscription_events
WHERE  user_id IS NULL
UNION ALL
-- Extra copies of the same event_id (2 copies = 1 extra)
SELECT 'duplicate_event_id',
       COALESCE (SUM(copies - 1), 0)
FROM   (SELECT   event_id,
                 COUNT(*) AS copies
        FROM     staging.subscription_events
        GROUP BY event_id
        HAVING   COUNT(*) > 1) AS dupes
UNION ALL
SELECT 'invalid_plan_id',
       COUNT(*)
FROM   staging.subscription_events
WHERE  plan_id NOT IN ('basic_ads', 'premium', 'bundle')
UNION ALL
-- Cancels/upgrades/etc. for a user who never signed up
SELECT 'event_without_signup',
       COUNT(*)
FROM   staging.subscription_events
WHERE  event_type <> 'signup'
       AND user_id NOT IN (SELECT user_id
                           FROM   staging.subscription_events
                           WHERE  event_type = 'signup'
                                  AND user_id IS NOT NULL);