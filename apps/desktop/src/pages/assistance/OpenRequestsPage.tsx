import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchOpenServiceRequests, submitServiceOffer, type ServiceRequest } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export function OpenRequestsPage() {
  const [requests, setRequests] = useState<ServiceRequest[]>([]);
  const [price, setPrice] = useState("1500");
  const [included, setIncluded] = useState("");
  const [target, setTarget] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    void fetchOpenServiceRequests().then(setRequests);
  }, []);

  async function onOffer(e: FormEvent, requestId: string) {
    e.preventDefault();
    const cents = Math.round(parseFloat(price) * 100);
    await submitServiceOffer(requestId, {
      price_cents: cents,
      included_work: included || "Labour and basic materials as discussed",
    });
    setMessage("Offer sent.");
    setTarget(null);
    setRequests(await fetchOpenServiceRequests());
  }

  return (
    <div>
      <Link to="/app/explore">← Explore</Link>
      <h1 className="nl-page__title">Open service requests</h1>
      <ul className="nl-activity__list">
        {requests.map((r) => (
          <li key={r.id} className="nl-activity__card">
            <strong>{r.title}</strong>
            <p className="nl-text-muted">
              {r.category.name} · {r.service_area_label} · {r.offer_count} offers
            </p>
            <p>{r.description}</p>
            <Link to={`/app/assistance/requests/${r.id}/offers`}>View as customer</Link>
            {target === r.id ? (
              <form onSubmit={(e) => void onOffer(e, r.id)}>
                <Input label="Price INR" value={price} onChange={(e) => setPrice(e.target.value)} />
                <Input label="Included work" value={included} onChange={(e) => setIncluded(e.target.value)} />
                <Button type="submit">Submit offer</Button>
              </form>
            ) : (
              <Button onClick={() => setTarget(r.id)}>Send offer</Button>
            )}
          </li>
        ))}
      </ul>
      {message ? <p className="nl-profile-success">{message}</p> : null}
    </div>
  );
}