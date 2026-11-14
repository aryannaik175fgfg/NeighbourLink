# Phase 7 — Trust & safety

## Done

- **Identity verification** — masked document reference, admin approve/reject, profile UI
- **Disputes** — rental bookings & service jobs, status + admin resolution, activity “Open dispute”
- **Admin audit log** — skill, identity, dispute actions
- **Admin console** — tabs: Skills, Identity, Disputes, Audit

## API

- `GET/POST /me/identity`
- `GET/POST /disputes`, `GET /disputes/mine`
- Admin: identity queue, dispute resolve, `GET /admin/audit-log`

## Not yet

- Escrow release automation tied to dispute outcomes
- Document upload to secure vault (references only today)