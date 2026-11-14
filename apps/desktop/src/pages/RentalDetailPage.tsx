import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import {
  fetchBookingQuote,
  fetchListing,
  fetchListingAvailability,
  fetchWishlistIds,
  requestBooking,
  saveListing,
  unsaveListing,
  type BookingQuote,
  type ItemAvailability,
  type ListingPublic,
} from "@/lib/api";
import "./RentalDetailPage.css";
import "@/pages/ProfilePage.css";

function formatInr(cents: number) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(
    cents / 100
  );
}

export function RentalDetailPage() {
  const { listingId } = useParams<{ listingId: string }>();
  const [listing, setListing] = useState<ListingPublic | null>(null);
  const [availability, setAvailability] = useState<ItemAvailability | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [note, setNote] = useState("");
  const [quote, setQuote] = useState<BookingQuote | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [isSaved, setIsSaved] = useState(false);

  useEffect(() => {
    if (!listingId) return;
    setLoading(true);
    Promise.all([fetchListing(listingId), fetchListingAvailability(listingId)])
      .then(([l, a]) => {
        setListing(l);
        setAvailability(a);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"))
      .finally(() => setLoading(false));
    void fetchWishlistIds()
      .then((ids) => setIsSaved(ids.includes(listingId ?? "")))
      .catch(() => setIsSaved(false));
  }, [listingId]);

  useEffect(() => {
    if (!listingId || !startDate || !endDate) {
      setQuote(null);
      return;
    }
    fetchBookingQuote(listingId, startDate, endDate)
      .then(setQuote)
      .catch(() => setQuote(null));
  }, [listingId, startDate, endDate]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!listingId) return;
    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      await requestBooking(listingId, {
        start_date: startDate,
        end_date: endDate,
        renter_note: note.trim() || undefined,
      });
      setMessage("Request sent. The owner will accept or decline. Payment comes next in Phase 2b.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not request booking");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <p className="nl-text-muted">Loading listing…</p>;
  if (!listing) return <p className="nl-auth-form__error">{error ?? "Listing not found"}</p>;

  return (
    <div className="nl-rental-detail">
      <Link to="/app/explore" className="nl-rental-detail__back">
        ← Back to explore
      </Link>
      <header className="nl-page__header nl-rental-detail__header">
        <div>
          <h1 className="nl-page__title">{listing.title}</h1>
          <p className="nl-page__desc">
            {listing.public_area_label} · {listing.category.name} · {listing.owner_display_name}
          </p>
        </div>
        <Button
          variant={isSaved ? "secondary" : "ghost"}
          onClick={() =>
            void (isSaved ? unsaveListing(listing.id) : saveListing(listing.id)).then(() => setIsSaved(!isSaved))
          }
        >
          {isSaved ? "Saved" : "Save for later"}
        </Button>
      </header>

      <div className="nl-rental-detail__grid">
        <section className="nl-rental-detail__main">
          <p>{listing.description}</p>
          <p className="nl-rental-detail__price">
            {formatInr(listing.daily_price_cents)} <span>/ day</span>
            {listing.deposit_cents > 0 ? <> · deposit {formatInr(listing.deposit_cents)}</> : null}
          </p>
        </section>

        <section className="nl-rental-detail__book">
          <h2>Request dates</h2>
          <p className="nl-rental-detail__hint">Start and end are both inclusive rental days.</p>
          <form onSubmit={(e) => void onSubmit(e)} className="nl-rental-detail__form">
            <Input label="Start date" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
            <Input label="End date" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} required />
            <Input label="Note to owner" value={note} onChange={(e) => setNote(e.target.value)} />
            {quote ? (
              <div className="nl-rental-detail__quote" aria-live="polite">
                <p>
                  {quote.rental_days} days · subtotal {formatInr(quote.subtotal_cents)}
                </p>
                <p className="nl-rental-detail__quote-total">Total due at payment: {formatInr(quote.total_cents)}</p>
              </div>
            ) : null}
            {error ? <p className="nl-auth-form__error">{error}</p> : null}
            {message ? <p className="nl-profile-success">{message}</p> : null}
            <Button type="submit" disabled={submitting}>
              {submitting ? "Sending…" : "Send booking request"}
            </Button>
          </form>
        </section>
      </div>

      {availability && availability.busy.length > 0 ? (
        <section className="nl-rental-detail__busy">
          <h3>Unavailable ranges</h3>
          <ul>
            {availability.busy.map((b, i) => (
              <li key={`${b.kind}-${i}`}>
                {b.start_date} → {b.end_date} ({b.kind})
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}