# Phase 1 — Foundation

## Delivered

- [x] Monorepo + Docker PostGIS
- [x] FastAPI app with modular routers
- [x] Users, profiles, roles, refresh sessions
- [x] Argon2id password hashing
- [x] Electron shell (context isolation + preload bridge)
- [x] Design tokens (forest green / ivory palette)
- [x] Auth screens (login / register)
- [x] App shell: sidebar, Rental|Assistance mode, route placeholders

## Not in Phase 1

- Listings, bookings, payments, messaging (Phase 2+)
- Map discovery, object storage uploads
- Admin workspace beyond route guard stub

## Default roles (seeded)

| Slug | Name |
|------|------|
| `customer` | Customer / renter |
| `item_owner` | Item owner |
| `provider` | Independent service provider |
| `trainee` | Trainee |
| `supervisor` | Supervisor |
| `administrator` | Administrator |

New users receive `customer` only. Elevated roles require administrator APIs (Phase 7).
