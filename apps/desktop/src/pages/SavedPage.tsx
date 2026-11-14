import { useCallback, useEffect, useState } from "react";
import { fetchWishlist, unsaveListing, type ListingPublic } from "@/lib/api";
import { ListingCard } from "@/components/listings/ListingCard";

export function SavedPage() {
  const [items, setItems] = useState<ListingPublic[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setItems(await fetchWishlist());
  }, []);

  useEffect(() => {
    void load().catch((err) => setError(err instanceof Error ? err.message : "Could not load"));
  }, [load]);

  async function remove(id: string) {
    await unsaveListing(id);
    await load();
  }

  return (
    <div>
      <header className="nl-page__header">
        <h1 className="nl-page__title">Saved items</h1>
        <p className="nl-page__desc">Listings you want to revisit — no price alerts yet.</p>
      </header>
      {error ? <p className="nl-auth-form__error">{error}</p> : null}
      {items.length === 0 ? (
        <p className="nl-text-muted">Nothing saved yet. Use Save on a rental listing while you browse.</p>
      ) : (
        <div className="nl-explore__grid">
          {items.map((l) => (
            <ListingCard key={l.id} listing={l} isSaved onToggleSave={(id) => void remove(id)} />
          ))}
        </div>
      )}
    </div>
  );
}