BEGIN TRANSACTION;

ALTER TABLE audit_auditlog ADD COLUMN before_json text NULL CHECK ((JSON_VALID("before_json") OR "before_json" IS NULL));
ALTER TABLE audit_auditlog ADD COLUMN after_json text NULL CHECK ((JSON_VALID("after_json") OR "after_json" IS NULL));

UPDATE audit_auditlog
SET before_json = COALESCE(before_json, '{}'),
    after_json = COALESCE(after_json, changes, '{}');

CREATE TABLE IF NOT EXISTS audit_adminloginlog (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    ip_address char(39) NOT NULL,
    user_agent TEXT NOT NULL,
    is_success bool NOT NULL,
    created_at datetime NOT NULL,
    user_id bigint NOT NULL REFERENCES users_user(id) DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX IF NOT EXISTS audit_admin_user_id_d420df_idx
ON audit_adminloginlog (user_id, created_at);

CREATE TABLE IF NOT EXISTS audit_webhookprocessinglog (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    provider varchar(50) NOT NULL,
    event_id varchar(255) NOT NULL,
    event_type varchar(100) NOT NULL,
    status varchar(20) NOT NULL,
    error_message TEXT NOT NULL,
    processing_time_ms INTEGER NULL,
    created_at datetime NOT NULL
);

CREATE INDEX IF NOT EXISTS audit_webho_provide_76ecbf_idx
ON audit_webhookprocessinglog (provider, event_id);

CREATE INDEX IF NOT EXISTS audit_webho_status_bcff36_idx
ON audit_webhookprocessinglog (status, created_at);

COMMIT;
