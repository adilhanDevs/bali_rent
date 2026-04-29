BEGIN TRANSACTION;

UPDATE analytics_analyticsevent
SET user_id = NULL
WHERE user_id IS NOT NULL
  AND user_id NOT IN (SELECT id FROM users_user);

COMMIT;
