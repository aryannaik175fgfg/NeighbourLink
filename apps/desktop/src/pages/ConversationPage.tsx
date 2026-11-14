import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchConversation, sendConversationMessage, type ConversationThread } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import "./MessagesPage.css";

export function ConversationPage() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const [thread, setThread] = useState<ConversationThread | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!conversationId) return;
    setThread(await fetchConversation(conversationId));
  }

  useEffect(() => {
    void load().catch((err) => setError(err instanceof Error ? err.message : "Could not load"));
  }, [conversationId]);

  async function onSend(e: FormEvent) {
    e.preventDefault();
    if (!conversationId || !draft.trim()) return;
    await sendConversationMessage(conversationId, draft.trim());
    setDraft("");
    await load();
  }

  if (!thread) return <p className="nl-text-muted">Loading…</p>;

  return (
    <div className="nl-conversation">
      <Link to="/app/messages" className="nl-rental-detail__back">
        All messages
      </Link>
      <h1 className="nl-page__title">{thread.job_title}</h1>
      <p className="nl-page__desc">
        With {thread.partner_name} · Job status: {thread.job_status.replace(/_/g, " ")}
      </p>
      {error ? <p className="nl-auth-form__error">{error}</p> : null}
      <ul className="nl-conversation__messages">
        {thread.messages.map((m) => (
          <li key={m.id} className={m.is_mine ? "is-mine" : ""}>
            <strong>{m.is_mine ? "You" : m.sender_name}</strong>
            <p>{m.body}</p>
            <time className="nl-text-muted">{new Date(m.created_at).toLocaleString()}</time>
          </li>
        ))}
      </ul>
      <form className="nl-conversation__composer" onSubmit={(e) => void onSend(e)}>
        <textarea rows={3} value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Write a message…" />
        <Button type="submit">Send</Button>
      </form>
    </div>
  );
}