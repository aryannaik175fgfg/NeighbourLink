# Phase 3 — Assistance marketplace

## Done

### Map (rentals + assistance)

- OpenStreetMap tiles via Leaflet (`list` / `map` / `split` on Explore)

### Assistance marketplace

- Provider portfolios + PostGIS search
- Service requests, offers, **side-by-side offer comparison**
- One job per request, **sandbox payments**, holds, **progress timeline**
- Job flow: pay → start → submit completion → confirm → **rate provider**
- **Assistance ratings** (separate from rentals; aggregated on provider cards)
- **Job-linked messaging** (conversation per service job)
- **Regulated skills** — plumbing & electrical require **administrator approval** before bidding

## Routes (desktop)

- Assistance: Explore, request, portfolio, open jobs, offer compare
- **Messages** + thread view
- **Admin** — skill verification queue (`administrator` role)
- **My activity** — pay, lifecycle, messages link, review form

## API highlights

- `POST /service-jobs/{id}/review`
- `GET /me/conversations`, `POST /conversations/{id}/messages`
- `GET /admin/skill-verifications`, `POST .../approve|reject`

## Not yet

- Push/email notifications
- Rental-linked messages
- Disputes, trainee/supervisor flows
- Production payment provider