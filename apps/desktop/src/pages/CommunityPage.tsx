import { FormEvent, useCallback, useEffect, useState } from "react";
import { createCommunityPost, fetchCommunityPosts, type CommunityPost } from "@/lib/api";
import { CommunityPostCard } from "@/components/community/CommunityPostCard";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import "./CommunityPage.css";

const DEFAULT_LAT = "19.1136";
const DEFAULT_LNG = "72.8697";

export function CommunityPage() {
  const [posts, setPosts] = useState<CommunityPost[]>([]);
  const [kind, setKind] = useState("");
  const [lat, setLat] = useState(DEFAULT_LAT);
  const [lng, setLng] = useState(DEFAULT_LNG);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [area, setArea] = useState("");
  const [postKind, setPostKind] = useState<"recommendation" | "question" | "announcement">("recommendation");
  const [linkedListingId, setLinkedListingId] = useState("");

  function patchPost(updated: CommunityPost) {
    setPosts((prev) => prev.map((p) => (p.id === updated.id ? { ...p, ...updated } : p)));
  }

  const load = useCallback(async () => {
    const latN = parseFloat(lat);
    const lngN = parseFloat(lng);
    setPosts(
      await fetchCommunityPosts({
        kind: kind || undefined,
        latitude: Number.isFinite(latN) ? latN : undefined,
        longitude: Number.isFinite(lngN) ? lngN : undefined,
      })
    );
  }, [kind, lat, lng]);

  useEffect(() => {
    void load().catch((err) => setError(err instanceof Error ? err.message : "Could not load"));
  }, [load]);

  async function onPublish(e: FormEvent) {
    e.preventDefault();
    setError(null);
    await createCommunityPost({
      kind: postKind,
      title,
      body,
      area_label: area,
      latitude: parseFloat(lat),
      longitude: parseFloat(lng),
      linked_listing_id: linkedListingId.trim() || undefined,
    });
    setTitle("");
    setBody("");
    setArea("");
    setShowForm(false);
    await load();
  }

  return (
    <div className="nl-community">
      <header className="nl-community__head">
        <div>
          <h1 className="nl-page__title">Community</h1>
          <p className="nl-page__desc">
            Recommendations, questions, and local announcements from neighbours — separate from marketplace listings.
          </p>
        </div>
        <Button onClick={() => setShowForm((v) => !v)}>{showForm ? "Cancel" : "New post"}</Button>
      </header>

      {showForm ? (
        <form className="nl-community__compose" onSubmit={(e) => void onPublish(e)}>
          <label className="nl-field">
            <span className="nl-field__label">Type</span>
            <select
              className="nl-community__select"
              value={postKind}
              onChange={(e) => setPostKind(e.target.value as typeof postKind)}
            >
              <option value="recommendation">Recommendation</option>
              <option value="question">Question</option>
              <option value="announcement">Announcement</option>
            </select>
          </label>
          <Input label="Title" value={title} onChange={(e) => setTitle(e.target.value)} required />
          <Input label="Area" value={area} onChange={(e) => setArea(e.target.value)} required />
          <Input
            label="Link listing ID (optional)"
            value={linkedListingId}
            onChange={(e) => setLinkedListingId(e.target.value)}
            placeholder="UUID from a rental listing"
          />
          <label className="nl-field">
            <span className="nl-field__label">Body</span>
            <textarea className="nl-community__textarea" rows={4} value={body} onChange={(e) => setBody(e.target.value)} required />
          </label>
          <Button type="submit">Publish</Button>
        </form>
      ) : null}

      <div className="nl-community__filters">
        <label className="nl-field">
          <span className="nl-field__label">Filter</span>
          <select className="nl-community__select" value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="">All types</option>
            <option value="recommendation">Recommendations</option>
            <option value="question">Questions</option>
            <option value="announcement">Announcements</option>
          </select>
        </label>
        <Input label="Lat" value={lat} onChange={(e) => setLat(e.target.value)} />
        <Input label="Lng" value={lng} onChange={(e) => setLng(e.target.value)} />
        <Button variant="secondary" onClick={() => void load()}>
          Refresh feed
        </Button>
      </div>

      {error ? <p className="nl-auth-form__error">{error}</p> : null}

      <ul className="nl-community__feed">
        {posts.length === 0 ? (
          <li className="nl-community__empty">No posts nearby yet. Be the first to share something useful.</li>
        ) : (
          posts.map((p) => <CommunityPostCard key={p.id} post={p} onUpdate={patchPost} />)
        )}
      </ul>
    </div>
  );
}