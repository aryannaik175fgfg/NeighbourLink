# Phase 9 — Escrow & locale

## Done

### Deposit escrow (sandbox)
- `deposit_escrow` row when rental payment succeeds and deposit &gt; 0
- Status: `held` → `released_to_renter` on booking **complete**
- Admin dispute resolve: `deposit_outcome` = `release_renter` | `release_owner`
- Activity shows escrow label; bookings API includes `deposit_escrow_status`

### Localization (shell)
- Catalogs: `en`, `hi`, `mr` — sidebar, mode toggle, tagline, escrow labels
- `LocaleProvider` follows `preferred_locale` from profile / settings

## Not yet
- Full app string coverage (page bodies still mostly English)
- Real payment provider + live escrow settlement
- Community moderation / comments (see `docs/PHASE5.md`)