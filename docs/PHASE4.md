# Phase 4 — Platform alerts & cross-cutting UX

## Done

### In-app notifications

- `notifications` table + dedupe keys
- Emitted on bookings, assistance, messages, skills, identity, disputes
- Desktop: Notifications page, sidebar badge, deep links

### Wishlists

- Saved items page + Explore cards

### Delivery & ops

- **Windows toast** — Electron `Notification` via preload IPC when new unread arrives (poll)
- **Email stub** — `notification_delivery.deliver_email` logs when `SMTP_HOST` unset
- **Request logging** — structured HTTP middleware + `X-Request-Id`
- **Readiness** — `GET /ready` (DB ping), `GET /health`
- **Windows packaging** — `npm run dist:win` (electron-builder NSIS)

## Optional env

```
SMTP_HOST=
SMTP_FROM=
```