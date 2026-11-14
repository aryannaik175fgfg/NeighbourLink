import { FormEvent, useCallback, useEffect, useState } from "react";
import { useMarketplaceMode } from "@/context/MarketplaceModeContext";
import { AssistanceExplore } from "@/pages/AssistanceExplore";
import { ListingCard } from "@/components/listings/ListingCard";
import { RentalMap } from "@/components/map/RentalMap";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import {
  fetchRentalCategories,
  fetchUserSettings,
  fetchWishlistIds,
  saveListing,
  searchListings,
  unsaveListing,
  type ListingPublic,
  type RentalCategory,
} from "@/lib/api";
import "./ExplorePage.css";

const DEFAULT_LAT = "19.1136";
const DEFAULT_LNG = "72.8697";

export function ExplorePage() {
  const { mode } = useMarketplaceMode();
  const [categories, setCategories] = useState<RentalCategory[]>([]);
  const [listings, setListings] = useState<ListingPublic[]>([]);
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [sort, setSort] = useState<"relevance" | "price_asc" | "price_desc" | "distance">("relevance");
  const [lat, setLat] = useState(DEFAULT_LAT);
  const [lng, setLng] = useState(DEFAULT_LNG);
  const [radiusKm, setRadiusKm] = useState("25");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<"list" | "map" | "split">("split");
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());

  const runSearch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Parameters<typeof searchListings>[0] = { q: q || undefined, category: category || undefined, sort };
      const latN = parseFloat(lat);
      const lngN = parseFloat(lng);
      if (Number.isFinite(latN) && Number.isFinite(lngN)) {
        params.latitude = latN;
        params.longitude = lngN;
        params.radius_km = parseFloat(radiusKm) || 25;
      }
      const data = await searchListings(params);
      setListings(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setListings([]);
    } finally {
      setLoading(false);
    }
  }, [q, category, sort, lat, lng, radiusKm]);

  useEffect(() => {
    if (mode !== "rental") return;
    fetchRentalCategories()
      .then(setCategories)
      .catch(() => setCategories([]));
    void (async () => {
      let latN = parseFloat(DEFAULT_LAT);
      let lngN = parseFloat(DEFAULT_LNG);
      let radius = 25;
      try {
        const s = await fetchUserSettings();
        if (s.default_latitude != null) {
          latN = s.default_latitude;
          setLat(String(latN));
        }
        if (s.default_longitude != null) {
          lngN = s.default_longitude;
          setLng(String(lngN));
        }
        radius = s.default_radius_km;
        setRadiusKm(String(radius));
      } catch {
        /* use Mumbai defaults */
      }
      try {
        const data = await searchListings({
          sort: "relevance",
          latitude: latN,
          longitude: lngN,
          radius_km: radius,
        });
        setListings(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Search failed");
      }
    })();
    void fetchWishlistIds()
      .then((ids) => setSavedIds(new Set(ids)))
      .catch(() => setSavedIds(new Set()));
  }, [mode]);

  async function toggleSave(listingId: string, shouldSave: boolean) {
    if (shouldSave) {
      await saveListing(listingId);
      setSavedIds((s) => new Set(s).add(listingId));
    } else {
      await unsaveListing(listingId);
      setSavedIds((s) => {
        const next = new Set(s);
        next.delete(listingId);
        return next;
      });
    }
  }

  if (mode !== "rental") {
    return <AssistanceExplore />;
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void runSearch();
  }

  const compactCards = view === "split";

  return (
    <div className="nl-explore">
      <div className="nl-explore__top">
        <header className="nl-page__header">
          <h1 className="nl-page__title">Explore rentals</h1>
          <p className="nl-page__desc">
            Items near you with approximate locations only — exact addresses unlock after booking.
          </p>
        </header>
        <div className="nl-explore__view-tabs" role="tablist" aria-label="Results view">
          {(
            [
              ["list", "List"],
              ["map", "Map"],
              ["split", "List & map"],
            ] as const
          ).map(([v, label]) => (
            <button
              key={v}
              type="button"
              role="tab"
              aria-selected={view === v}
              className={`nl-explore__view-tab ${view === v ? "is-active" : ""}`}
              onClick={() => setView(v)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <form className="nl-explore__filters" onSubmit={onSubmit}>
        <div className="nl-explore__filters-row nl-explore__filters-row--primary">
          <Input label="Search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Drill, camera, speaker…" />
          <label className="nl-field">
            <span className="nl-field__label">Category</span>
            <select className="nl-explore__select" value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">All categories</option>
              {categories.map((c) => (
                <option key={c.slug} value={c.slug}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <label className="nl-field">
            <span className="nl-field__label">Sort</span>
            <select
              className="nl-explore__select"
              value={sort}
              onChange={(e) => setSort(e.target.value as typeof sort)}
            >
              <option value="relevance">Relevance</option>
              <option value="price_asc">Price · low to high</option>
              <option value="price_desc">Price · high to low</option>
              <option value="distance">Distance</option>
            </select>
          </label>
          <Button type="submit" disabled={loading}>
            {loading ? "Searching…" : "Search"}
          </Button>
        </div>
        <div className="nl-explore__filters-row nl-explore__filters-row--location">
          <Input label="Latitude" value={lat} onChange={(e) => setLat(e.target.value)} />
          <Input label="Longitude" value={lng} onChange={(e) => setLng(e.target.value)} />
          <div>
            <Input label="Radius (km)" value={radiusKm} onChange={(e) => setRadiusKm(e.target.value)} />
            <p className="nl-explore__field-hint">Defaults to Mumbai area if unchanged.</p>
          </div>
        </div>
      </form>

      {error ? <p className="nl-explore__error">{error}</p> : null}

      {!loading && listings.length === 0 ? (
        <div className="nl-explore__empty">
          <p>No listings in this area yet.</p>
          <p className="nl-explore__empty-hint">Try a wider radius or add a listing under My listings.</p>
        </div>
      ) : (
        <div className={`nl-explore__split nl-explore__split--${view}`}>
          {(view === "list" || view === "split") && (
            <div className="nl-explore__list-pane">
              <div className="nl-explore__grid">
                {listings.map((listing) => (
                  <ListingCard
                    key={listing.id}
                    listing={listing}
                    compact={compactCards}
                    isSaved={savedIds.has(listing.id)}
                    onToggleSave={(id, next) => void toggleSave(id, next)}
                  />
                ))}
              </div>
            </div>
          )}
          {(view === "map" || view === "split") && listings.length > 0 ? (
            <div className="nl-explore__map-pane">
              <RentalMap listings={listings} />
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}