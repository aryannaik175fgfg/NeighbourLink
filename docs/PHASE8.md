# Phase 8 — Connectivity & growth

## Done

### Rental messaging
- `rental_conversations` + `rental_messages`
- Thread opens when owner **accepts** a booking
- Unified inbox: `GET /me/conversations` (service + rental)
- `GET /rental-bookings/{id}/conversation`
- Activity → **Messages** on rentals

### Trainee / supervisor
- Supervision requests, accept/decline, active relationship
- Trainees must have active supervision before bidding
- Endorsements from supervisors
- Desktop **Mentorship** page + trainee enroll

### Session management
- `GET /me/sessions`, revoke one, `POST /me/sessions/revoke-others`
- Settings → **Signed-in devices**

## Not yet
- Full-string i18n
- Production payment provider