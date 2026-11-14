import { FormEvent, useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { fetchIdentity, submitIdentity, updateProfile, type IdentityStatus } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import "./ProfilePage.css";

export function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const [displayName, setDisplayName] = useState(user?.profile.display_name ?? "");
  const [bio, setBio] = useState(user?.profile.bio ?? "");
  const [location, setLocation] = useState(user?.profile.approximate_location ?? "");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [identity, setIdentity] = useState<IdentityStatus | null>(null);
  const [docType, setDocType] = useState("pan");
  const [docRef, setDocRef] = useState("");
  const [idNote, setIdNote] = useState("");

  useEffect(() => {
    if (!user) return;
    setDisplayName(user.profile.display_name);
    setBio(user.profile.bio ?? "");
    setLocation(user.profile.approximate_location ?? "");
  }, [user]);

  useEffect(() => {
    void fetchIdentity()
      .then(setIdentity)
      .catch(() => setIdentity(null));
  }, [user]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setSaving(true);
    try {
      await updateProfile({
        display_name: displayName.trim(),
        bio: bio.trim() || null,
        approximate_location: location.trim() || null,
      });
      await refreshUser();
      setMessage("Profile saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save profile");
    } finally {
      setSaving(false);
    }
  }

  if (!user) return null;

  return (
    <div className="nl-page">
      <header className="nl-page__header">
        <h1 className="nl-page__title">My profile</h1>
        <p className="nl-page__desc">Your trust profile grows with verified activity and neighbour feedback.</p>
      </header>

      <div className="nl-profile-grid">
        <form className="nl-profile-card" onSubmit={(e) => void onSubmit(e)}>
          <h2 className="nl-profile-card__title">Public details</h2>
          <Input label="Display name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} required />
          <label className="nl-field">
            <span className="nl-field__label">Bio</span>
            <textarea
              className="nl-profile-textarea"
              rows={4}
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              maxLength={1000}
            />
          </label>
          <Input
            label="Approximate area (city / neighbourhood)"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. Andheri West, Mumbai"
          />
          {error ? <p className="nl-auth-form__error">{error}</p> : null}
          {message ? <p className="nl-profile-success">{message}</p> : null}
          <Button type="submit" disabled={saving}>
            {saving ? "Saving…" : "Save changes"}
          </Button>
        </form>

        <form
          className="nl-profile-card"
          onSubmit={(e) => {
            e.preventDefault();
            void submitIdentity({
              document_type: docType,
              document_reference: docRef.trim(),
              user_note: idNote.trim() || undefined,
            })
              .then(setIdentity)
              .then(() => setMessage("Identity submitted for review."))
              .catch((err) => setError(err instanceof Error ? err.message : "Could not submit"));
          }}
        >
          <h2 className="nl-profile-card__title">Identity verification</h2>
          {identity?.status === "approved" ? (
            <p className="nl-profile-success">Verified — {identity.document_type.toUpperCase()}</p>
          ) : identity?.status === "pending" ? (
            <p className="nl-text-muted">Pending review (submitted {new Date(identity.submitted_at).toLocaleDateString()}).</p>
          ) : identity?.status === "rejected" ? (
            <p className="nl-auth-form__error">{identity.admin_note ?? "Not approved — you may resubmit."}</p>
          ) : (
            <p className="nl-text-muted">Submit masked ID reference only — never upload full document numbers in chat.</p>
          )}
          {identity?.status !== "approved" && identity?.status !== "pending" ? (
            <>
              <label className="nl-field">
                <span className="nl-field__label">Document type</span>
                <select className="nl-settings__select" value={docType} onChange={(e) => setDocType(e.target.value)}>
                  <option value="pan">PAN</option>
                  <option value="aadhaar">Aadhaar (last 4)</option>
                  <option value="passport">Passport</option>
                  <option value="other">Other</option>
                </select>
              </label>
              <Input label="Masked reference" value={docRef} onChange={(e) => setDocRef(e.target.value)} required minLength={4} />
              <Input label="Note (optional)" value={idNote} onChange={(e) => setIdNote(e.target.value)} />
              <Button type="submit" variant="secondary">
                Submit for verification
              </Button>
            </>
          ) : null}
        </form>

        <aside className="nl-profile-card nl-profile-card--meta">
          <h2 className="nl-profile-card__title">Account</h2>
          <dl className="nl-profile-dl">
            <dt>Email</dt>
            <dd>{user.email}</dd>
            <dt>Roles</dt>
            <dd>
              <ul className="nl-profile-roles">
                {user.roles.map((r) => (
                  <li key={r.slug}>{r.name}</li>
                ))}
              </ul>
            </dd>
            <dt>Member since</dt>
            <dd>{new Date(user.created_at).toLocaleDateString()}</dd>
          </dl>
        </aside>
      </div>
    </div>
  );
}
