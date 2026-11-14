import { FormEvent, useEffect, useState } from "react";
import {
  fetchMyPortfolioCategories,
  fetchServiceCategories,
  upsertProviderPortfolio,
  type ProviderCategoryStatus,
  type ServiceCategory,
} from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export function ProviderPortfolioPage() {
  const [cats, setCats] = useState<ServiceCategory[]>([]);
  const [selected, setSelected] = useState<string[]>(["general"]);
  const [headline, setHeadline] = useState("");
  const [intro, setIntro] = useState("");
  const [area, setArea] = useState("");
  const [lat, setLat] = useState("19.1136");
  const [lng, setLng] = useState("72.8697");
  const [msg, setMsg] = useState<string | null>(null);
  const [statuses, setStatuses] = useState<ProviderCategoryStatus[]>([]);

  useEffect(() => {
    fetchServiceCategories().then(setCats);
  }, []);

  function toggle(slug: string) {
    setSelected((s) => (s.includes(slug) ? s.filter((x) => x !== slug) : [...s, slug]));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await upsertProviderPortfolio({
      headline,
      introduction: intro,
      service_area_label: area,
      latitude: parseFloat(lat),
      longitude: parseFloat(lng),
      category_slugs: selected,
    });
    setMsg("Portfolio saved. Provider role granted.");
    try {
      setStatuses(await fetchMyPortfolioCategories());
    } catch {
      setStatuses([]);
    }
  }

  return (
    <div>
      <h1 className="nl-page__title">Provider portfolio</h1>
      <form onSubmit={(e) => void onSubmit(e)} className="nl-rental-detail__form">
        <Input label="Headline" value={headline} onChange={(e) => setHeadline(e.target.value)} required />
        <label className="nl-field">
          <span className="nl-field__label">Introduction</span>
          <textarea className="nl-profile-textarea" rows={4} value={intro} onChange={(e) => setIntro(e.target.value)} required />
        </label>
        <Input label="Service area" value={area} onChange={(e) => setArea(e.target.value)} required />
        <Input label="Latitude" value={lat} onChange={(e) => setLat(e.target.value)} required />
        <Input label="Longitude" value={lng} onChange={(e) => setLng(e.target.value)} required />
        <fieldset>
          <legend>Skills — plumbing &amp; electrical need admin approval before bidding</legend>
          {cats.map((c) => (
            <label key={c.slug} style={{ display: "block", marginBottom: 4 }}>
              <input type="checkbox" checked={selected.includes(c.slug)} onChange={() => toggle(c.slug)} /> {c.name}
              {c.requires_verification ? " (regulated)" : ""}
            </label>
          ))}
        </fieldset>
        {statuses.length > 0 ? (
          <ul className="nl-text-muted" style={{ fontSize: 13 }}>
            {statuses.map((s) => (
              <li key={s.slug}>
                {s.name}: {s.verification_status.replace(/_/g, " ")}
              </li>
            ))}
          </ul>
        ) : null}
        {msg ? <p className="nl-profile-success">{msg}</p> : null}
        <Button type="submit">Save portfolio</Button>
      </form>
    </div>
  );
}