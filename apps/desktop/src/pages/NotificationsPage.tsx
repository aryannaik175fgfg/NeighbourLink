import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type AppNotification,
} from "@/lib/api";
import { Button } from "@/components/ui/Button";
import "./NotificationsPage.css";

export function NotificationsPage() {
  const [items, setItems] = useState<AppNotification[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setItems(await fetchNotifications());
  }

  useEffect(() => {
    void load().catch((err) => setError(err instanceof Error ? err.message : "Could not load"));
  }, []);

  async function open(n: AppNotification) {
    if (!n.read_at) {
      await markNotificationRead(n.id);
    }
    await load();
  }

  async function markAll() {
    await markAllNotificationsRead();
    await load();
  }

  return (
    <div>
      <div className="nl-notifications__head">
        <div>
          <h1 className="nl-page__title">Notifications</h1>
          <p className="nl-page__desc">In-app alerts for payments, messages, and verification — no email yet.</p>
        </div>
        {items.some((n) => !n.read_at) ? (
          <Button variant="secondary" onClick={() => void markAll()}>
            Mark all read
          </Button>
        ) : null}
      </div>
      {error ? <p className="nl-auth-form__error">{error}</p> : null}
      {items.length === 0 ? <p className="nl-text-muted">You are all caught up.</p> : null}
      <ul className="nl-notifications__list">
        {items.map((n) => (
          <li key={n.id} className={n.read_at ? "" : "is-unread"}>
            <div className="nl-notifications__card">
              <strong>{n.title}</strong>
              <p>{n.body}</p>
              <time className="nl-text-muted">{new Date(n.created_at).toLocaleString()}</time>
              {n.link_path ? (
                <Link
                  to={n.link_path}
                  className="nl-notifications__link"
                  onClick={() => void open(n)}
                >
                  Open
                </Link>
              ) : (
                <button type="button" className="nl-notifications__dismiss" onClick={() => void open(n)}>
                  Dismiss
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}