BEGIN TRANSACTION;

INSERT INTO catalog_vehicletype (code, name)
SELECT 'maxi', 'Maxi Scooter'
WHERE NOT EXISTS (
  SELECT 1 FROM catalog_vehicletype WHERE code = 'maxi'
);

INSERT INTO catalog_vehicletype (code, name)
SELECT 'moto', 'Motorcycle'
WHERE NOT EXISTS (
  SELECT 1 FROM catalog_vehicletype WHERE code = 'moto'
);

UPDATE catalog_vehiclemodel
SET
  name = 'PCX 160',
  brand = 'Honda',
  engine_cc = 160,
  transmission = 'Automatic',
  fuel_consumption = 2.1,
  year = 2024,
  trunk = '30L',
  helmets_count = 2,
  description = 'Premium scooter for Bali city rides and longer island routes.',
  rental_terms = 'Helmet included. Minimum age 18. International driving permit recommended.',
  type_id = (SELECT id FROM catalog_vehicletype WHERE code = 'scooter')
WHERE id = 1;

INSERT INTO catalog_vehiclemodel (name, brand, engine_cc, transmission, fuel_consumption, year, trunk, helmets_count, description, rental_terms, type_id)
SELECT 'NMAX 155', 'Yamaha', 155, 'Automatic', 2.0, 2024, '25L', 2, 'Comfortable maxi scooter for longer Bali travel.', 'Helmet included. Minimum age 18. International driving permit recommended.', (SELECT id FROM catalog_vehicletype WHERE code = 'maxi')
WHERE NOT EXISTS (
  SELECT 1 FROM catalog_vehiclemodel WHERE brand = 'Yamaha' AND name = 'NMAX 155' AND year = 2024
);

INSERT INTO catalog_vehiclemodel (name, brand, engine_cc, transmission, fuel_consumption, year, trunk, helmets_count, description, rental_terms, type_id)
SELECT 'ADV 150', 'Honda', 150, 'Automatic', 2.3, 2024, '28L', 2, 'Adventure-inspired scooter for varied Bali roads.', 'Helmet included. Minimum age 18. International driving permit recommended.', (SELECT id FROM catalog_vehicletype WHERE code = 'maxi')
WHERE NOT EXISTS (
  SELECT 1 FROM catalog_vehiclemodel WHERE brand = 'Honda' AND name = 'ADV 150' AND year = 2024
);

INSERT INTO catalog_vehiclemodel (name, brand, engine_cc, transmission, fuel_consumption, year, trunk, helmets_count, description, rental_terms, type_id)
SELECT 'Aerox 155', 'Yamaha', 155, 'Automatic', 1.9, 2024, '24L', 2, 'Sporty scooter with responsive handling for urban routes.', 'Helmet included. Minimum age 18. International driving permit recommended.', (SELECT id FROM catalog_vehicletype WHERE code = 'scooter')
WHERE NOT EXISTS (
  SELECT 1 FROM catalog_vehiclemodel WHERE brand = 'Yamaha' AND name = 'Aerox 155' AND year = 2024
);

INSERT INTO catalog_vehiclemodel (name, brand, engine_cc, transmission, fuel_consumption, year, trunk, helmets_count, description, rental_terms, type_id)
SELECT 'Vario 160', 'Honda', 160, 'Automatic', 2.0, 2024, '18L', 2, 'Reliable everyday scooter with balanced performance.', 'Helmet included. Minimum age 18. International driving permit recommended.', (SELECT id FROM catalog_vehicletype WHERE code = 'scooter')
WHERE NOT EXISTS (
  SELECT 1 FROM catalog_vehiclemodel WHERE brand = 'Honda' AND name = 'Vario 160' AND year = 2024 AND id <> 1
);

INSERT INTO catalog_vehiclemodel (name, brand, engine_cc, transmission, fuel_consumption, year, trunk, helmets_count, description, rental_terms, type_id)
SELECT 'Meteor 350', 'Royal Enfield', 350, 'Manual', 3.5, 2023, 'Touring Ready', 1, 'Classic motorcycle with relaxed ergonomics for long scenic rides.', 'Experienced riders only. Helmet included. International driving permit recommended.', (SELECT id FROM catalog_vehicletype WHERE code = 'moto')
WHERE NOT EXISTS (
  SELECT 1 FROM catalog_vehiclemodel WHERE brand = 'Royal Enfield' AND name = 'Meteor 350'
);

UPDATE catalog_vehicle
SET
  title = 'Honda PCX 160',
  slug = 'honda-pcx-160',
  sku = 'PCX-160-001',
  color = 'Matte Black',
  base_price_usd = 5.50,
  status = 'available',
  mileage = 4200,
  rating_avg = 4.9,
  reviews_count = 124,
  is_featured = 1,
  created_at = COALESCE(created_at, CURRENT_TIMESTAMP),
  model_id = 1
WHERE id = 1;

INSERT INTO catalog_vehicle (title, slug, sku, color, base_price_usd, status, mileage, rating_avg, reviews_count, is_featured, created_at, model_id)
SELECT 'Yamaha NMAX 155', 'yamaha-nmax-155', 'NMAX-155-001', 'Midnight Blue', 6.20, 'available', 3100, 4.8, 98, 1, CURRENT_TIMESTAMP, (
  SELECT id FROM catalog_vehiclemodel WHERE brand = 'Yamaha' AND name = 'NMAX 155' AND year = 2024 LIMIT 1
)
WHERE NOT EXISTS (
  SELECT 1 FROM catalog_vehicle WHERE slug = 'yamaha-nmax-155'
);

INSERT INTO catalog_vehicle (title, slug, sku, color, base_price_usd, status, mileage, rating_avg, reviews_count, is_featured, created_at, model_id)
SELECT 'Honda ADV 150', 'honda-adv-150', 'ADV-150-001', 'Graphite Black', 7.10, 'available', 2900, 4.9, 67, 1, CURRENT_TIMESTAMP, (
  SELECT id FROM catalog_vehiclemodel WHERE brand = 'Honda' AND name = 'ADV 150' AND year = 2024 LIMIT 1
)
WHERE NOT EXISTS (
  SELECT 1 FROM catalog_vehicle WHERE slug = 'honda-adv-150'
);

INSERT INTO catalog_vehicle (title, slug, sku, color, base_price_usd, status, mileage, rating_avg, reviews_count, is_featured, created_at, model_id)
SELECT 'Yamaha Aerox 155', 'yamaha-aerox-155', 'AEROX-155-001', 'Onyx', 5.20, 'available', 5100, 4.7, 112, 0, CURRENT_TIMESTAMP, (
  SELECT id FROM catalog_vehiclemodel WHERE brand = 'Yamaha' AND name = 'Aerox 155' AND year = 2024 LIMIT 1
)
WHERE NOT EXISTS (
  SELECT 1 FROM catalog_vehicle WHERE slug = 'yamaha-aerox-155'
);

INSERT INTO catalog_vehicle (title, slug, sku, color, base_price_usd, status, mileage, rating_avg, reviews_count, is_featured, created_at, model_id)
SELECT 'Honda Vario 160', 'honda-vario-160', 'VARIO-160-001', 'Deep Plum', 4.50, 'rented', 3900, 4.6, 89, 0, CURRENT_TIMESTAMP, (
  SELECT id FROM catalog_vehiclemodel WHERE brand = 'Honda' AND name = 'Vario 160' AND year = 2024 AND id <> 1 LIMIT 1
)
WHERE NOT EXISTS (
  SELECT 1 FROM catalog_vehicle WHERE slug = 'honda-vario-160'
);

INSERT INTO catalog_vehicle (title, slug, sku, color, base_price_usd, status, mileage, rating_avg, reviews_count, is_featured, created_at, model_id)
SELECT 'Royal Enfield Meteor 350', 'royal-enfield-meteor', 'METEOR-350-001', 'Fireball Red', 12.70, 'available', 1800, 5.0, 43, 1, CURRENT_TIMESTAMP, (
  SELECT id FROM catalog_vehiclemodel WHERE brand = 'Royal Enfield' AND name = 'Meteor 350' LIMIT 1
)
WHERE NOT EXISTS (
  SELECT 1 FROM catalog_vehicle WHERE slug = 'royal-enfield-meteor'
);

UPDATE addons_addon
SET
  code = 'helmet_full',
  name = 'Full-Face Helmet',
  description = 'Premium full-face helmet.',
  price_usd = 1.00,
  price_type = 'per_day',
  is_active = 1,
  sort_order = 1,
  updated_at = CURRENT_TIMESTAMP
WHERE code = 'helmet_extra';

UPDATE addons_addon
SET
  code = 'insurance',
  name = 'Full Insurance',
  description = 'Complete protection against accidents.',
  price_usd = 1.60,
  price_type = 'per_day',
  is_active = 1,
  sort_order = 2,
  updated_at = CURRENT_TIMESTAMP
WHERE code = 'insurance_full';

INSERT INTO addons_addon (code, name, description, price_usd, price_type, is_active, sort_order, created_at, updated_at)
SELECT 'gps', 'GPS Navigator', 'Offline Bali maps loaded.', 1.30, 'per_day', 1, 3, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM addons_addon WHERE code = 'gps');

INSERT INTO addons_addon (code, name, description, price_usd, price_type, is_active, sort_order, created_at, updated_at)
SELECT 'raincoat', 'Rain Poncho', 'Lightweight waterproof cover.', 0.60, 'per_day', 1, 4, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM addons_addon WHERE code = 'raincoat');

INSERT INTO addons_addon (code, name, description, price_usd, price_type, is_active, sort_order, created_at, updated_at)
SELECT 'phone_mount', 'Phone Mount', 'Universal secure mount.', 0.60, 'per_day', 1, 5, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM addons_addon WHERE code = 'phone_mount');

INSERT INTO addons_addon (code, name, description, price_usd, price_type, is_active, sort_order, created_at, updated_at)
SELECT 'wifi', 'Pocket WiFi 4G', 'Unlimited data in Bali.', 2.30, 'per_day', 1, 6, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM addons_addon WHERE code = 'wifi');

INSERT INTO addons_addon (code, name, description, price_usd, price_type, is_active, sort_order, created_at, updated_at)
SELECT 'helmet_open', 'Open-Face Helmet', 'Half helmet with open airflow.', 0.60, 'per_day', 1, 7, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM addons_addon WHERE code = 'helmet_open');

INSERT INTO addons_addon (code, name, description, price_usd, price_type, is_active, sort_order, created_at, updated_at)
SELECT 'bag', 'Rear Bag', 'Water-resistant rear storage bag.', 1.00, 'per_day', 1, 8, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM addons_addon WHERE code = 'bag');

UPDATE delivery_deliveryzone
SET
  name = 'Seminyak',
  center_lat = -8.6900,
  center_lng = 115.1680,
  radius_km = 7.0,
  free_delivery = 1,
  base_price_usd = 0.00,
  price_per_km_usd = 0.50,
  is_active = 1,
  updated_at = CURRENT_TIMESTAMP
WHERE id = 1;

INSERT INTO delivery_deliveryzone (name, polygon_json, center_lat, center_lng, radius_km, free_delivery, base_price_usd, price_per_km_usd, is_active, created_at, updated_at)
SELECT 'Canggu', NULL, -8.6480, 115.1380, 7.0, 1, 0.00, 0.50, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM delivery_deliveryzone WHERE name = 'Canggu');

INSERT INTO delivery_deliveryzone (name, polygon_json, center_lat, center_lng, radius_km, free_delivery, base_price_usd, price_per_km_usd, is_active, created_at, updated_at)
SELECT 'Kuta', NULL, -8.7220, 115.1720, 6.0, 1, 0.00, 0.50, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM delivery_deliveryzone WHERE name = 'Kuta');

INSERT INTO delivery_deliveryzone (name, polygon_json, center_lat, center_lng, radius_km, free_delivery, base_price_usd, price_per_km_usd, is_active, created_at, updated_at)
SELECT 'Legian', NULL, -8.7090, 115.1685, 6.0, 1, 0.00, 0.50, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM delivery_deliveryzone WHERE name = 'Legian');

INSERT INTO delivery_deliveryzone (name, polygon_json, center_lat, center_lng, radius_km, free_delivery, base_price_usd, price_per_km_usd, is_active, created_at, updated_at)
SELECT 'Denpasar', NULL, -8.6500, 115.2160, 8.0, 1, 0.00, 0.50, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM delivery_deliveryzone WHERE name = 'Denpasar');

INSERT INTO delivery_deliveryzone (name, polygon_json, center_lat, center_lng, radius_km, free_delivery, base_price_usd, price_per_km_usd, is_active, created_at, updated_at)
SELECT 'Jimbaran', NULL, -8.7900, 115.1680, 8.0, 0, 1.60, 0.50, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM delivery_deliveryzone WHERE name = 'Jimbaran');

INSERT INTO delivery_deliveryzone (name, polygon_json, center_lat, center_lng, radius_km, free_delivery, base_price_usd, price_per_km_usd, is_active, created_at, updated_at)
SELECT 'Sanur', NULL, -8.6920, 115.2630, 8.0, 0, 1.60, 0.50, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM delivery_deliveryzone WHERE name = 'Sanur');

INSERT INTO delivery_deliveryzone (name, polygon_json, center_lat, center_lng, radius_km, free_delivery, base_price_usd, price_per_km_usd, is_active, created_at, updated_at)
SELECT 'Ubud', NULL, -8.5069, 115.2625, 10.0, 0, 3.20, 0.60, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM delivery_deliveryzone WHERE name = 'Ubud');

INSERT INTO delivery_deliveryzone (name, polygon_json, center_lat, center_lng, radius_km, free_delivery, base_price_usd, price_per_km_usd, is_active, created_at, updated_at)
SELECT 'Nusa Dua', NULL, -8.8070, 115.2300, 9.0, 0, 3.20, 0.60, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM delivery_deliveryzone WHERE name = 'Nusa Dua');

INSERT INTO delivery_deliveryzone (name, polygon_json, center_lat, center_lng, radius_km, free_delivery, base_price_usd, price_per_km_usd, is_active, created_at, updated_at)
SELECT 'Uluwatu', NULL, -8.8290, 115.0840, 10.0, 0, 4.80, 0.70, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM delivery_deliveryzone WHERE name = 'Uluwatu');

COMMIT;
