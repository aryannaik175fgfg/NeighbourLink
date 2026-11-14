import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import {
  addCommunityComment,
  fetchCommunityPostDetail,
  setCommunityReaction,
  type CommunityPost,
  type CommunityPostDetail,
} from "@/lib/api";
import { Button } from "@/components/ui/Button";

type Props = {
  post: CommunityPost;
  onUpdate: (post: CommunityPost) => void;
};

export function CommunityPostCard({ post, onUpdate }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [detail, setDetail] = useState<CommunityPostDetail | null>(null);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);

  async function toggleExpand() {
    if (!expanded) {
      const d = await fetchCommunityPostDetail(post.id);
      setDetail(d);
      onUpdate(d);
    }
    setExpanded((v) => !v);
  }

  async function react(reaction: "helpful" | "thanks") {
    const updated = await setCommunityReaction(post.id, reaction);
    onUpdate(updated);
    if (detail) setDetail({ ...detail, ...updated, comments: detail.comments });
  }

  async function submitComment(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await addCommunityComment(post.id, comment.trim());
      setComment("");
      const d = await fetchCommunityPostDetail(post.id);
      setDetail(d);
      onUpdate(d);
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="nl-community__card">
      <div className="nl-community__card-head">
        <span className={`nl-community__kind nl-community__kind--${post.kind}`}>{post.kind}</span>
        {post.is_mine ? <span className="nl-community__mine">You</span> : null}
      </div>
      <h2 className="nl-community__title">{post.title}</h2>
      <p className="nl-community__meta">
        {post.author_name} · {post.area_label} · {new Date(post.created_at).toLocaleDateString()}
      </p>
      {post.linked_listing_title ? (
        <p className="nl-community__link">
          Linked listing:{" "}
          {post.linked_listing_id ? (
            <Link to={`/app/rentals/${post.linked_listing_id}`}>{post.linked_listing_title}</Link>
          ) : (
            post.linked_listing_title
          )}
        </p>
      ) : null}
      <p className="nl-community__body">{post.body}</p>
      <div className="nl-community__actions">
        <Button variant={post.my_reaction === "helpful" ? "primary" : "ghost"} type="button" onClick={() => void react("helpful")}>
          Helpful ({post.helpful_count ?? 0})
        </Button>
        <Button variant={post.my_reaction === "thanks" ? "primary" : "ghost"} type="button" onClick={() => void react("thanks")}>
          Thanks ({post.thanks_count ?? 0})
        </Button>
        <Button variant="ghost" type="button" onClick={() => void toggleExpand()}>
          {expanded ? "Hide" : "Comments"} ({post.comment_count ?? 0})
        </Button>
      </div>
      {expanded && detail ? (
        <>
          <ul className="nl-community__comments">
            {detail.comments.map((c) => (
              <li key={c.id}>
                <strong>{c.author_name}</strong>
                <span className="nl-text-muted"> · {new Date(c.created_at).toLocaleString()}</span>
                <p>{c.body}</p>
              </li>
            ))}
          </ul>
          <form className="nl-community__comment-form" onSubmit={(e) => void submitComment(e)}>
            <input
              className="nl-field__input"
              placeholder="Add a neighbourly reply…"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              required
            />
            <Button type="submit" disabled={busy}>
              Reply
            </Button>
          </form>
        </>
      ) : null}
    </li>
  );
}