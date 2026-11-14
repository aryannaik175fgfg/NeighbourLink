import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { acceptServiceOffer, fetchMyServiceRequests, fetchRequestOffers, type ServiceOffer } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import "./RequestOffersPage.css";

function inr(cents: number) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(
    cents / 100
  );
}

export function RequestOffersPage() {
  const { requestId } = useParams<{ requestId: string }>();
  const [offers, setOffers] = useState<ServiceOffer[]>([]);
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!requestId) return;
    const [o, mine] = await Promise.all([fetchRequestOffers(requestId), fetchMyServiceRequests()]);
    setOffers(o);
    setTitle(mine.find((r) => r.id === requestId)?.title ?? "Request");
  }

  useEffect(() => {
    void load();
  }, [requestId]);

  const sorted = useMemo(
    () => [...offers].sort((a, b) => a.price_cents - b.price_cents || a.estimated_days - b.estimated_days),
    [offers]
  );

  async function pick(offerId: string) {
    try {
      await acceptServiceOffer(offerId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not accept");
    }
  }

  return (
    <div>
      <h1 className="nl-page__title">Compare offers</h1>
      <p className="nl-page__desc">
        {title} — compare scope and price side by side. We never auto-select the lowest bid; you choose who to trust.
      </p>
      {error ? <p className="nl-auth-form__error">{error}</p> : null}
      {sorted.length === 0 ? (
        <p className="nl-text-muted">No offers yet. Check back after neighbours respond.</p>
      ) : (
        <div className="nl-table-scroll">
          <table className="nl-offer-compare">
            <thead>
              <tr>
                <th scope="col">Provider</th>
                <th scope="col">Price</th>
                <th scope="col">Est. time</th>
                <th scope="col">Included</th>
                <th scope="col">Excluded</th>
                <th scope="col">Status</th>
                <th scope="col">Action</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((o) => (
                <tr key={o.id}>
                  <td>
                    <strong>{o.provider_name}</strong>
                  </td>
                  <td className="nl-offer-compare__price">{inr(o.price_cents)}</td>
                  <td>~{o.estimated_days} day(s)</td>
                  <td className="nl-offer-compare__work">{o.included_work}</td>
                  <td className="nl-offer-compare__work">{o.excluded_work ?? "—"}</td>
                  <td>{o.status.replace(/_/g, " ")}</td>
                  <td>
                    {o.status === "pending" ? (
                      <Button onClick={() => void pick(o.id)}>Accept</Button>
                    ) : (
                      <span className="nl-text-muted">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}