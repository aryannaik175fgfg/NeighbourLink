# Phase 2 (in progress) — Rental listings

## Shipped in this slice

- `rental_categories` + `items` with PostGIS `location` (GIST index)
- APIs: `GET /rental-categories`, `GET /listings` (search + distance), `GET /listings/{id}`, `POST /listings`, `GET /me/listings`, `PATCH /listings/{id}`
- Public responses omit `exact_address`; owners see it on manage endpoints
- First listing grants `item_owner` role (backend only)
- Desktop: **Explore rentals** search UI + **My listings** create form

## Shipped in payment slice

- Sandbox `payments` + idempotent `payment_events`
- HMAC webhook `POST /api/v1/webhooks/payments` (`X-NL-Signature: sha256=…`)
- `payment-intent` + dev `sandbox-pay` (renter only)
- 24h hold on owner accept; auto-`expired` when listing activity loads
- Lifecycle: `confirmed` → `active` (pickup) → `returned` → `completed`

## Next (still Phase 2)

- Item photos / object storage
- Real payment provider + production webhooks
- Map discovery view
- Condition reports at pickup/return

## Local run checklist

1. Start **Docker Desktop**, wait until running.
2. `docker compose up -d`
3. Backend: `scripts\dev-backend.ps1` or steps in root `README.md`
4. Desktop: `cd apps\desktop` → `npm run dev`