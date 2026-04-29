# API Reference - Bali Scooter Rental Backend

This document provides a comprehensive reference for all endpoints available in the Bali Scooter Rental API.

## Base URL
- Production: `https://api.balirental.com/api/v1/`
- Staging: `https://staging-api.balirental.com/api/v1/`
- Local: `http://localhost:8000/api/v1/`

## Authentication
Most endpoints require JWT authentication. 
Include the token in the `Authorization` header: `Authorization: Bearer <your_access_token>`

---

## 1. Auth & Profile

### Register
- **URL**: `/auth/register/`
- **Method**: `POST`
- **Purpose**: Create a new client account.
- **Authentication**: None
- **Request Fields**: `email`, `password`, `username`, `full_name`, `phone`
- **Response**: User object with token.
- **Rate limit**: Scoped by `THROTTLE_REGISTER`.

### Login
- **URL**: `/auth/login/`
- **Method**: `POST`
- **Purpose**: Obtain JWT access and refresh tokens.
- **Authentication**: None
- **Request Fields**: `email`, `password`
- **Response**: `access`, `refresh`
- **Rate limit**: Scoped by `THROTTLE_LOGIN`.

### Logout
- **URL**: `/auth/logout/`
- **Method**: `POST`
- **Purpose**: Blacklist the refresh token.
- **Authentication**: Required
- **Request Fields**: `refresh`

### Profile
- **URL**: `/profile/`
- **Method**: `GET`, `PATCH`
- **Purpose**: Get or update current user profile details.
- **Authentication**: Required

---

## 2. Catalog (Scooters)

### List Scooters
- **URL**: `/scooters/`
- **Method**: `GET`
- **Purpose**: Browse available scooters.
- **Filters**: `status`, `type`, `min_price`, `max_price`, `is_featured`
- **Search**: `title`, `model`, `brand`
- **Availability Params**: `start_date`, `end_date` can be supplied to include availability without extra per-scooter checks.

### Scooter Details
- **URL**: `/scooters/{id}/`
- **Method**: `GET`
- **Purpose**: Detailed info including images and specifications.

### Popular Scooters
- **URL**: `/scooters/popular/`
- **Method**: `GET`
- **Purpose**: Get featured and high-rated scooters.

### Check Availability
- **URL**: `/scooters/{id}/availability/`
- **Method**: `GET`
- **Purpose**: Check if a scooter is available for specific dates or get a calendar view.
- **Params**: `year`, `month` OR `start_date`, `end_date`

---

## 3. Add-ons

### List Add-ons
- **URL**: `/add-ons/`
- **Method**: `GET`
- **Purpose**: List extra items (helmets, raincoats, etc.) available for rent.

---

## 4. Bookings

### Create Booking
- **URL**: `/bookings/`
- **Method**: `POST`
- **Purpose**: Initiate a new rental booking.
- **Request Fields**: `scooter_id`, `start_datetime`, `end_datetime`, `add_on_ids`, `promo_code`, `payment_method`, `delivery_address`, `delivery_latitude`, `delivery_longitude`, `currency`

### Calculate Price
- **URL**: `/bookings/calculate/`
- **Method**: `POST`
- **Purpose**: Get price breakdown before creating a booking. Same request fields as Create Booking.
- **Rate limit**: Scoped by `THROTTLE_PRICING_CALCULATE`.

### My Bookings
- **URL**: `/bookings/`
- **Method**: `GET`
- **Purpose**: List bookings for the authenticated user.

### Cancel Booking
- **URL**: `/bookings/{id}/cancel/`
- **Method**: `POST`
- **Purpose**: Cancel a pending or confirmed booking.

---

## 5. Pricing (Advanced)

### Calculate Full Price
- **URL**: `/pricing/calculate/`
- **Method**: `POST`
- **Purpose**: Advanced price calculation engine accounting for seasons, occupancy, device, and geo-rules.

---

## 6. Payments

### Create Payment
- **URL**: `/payments/create/`
- **Method**: `POST`
- **Purpose**: Create a payment session (e.g., Stripe Checkout).
- **Rate limit**: Scoped by `THROTTLE_PAYMENT_CREATE`.

### Crypto Invoice
- **URL**: `/payments/crypto/invoice/create/`
- **Method**: `POST`
- **Purpose**: Generate a crypto payment address and invoice.

---

## 7. Documents

### Upload Document
- **URL**: `/documents/`
- **Method**: `POST`
- **Purpose**: Upload passport or driver's license for verification.
- **Fields**: `document_type`, `file`
- **Accepted files**: JPG, PNG, PDF only. Max size 5 MB.

### My Documents
- **URL**: `/documents/my/`
- **Method**: `GET`
- **Purpose**: Check status of uploaded documents.

---

## 8. Marketing

### Validate Promo Code
- **URL**: `/marketing/promocodes/validate/`
- **Method**: `POST`
- **Purpose**: Verify if a promo code is valid and get discount amount.
- **Rate limit**: Scoped by `THROTTLE_PROMO_VALIDATE`.

### Banners
- **URL**: `/banners/`
- **Method**: `GET`
- **Purpose**: Get active promotional banners for home or catalog.

---

## 9. Notifications

### Register Device
- **URL**: `/notifications/register-device/`
- **Method**: `POST`
- **Purpose**: Register FCM token for push notifications.

### List Notifications
- **URL**: `/notifications/`
- **Method**: `GET`
- **Purpose**: Get in-app notification history.

---

## 10. Reviews

### List Reviews
- **URL**: `/reviews/`
- **Method**: `GET`
- **Purpose**: Get approved reviews. Can be filtered by `scooter_id`.

### Submit Review
- **URL**: `/scooters/{id}/reviews/`
- **Method**: `POST`
- **Purpose**: Submit a new review after booking.

---

## 11. Admin Endpoints
Admin endpoints are located under `/api/v1/admin/` and require Admin/Manager roles.

- `/admin/scooters/`: Full CRUD for fleet.
- `/admin/bookings/`: Manage all customer bookings.
- `/admin/users/`: Manage users and roles.
- `/admin/pricing/`: Manage seasons and dynamic rules.
- `/admin/audit/`: View system-wide audit logs.
- `/admin/security/webhooks/`: View normalized webhook processing logs.
- `/admin/analytics/revenue/`: Financial reporting.
- `/admin/analytics/funnel/`: Conversion tracking.

---

## 12. Analytics Events

### Track Event
- **URL**: `/analytics/events/`
- **Method**: `POST`
- **Purpose**: Capture client analytics events.
- **Rate limit**: Scoped by `THROTTLE_ANALYTICS_EVENTS`.

---

## Error Responses
The API uses standard HTTP status codes:
- `400 Bad Request`: Validation errors (returns JSON with field errors).
- `401 Unauthorized`: Token missing or expired.
- `403 Forbidden`: Insufficient permissions.
- `404 Not Found`: Resource does not exist.
- `429 Too Many Requests`: Rate limit exceeded.
- `500 Internal Server Error`: Unexpected server error.
