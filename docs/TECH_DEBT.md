# Technical Debt - Bali Scooter Rental

This document identifies areas of the codebase that require refactoring, cleanup, or architectural alignment.

## 1. Logic Duplication

### Promo Codes
- **Status**: Consolidated on `marketing.models.PromoCode`.
- **Current owner**: `marketing.services.MarketingService`.
- **Notes**: API compatibility aliases remain on the marketing model (`value`, `valid_from`, `valid_until`). Do not reintroduce CRM promo code logic.

### Referral Models
- **Status**: Referral ownership moved to the `loyalty` app.
- **Current owner**: `loyalty.services.referrals.ReferralService`.
- **Notes**: `MarketingService.create_referral()` remains as a backward-compatible wrapper only.

### Webhook Logging
- **Found in**: `payments.models.PaymentWebhookEvent`, `crypto_payments.models.CryptoWebhookEvent`, and `audit.models.WebhookProcessingLog`.
- **Status**: `audit.WebhookProcessingLog` is the canonical production log.
- **Current owner**: `audit.services.WebhookLogService`.
- **Notes**: Legacy payment/crypto webhook event models are deprecated compatibility tables. New webhook code should use `WebhookLogService.begin()`, `mark_success()`, and `mark_failure()`.

## 2. Model Cleanup

### Delivery Zones
- **Found in**: `delivery.models.DeliveryZone`.
- **Issue**: Contains legacy fields (`center_lat`, `center_lng`, `radius_km`, `polygon_json`, `free_delivery`) kept for compatibility.
- **Current behavior**: Pricing logic uses polygon matching only. Radius/center fields are not consulted.
- **Migration plan**: Keep fields through the next client release, backfill `polygon` for any real zones that still only have radius data, then remove the legacy fields in a scheduled breaking migration.

### Pricing Rules
- **Found in**: `pricing` app vs `crm` app.
- **Issue**: `crm.models` has `SeasonPriceRule` and `DynamicPriceRule` which overlap with the more advanced `pricing` app models.
- **Recommendation**: Deprecate the CRM pricing models in favor of the specialized `pricing` app.

## 3. Infrastructure & Testing

### Test Coverage
- **Issue**: While `pytest` is configured, the actual test coverage for edge cases in the pricing engine and booking availability collisions needs verification.
- **Recommendation**: Increase unit test coverage for `BookingPriceService` and `BookingCreationService`.

### Media Storage
- **Issue**: Still uses local file storage for sensitive documents (Passports/Licenses).
- **Current guardrails**: Document uploads validate extension, MIME type, size, and use UUID-based server filenames.
- **Recommendation**: Implement `django-storages` with S3 and use private buckets with signed URLs for sensitive user documents.

### Monitoring
- **Current status**: Structured console logs and unified webhook logs are in place.
- **Remaining work**: `sentry-sdk` is not installed. Add it before launch if the client wants exception aggregation, alert routing, and release tracking.

## 4. Documentation
- **Issue**: Swagger UI is available at `/api/schema/swagger-ui/` but some complex service-layer logic (like the exact math of the pricing engine) isn't fully reflected in auto-generated docs.
- **Recommendation**: Add more `@extend_schema` decorators to views to document service-layer outputs.
