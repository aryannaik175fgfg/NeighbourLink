import { FormEvent, useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import {
  acceptSupervisionRequest,
  declineSupervisionRequest,
  createSupervisionEndorsement,
  enrollAsTrainee,
  fetchMyEndorsements,
  fetchMySupervision,
  fetchPendingSupervision,
  requestSupervisor,
  type SupervisionRow,
  type EndorsementRow,
} from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import "./MentorshipPage.css";

export function MentorshipPage() {
  const { user, hasRole, refreshUser } = useAuth();
  const [rows, setRows] = useState<SupervisionRow[]>([]);
  const [pending, setPending] = useState<SupervisionRow[]>([]);
  const [endorsements, setEndorsements] = useState<EndorsementRow[]>([]);
  const [supervisorEmail, setSupervisorEmail] = useState("");
  const [note, setNote] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function reload() {
    setRows(await fetchMySupervision());
    if (hasRole("supervisor")) {
      setPending(await fetchPendingSupervision());
    }
    if (hasRole("trainee")) {
      setEndorsements(await fetchMyEndorsements());
    }
  }

  useEffect(() => {
    void reload().catch((err) => setError(err instanceof Error ? err.message : "Could not load"));
  }, [hasRole]);

  async function onEnroll() {
    await enrollAsTrainee();
    await refreshUser();
    setMessage("You are enrolled as a trainee. Request a supervisor to start bidding.");
    await reload();
  }

  async function onRequest(e: FormEvent) {
    e.preventDefault();
    await requestSupervisor({ supervisor_email: supervisorEmail.trim(), trainee_note: note.trim() || undefined });
    setMessage("Request sent.");
    setSupervisorEmail("");
    setNote("");
    await reload();
  }

  return (
    <div className="nl-mentorship">
      <header className="nl-page__header">
        <h1 className="nl-page__title">Mentorship</h1>
        <p className="nl-page__desc">
          Trainees develop skills with a supervising neighbour. Active supervision is required before bidding on jobs.
        </p>
      </header>

      {error ? <p className="nl-auth-form__error">{error}</p> : null}
      {message ? <p className="nl-profile-success">{message}</p> : null}

      {!hasRole("trainee") && !hasRole("supervisor") ? (
        <div className="nl-mentorship__card">
          <p>Join the trainee pathway if you are learning a trade and want guided on-platform work.</p>
          <Button onClick={() => void onEnroll()}>Become a trainee</Button>
        </div>
      ) : null}

      {hasRole("trainee") ? (
        <form className="nl-mentorship__card" onSubmit={(e) => void onRequest(e)}>
          <h2>Request a supervisor</h2>
          <Input
            label="Supervisor email"
            type="email"
            value={supervisorEmail}
            onChange={(e) => setSupervisorEmail(e.target.value)}
            required
          />
          <Input label="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
          <Button type="submit">Send request</Button>
        </form>
      ) : null}

      {hasRole("supervisor") && pending.length > 0 ? (
        <section className="nl-mentorship__card">
          <h2>Pending requests</h2>
          <ul className="nl-mentorship__list">
            {pending.map((p) => (
              <li key={p.id}>
                <strong>{p.trainee_name}</strong>
                <p className="nl-text-muted">{p.trainee_note ?? "No note"}</p>
                <Button onClick={() => void acceptSupervisionRequest(p.id).then(reload)}>Accept</Button>
                <Button variant="ghost" onClick={() => void declineSupervisionRequest(p.id).then(reload)}>
                  Decline
                </Button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="nl-mentorship__card">
        <h2>Your relationships</h2>
        {rows.length === 0 ? <p className="nl-text-muted">None yet.</p> : null}
        <ul className="nl-mentorship__list">
          {rows.map((r) => (
            <li key={r.id}>
              <strong>
                {user?.id === r.trainee_id ? r.supervisor_name : r.trainee_name} · {r.status}
              </strong>
            </li>
          ))}
        </ul>
      </section>

      {hasRole("trainee") && endorsements.length > 0 ? (
        <section className="nl-mentorship__card">
          <h2>Endorsements received</h2>
          <ul className="nl-mentorship__list">
            {endorsements.map((e) => (
              <li key={e.id}>
                {e.category_name ? `${e.category_name}: ` : ""}
                {e.note}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {hasRole("supervisor") ? (
        <SupervisorEndorseForm onDone={() => void reload()} />
      ) : null}
    </div>
  );
}

function SupervisorEndorseForm({ onDone }: { onDone: () => void }) {
  const [traineeId, setTraineeId] = useState("");
  const [categorySlug, setCategorySlug] = useState("");
  const [note, setNote] = useState("");

  return (
    <form
      className="nl-mentorship__card"
      onSubmit={(e) => {
        e.preventDefault();
        void createSupervisionEndorsement({
          trainee_id: traineeId.trim(),
          category_slug: categorySlug.trim() || undefined,
          note: note.trim(),
        }).then(onDone);
      }}
    >
      <h2>Endorse a trainee</h2>
      <Input label="Trainee user ID" value={traineeId} onChange={(e) => setTraineeId(e.target.value)} required />
      <Input label="Category slug (optional)" value={categorySlug} onChange={(e) => setCategorySlug(e.target.value)} />
      <Input label="Observation note" value={note} onChange={(e) => setNote(e.target.value)} required />
      <Button type="submit">Record endorsement</Button>
    </form>
  );
}