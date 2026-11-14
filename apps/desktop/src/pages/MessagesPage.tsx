import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchMyConversations, type ConversationSummary } from "@/lib/api";
import "./MessagesPage.css";

export function MessagesPage() {
  const [threads, setThreads] = useState<ConversationSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchMyConversations()
      .then(setThreads)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load messages"));
  }, []);

  return (
    <div>
      <h1 className="nl-page__title">Messages</h1>
      <p className="nl-page__desc">Rental and service threads with people you are transacting with — not anonymous chat.</p>
      {error ? <p className="nl-auth-form__error">{error}</p> : null}
      {threads.length === 0 ? <p className="nl-text-muted">No conversations yet. Accept a service offer to open a thread.</p> : null}
      <ul className="nl-messages-list">
        {threads.map((t) => (
          <li key={t.id}>
            <Link to={`/app/messages/${t.id}`} className="nl-messages-list__item">
              <strong>
                {t.kind === "rental_booking" ? "Rental · " : ""}
                {t.job_title}
              </strong>
              <span className="nl-text-muted">{t.partner_name}</span>
              <p className="nl-messages-list__preview">{t.last_message_preview ?? "No messages yet"}</p>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}