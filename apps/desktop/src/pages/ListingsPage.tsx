import { FormEvent, useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import {
  createListing,
  fetchMyListings,
  uploadListingPhoto,
  fetchRentalCategories,
  type ListingCreateBody,
  type ListingOwner,
  type RentalCategory,
} from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import "@/pages/ExplorePage.css";
import "./ListingsPage.css";

function formatInr(cents: number) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(
    cents / 100
  );
}

export function ListingsPage() {
  const { refreshUser } = useAuth();
  const [mine, setMine] = useState<ListingOwner[]>([]);
  const [categories, setCategories] = useState<RentalCategory[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const [form, setForm] = useState({
    category_slug: "power-tools",
    title: "",
    description: "",
    condition: "good" as ListingCreateBody["condition"],
    daily_price_inr: "",
    deposit_inr: "0",
    public_area_label: "",
    exact_address: "",
    latitude: "",
    longitude: "",
    pickup_instructions: "",
  });

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [items, cats] = await Promise.all([fetchMyListings(), fetchRentalCategories()]);
      setMine(items);
      setCategories(cats);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load listings");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setMessage(null);
    const daily = Math.round(parseFloat(form.daily_price_inr) * 100);
    const deposit = Math.round(parseFloat(form.deposit_inr || "0") * 100);
    const lat = parseFloat(form.latitude);
    const lng = parseFloat(form.longitude);
    if (!Number.isFinite(daily) || daily < 100) {
      setError("Enter a valid daily price in INR.");
      setSubmitting(false);
      return;
    }
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      setError("Latitude and longitude are required for nearby discovery.");
      setSubmitting(false);
      return;
    }
    try {
      await createListing({
        category_slug: form.category_slug,
        title: form.title.trim(),
        description: form.description.trim(),
        condition: form.condition,
        daily_price_cents: daily,
        deposit_cents: deposit,
        public_area_label: form.public_area_label.trim(),
        exact_address: form.exact_address.trim() || null,
        latitude: lat,
        longitude: lng,
        pickup_instructions: form.pickup_instructions.trim() || null,
      });
      await refreshUser();
      await load();
      setMessage("Listing published. You now have the item owner role for managing rentals.");
      setForm((f) => ({ ...f, title: "", description: "" }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create listing");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="nl-listings-page">
      <header className="nl-page__header">
        <h1 className="nl-page__title">My listings</h1>
        <p className="nl-page__desc">Publish rentable items. Your first listing grants the item owner role automatically.</p>
      </header>

      <div className="nl-listings-page__layout">
        <form className="nl-listings-form" onSubmit={(e) => void onSubmit(e)}>
          <h2 className="nl-listings-form__title">New listing</h2>
          <label className="nl-field">
            <span className="nl-field__label">Category</span>
            <select
              className="nl-explore__select"
              value={form.category_slug}
              onChange={(e) => setForm((f) => ({ ...f, category_slug: e.target.value }))}
            >
              {categories.map((c) => (
                <option key={c.slug} value={c.slug}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <Input label="Title" value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} required />
          <label className="nl-field">
            <span className="nl-field__label">Description</span>
            <textarea
              className="nl-profile-textarea"
              rows={4}
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              required
              minLength={10}
            />
          </label>
          <label className="nl-field">
            <span className="nl-field__label">Condition</span>
            <select
              className="nl-explore__select"
              value={form.condition}
              onChange={(e) => setForm((f) => ({ ...f, condition: e.target.value as ListingCreateBody["condition"] }))}
            >
              <option value="new">New</option>
              <option value="like_new">Like new</option>
              <option value="good">Good</option>
              <option value="fair">Fair</option>
            </select>
          </label>
          <Input
            label="Daily price (INR)"
            type="number"
            min="1"
            step="1"
            value={form.daily_price_inr}
            onChange={(e) => setForm((f) => ({ ...f, daily_price_inr: e.target.value }))}
            required
          />
          <Input
            label="Refundable deposit (INR)"
            type="number"
            min="0"
            step="1"
            value={form.deposit_inr}
            onChange={(e) => setForm((f) => ({ ...f, deposit_inr: e.target.value }))}
          />
          <Input
            label="Public area label"
            value={form.public_area_label}
            onChange={(e) => setForm((f) => ({ ...f, public_area_label: e.target.value }))}
            placeholder="Neighbourhood shown in search"
            required
          />
          <Input
            label="Exact address (private until booking)"
            value={form.exact_address}
            onChange={(e) => setForm((f) => ({ ...f, exact_address: e.target.value }))}
          />
          <Input label="Latitude" value={form.latitude} onChange={(e) => setForm((f) => ({ ...f, latitude: e.target.value }))} required />
          <Input label="Longitude" value={form.longitude} onChange={(e) => setForm((f) => ({ ...f, longitude: e.target.value }))} required />
          <Input
            label="Pickup instructions"
            value={form.pickup_instructions}
            onChange={(e) => setForm((f) => ({ ...f, pickup_instructions: e.target.value }))}
          />
          {error ? <p className="nl-auth-form__error">{error}</p> : null}
          {message ? <p className="nl-profile-success">{message}</p> : null}
          <Button type="submit" disabled={submitting}>
            {submitting ? "Publishing…" : "Publish listing"}
          </Button>
        </form>

        <section className="nl-listings-owned">
          <h2 className="nl-listings-form__title">Your listings</h2>
          {loading ? <p className="nl-text-muted">Loading…</p> : null}
          {!loading && mine.length === 0 ? <p className="nl-text-muted">No listings yet.</p> : null}
          <ul className="nl-listings-owned__list">
            {mine.map((item) => (
              <li key={item.id} className="nl-listings-owned__item">
                <div className="nl-listings-owned__head">
                  <strong>{item.title}</strong>
                  <span className="nl-listings-owned__status">{item.status}</span>
                </div>
                <p className="nl-listings-owned__meta">
                  {formatInr(item.daily_price_cents)}/day · {item.public_area_label}
                </p>
                <label className="nl-field">
                  <span className="nl-field__label">Add photo</span>
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp,image/gif"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      void uploadListingPhoto(item.id, file).then(() => load());
                    }}
                  />
                </label>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}