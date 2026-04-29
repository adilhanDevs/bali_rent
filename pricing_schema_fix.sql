BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS "pricing_devicepricingrule" (
  "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
  "name" varchar(100) NOT NULL,
  "platform" varchar(20) NOT NULL,
  "adjustment_percent" decimal NOT NULL,
  "is_active" bool NOT NULL,
  "created_at" datetime NOT NULL
);

CREATE TABLE IF NOT EXISTS "pricing_geopricingrule" (
  "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
  "name" varchar(100) NOT NULL,
  "country_code" varchar(2) NOT NULL,
  "adjustment_percent" decimal NOT NULL,
  "is_active" bool NOT NULL,
  "created_at" datetime NOT NULL
);

CREATE TABLE IF NOT EXISTS "pricing_occupancypricingrule" (
  "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
  "name" varchar(100) NOT NULL,
  "min_occupancy_percent" integer NOT NULL,
  "max_occupancy_percent" integer NOT NULL,
  "adjustment_percent" decimal NOT NULL,
  "is_active" bool NOT NULL,
  "created_at" datetime NOT NULL
);

CREATE TABLE IF NOT EXISTS "pricing_season" (
  "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
  "name" varchar(100) NOT NULL,
  "start_date" date NOT NULL,
  "end_date" date NOT NULL,
  "is_active" bool NOT NULL,
  "created_at" datetime NOT NULL,
  "updated_at" datetime NOT NULL
);

CREATE TABLE IF NOT EXISTS "pricing_pricecalculationlog" (
  "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
  "calculation_snapshot" text NOT NULL,
  "total_price" decimal NOT NULL,
  "ip_address" char(39) NULL,
  "user_agent" text NULL,
  "created_at" datetime NOT NULL,
  "booking_id" bigint NULL UNIQUE REFERENCES "bookings_booking" ("id") DEFERRABLE INITIALLY DEFERRED,
  "scooter_id" bigint NULL REFERENCES "catalog_vehicle" ("id") DEFERRABLE INITIALLY DEFERRED,
  "user_id" bigint NULL REFERENCES "users_user" ("id") DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE IF NOT EXISTS "pricing_scooterseasonprice" (
  "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
  "price_per_day" decimal NOT NULL,
  "created_at" datetime NOT NULL,
  "updated_at" datetime NOT NULL,
  "scooter_id" bigint NOT NULL REFERENCES "catalog_vehicle" ("id") DEFERRABLE INITIALLY DEFERRED,
  "season_id" bigint NOT NULL REFERENCES "pricing_season" ("id") DEFERRABLE INITIALLY DEFERRED
);

CREATE UNIQUE INDEX IF NOT EXISTS "pricing_scooterseasonprice_scooter_id_season_id_uniq" ON "pricing_scooterseasonprice" ("scooter_id", "season_id");
CREATE INDEX IF NOT EXISTS "pricing_sea_start_d_27b9a0_idx" ON "pricing_season" ("start_date", "end_date", "is_active");
CREATE INDEX IF NOT EXISTS "pricing_pri_created_cd278f_idx" ON "pricing_pricecalculationlog" ("created_at");
CREATE INDEX IF NOT EXISTS "pricing_pri_scooter_7b11bd_idx" ON "pricing_pricecalculationlog" ("scooter_id", "created_at");
CREATE INDEX IF NOT EXISTS "pricing_pricecalculationlog_scooter_id_idx" ON "pricing_pricecalculationlog" ("scooter_id");
CREATE INDEX IF NOT EXISTS "pricing_pricecalculationlog_user_id_idx" ON "pricing_pricecalculationlog" ("user_id");

INSERT INTO django_migrations ("app", "name", "applied")
SELECT 'pricing', '0001_initial', CURRENT_TIMESTAMP
WHERE NOT EXISTS (
  SELECT 1 FROM django_migrations WHERE app = 'pricing' AND name = '0001_initial'
);

COMMIT;
