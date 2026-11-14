import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createServiceRequest, fetchMyServiceRequests, fetchServiceCategories, type ServiceCategory } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import "@/pages/ExplorePage.css";

export function ServiceRequestPage() {
  const navigate = useNavigate();
  const [cats, setCats] = useState<ServiceCategory[]>([]);
  const [category, setCategory] = useState("plumbing");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [area, setArea] = useState("");
  const [lat, setLat] = useState("19.1136");
  const [lng, setLng] = useState("72.8697");
  const [budget, setBudget] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchServiceCategories().then(setCats);
    fetchMyServiceRequests().then((r) => {
      if (r.length) setCategory(r[0].category.slug);
    });
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const req = await createServiceRequest({
        category_slug: category,
        title: title.trim(),
        description: description.trim(),
        service_area_label: area.trim(),
        latitude: parseFloat(lat),
        longitude: parseFloat(lng),
        budget_cents: budget ? Math.round(parseFloat(budget) * 100) : undefined,
      });
      navigate(`/app/assistance/requests/${req.id}/offers`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not publish");
    }
  }

  return (
    <div>
      <Link to="/app/explore">← Explore</Link>
      <h1 className="nl-page__title">Post a service request</h1>
      <form className="nl-rental-detail__form" onSubmit={(e) => void onSubmit(e)}>
        <label className="nl-field">
          <span className="nl-field__label">Category</span>
          <select className="nl-explore__select" value={category} onChange={(e) => setCategory(e.target.value)}>
            {cats.map((c) => (
              <option key={c.slug} value={c.slug}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <Input label="Title" value={title} onChange={(e) => setTitle(e.target.value)} required />
        <label className="nl-field">
          <span className="nl-field__label">Description</span>
          <textarea className="nl-profile-textarea" rows={4} value={description} onChange={(e) => setDescription(e.target.value)} required />
        </label>
        <Input label="Area" value={area} onChange={(e) => setArea(e.target.value)} required />
        <Input label="Latitude" value={lat} onChange={(e) => setLat(e.target.value)} required />
        <Input label="Longitude" value={lng} onChange={(e) => setLng(e.target.value)} required />
        <Input label="Budget INR (optional)" value={budget} onChange={(e) => setBudget(e.target.value)} />
        {error ? <p className="nl-auth-form__error">{error}</p> : null}
        <Button type="submit">Publish request</Button>
      </form>
    </div>
  );
}