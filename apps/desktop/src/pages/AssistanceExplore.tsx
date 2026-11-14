import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { DiscoveryMap } from "@/components/map/DiscoveryMap";
import {
  fetchServiceCategories,
  searchProviders,
  type ProviderPublic,
  type ServiceCategory,
} from "@/lib/api";
import "./AssistanceExplore.css";
import "./ExplorePage.css";

export function AssistanceExplore() {
  const [categories, setCategories] = useState<ServiceCategory[]>([]);
  const [providers, setProviders] = useState<ProviderPublic[]>([]);
  const [category, setCategory] = useState("");
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [view, setView] = useState<"list" | "map" | "split">("split");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSearch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Parameters<typeof searchProviders>[0] = { category: category || undefined };
      const latN = parseFloat(lat);
      const lngN = parseFloat(lng);
      if (Number.isFinite(latN) && Number.isFinite(lngN)) {
        params.latitude = latN;
        params.longitude = lngN;
        params.radius_km = 25;
      }
      setProviders(await searchProviders(params));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setProviders([]);
    } finally {
      setLoading(false);
    }
  }, [category, lat, lng]);

  useEffect(() => {
    fetchServiceCategories().then(setCategories).catch(() => setCategories([]));
    void runSearch();
  }, []);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void runSearch();
  }

  const mapPoints = providers.map((p) => ({
    id: p.user_id,
    title: p.headline,
    latitude: p.latitude,
    longitude: p.longitude,
    subtitle: p.service_area_label,
  }));

  return (
    <div className="nl-assist-explore">
      <header className="nl-page__header">
        <h1 className="nl-page__title">Find local services</h1>
        <p className="nl-page__desc">
          Discover providers by skill and distance. Separate assistance ratings — &quot;No ratings yet&quot; until
          verified reviews exist.
        </p>
      </header>

      <div className="nl-assist-explore__actions">
        <Link to="/app/assistance/request" className="nl-assist-explore__cta">
          Post a service request
        </Link>
        <Link to="/app/assistance/portfolio" className="nl-assist-explore__cta nl-assist-explore__cta--secondary">
          Provider portfolio
        </Link>
        <Link to="/app/assistance/open-jobs" className="nl-assist-explore__cta nl-assist-explore__cta--secondary">
          Browse open requests
        </Link>
      </div>

      <form className="nl-explore__filters" onSubmit={onSubmit}>
        <label className="nl-field">
          <span className="nl-field__label">Category</span>
          <select className="nl-explore__select" value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">All services</option>
            {categories.map((c) => (
              <option key={c.slug} value={c.slug}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <Input label="Latitude" value={lat} onChange={(e) => setLat(e.target.value)} placeholder="19.1136" />
        <Input label="Longitude" value={lng} onChange={(e) => setLng(e.target.value)} placeholder="72.8697" />
        <Button type="submit" disabled={loading}>
          {loading ? "Searching…" : "Search"}
        </Button>
      </form>

      <div className="nl-explore__view-tabs" role="tablist">
        {(["list", "map", "split"] as const).map((v) => (
          <button
            key={v}
            type="button"
            role="tab"
            className={`nl-explore__view-tab ${view === v ? "is-active" : ""}`}
            onClick={() => setView(v)}
          >
            {v === "split" ? "List & map" : v}
          </button>
        ))}
      </div>

      {error ? <p className="nl-explore__error">{error}</p> : null}

      <div className={`nl-explore__split nl-explore__split--${view}`}>
        {(view === "list" || view === "split") && (
          <div className="nl-assist-explore__grid">
            {providers.map((p) => (
              <article key={p.user_id} className="nl-assist-card">
                <h3>{p.headline}</h3>
                <p className="nl-assist-card__area">{p.service_area_label}</p>
                <p className="nl-assist-card__intro">{p.introduction}</p>
                <p className="nl-assist-card__meta">
                  {p.display_name}
                  {p.distance_meters != null ? ` · ${(p.distance_meters / 1000).toFixed(1)} km` : ""}
                </p>
                <p className="nl-assist-card__rating">
                  {p.assistance_rating_count > 0
                    ? `${p.assistance_rating} (${p.assistance_rating_count} reviews)`
                    : "No ratings yet"}
                </p>
              </article>
            ))}
          </div>
        )}
        {(view === "map" || view === "split") && <DiscoveryMap points={mapPoints} />}
      </div>
    </div>
  );
}