import { useEffect, useState } from "react";
import { fetchMyDisputes, type DisputeRow } from "@/lib/api";
import "./DisputesPage.css";

export function DisputesPage() {
  const [rows, setRows] = useState<DisputeRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchMyDisputes()
      .then(setRows)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load"));
  }, []);

  return (
    <div>
      <header className="nl-page__header">
        <h1 className="nl-page__title">Disputes</h1>
        <p className="nl-page__desc">Cases you opened or are party to. Administrators resolve them under Platform rules.</p>
      </header>
      {error ? <p className="nl-auth-form__error">{error}</p> : null}
      {rows.length === 0 ? <p className="nl-text-muted">No disputes yet.</p> : null}
      <ul className="nl-disputes-list">
        {rows.map((d) => (
          <li key={d.id} className="nl-disputes-list__card">
            <div className="nl-disputes-list__head">
              <strong>{d.subject_type.replace(/_/g, " ")}</strong>
              <span>{d.status.replace(/_/g, " ")}</span>
            </div>
            <p className="nl-text-muted">Opened {new Date(d.created_at).toLocaleString()}</p>
            <p>{d.reason}</p>
            {d.resolution_notes ? <p className="nl-disputes-list__resolution">Resolution: {d.resolution_notes}</p> : null}
          </li>
        ))}
      </ul>
    </div>
  );
}