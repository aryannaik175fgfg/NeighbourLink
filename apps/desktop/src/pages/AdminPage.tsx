import { useEffect, useState } from "react";
import {
  approveIdentity,
  approveSkillVerification,
  fetchAdminDisputes,
  fetchAuditLog,
  fetchPendingIdentityVerifications,
  fetchPendingSkillVerifications,
  rejectIdentity,
  rejectSkillVerification,
  resolveAdminDispute,
  fetchAdminCommunityPosts,
  hideCommunityPost,
  type AuditRow,
  type CommunityPost,
  type DisputeRow,
  type IdentityAdminRow,
  type SkillVerificationRow,
} from "@/lib/api";
import { Button } from "@/components/ui/Button";
import "./AdminPage.css";

type Tab = "skills" | "identity" | "disputes" | "community" | "audit";

export function AdminPage() {
  const [tab, setTab] = useState<Tab>("skills");
  const [skills, setSkills] = useState<SkillVerificationRow[]>([]);
  const [identity, setIdentity] = useState<IdentityAdminRow[]>([]);
  const [disputes, setDisputes] = useState<DisputeRow[]>([]);
  const [audit, setAudit] = useState<AuditRow[]>([]);
  const [communityPosts, setCommunityPosts] = useState<CommunityPost[]>([]);
  const [hideReasons, setHideReasons] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [resolveNotes, setResolveNotes] = useState<Record<string, string>>({});
  const [depositOutcomes, setDepositOutcomes] = useState<Record<string, "release_renter" | "release_owner" | "">>({});

  async function loadSkills() {
    setSkills(await fetchPendingSkillVerifications());
  }

  async function loadIdentity() {
    setIdentity(await fetchPendingIdentityVerifications());
  }

  async function loadDisputes() {
    setDisputes(await fetchAdminDisputes());
  }

  async function loadAudit() {
    setAudit(await fetchAuditLog());
  }

  async function loadCommunity() {
    setCommunityPosts(await fetchAdminCommunityPosts());
  }

  useEffect(() => {
    setError(null);
    const run = async () => {
      try {
        if (tab === "skills") await loadSkills();
        if (tab === "identity") await loadIdentity();
        if (tab === "disputes") await loadDisputes();
        if (tab === "community") await loadCommunity();
        if (tab === "audit") await loadAudit();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load");
      }
    };
    void run();
  }, [tab]);

  return (
    <div className="nl-admin">
      <h1 className="nl-page__title">Administration</h1>
      <p className="nl-page__desc">Skills, identity, disputes, and audit trail.</p>

      <div className="nl-admin__tabs" role="tablist">
        {(
          [
            ["skills", "Skills"],
            ["identity", "Identity"],
            ["disputes", "Disputes"],
            ["community", "Community"],
            ["audit", "Audit log"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            className={`nl-admin__tab ${tab === key ? "is-active" : ""}`}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {error ? <p className="nl-auth-form__error">{error}</p> : null}

      {tab === "skills" ? (
        <ul className="nl-admin-queue">
          {skills.length === 0 ? <p className="nl-text-muted">No pending skill verifications.</p> : null}
          {skills.map((r) => (
            <li key={`${r.portfolio_user_id}-${r.category_id}`} className="nl-admin-queue__card">
              <strong>
                {r.provider_name} — {r.category_name}
              </strong>
              <p>{r.provider_headline}</p>
              <div className="nl-admin-queue__actions">
                <Button onClick={() => void approveSkillVerification(r.portfolio_user_id, r.category_id, "Approved").then(loadSkills)}>
                  Approve
                </Button>
                <Button
                  variant="danger"
                  onClick={() =>
                    void rejectSkillVerification(
                      r.portfolio_user_id,
                      r.category_id,
                      "Documentation did not meet platform requirements."
                    ).then(loadSkills)
                  }
                >
                  Reject
                </Button>
              </div>
            </li>
          ))}
        </ul>
      ) : null}

      {tab === "identity" ? (
        <ul className="nl-admin-queue">
          {identity.length === 0 ? <p className="nl-text-muted">No pending identity checks.</p> : null}
          {identity.map((r) => (
            <li key={r.user_id} className="nl-admin-queue__card">
              <strong>
                {r.display_name} ({r.email})
              </strong>
              <p>
                {r.document_type.toUpperCase()} · ref {r.document_reference}
              </p>
              {r.user_note ? <p>{r.user_note}</p> : null}
              <div className="nl-admin-queue__actions">
                <Button onClick={() => void approveIdentity(r.user_id, "Verified").then(loadIdentity)}>Approve</Button>
                <Button variant="danger" onClick={() => void rejectIdentity(r.user_id, "Could not verify documents.").then(loadIdentity)}>
                  Reject
                </Button>
              </div>
            </li>
          ))}
        </ul>
      ) : null}

      {tab === "disputes" ? (
        <ul className="nl-admin-queue">
          {disputes.length === 0 ? <p className="nl-text-muted">No disputes.</p> : null}
          {disputes.map((d) => (
            <li key={d.id} className="nl-admin-queue__card">
              <strong>
                {d.subject_type} · {d.status}
              </strong>
              <p>{d.reason}</p>
              {d.status === "open" || d.status === "under_review" ? (
                <>
                  <textarea
                    className="nl-profile-textarea"
                    rows={2}
                    placeholder="Resolution notes"
                    value={resolveNotes[d.id] ?? ""}
                    onChange={(e) => setResolveNotes((m) => ({ ...m, [d.id]: e.target.value }))}
                  />
                  {d.subject_type === "rental_booking" ? (
                    <label className="nl-field">
                      <span className="nl-field__label">Deposit outcome (if held)</span>
                      <select
                        className="nl-settings__select"
                        value={depositOutcomes[d.id] ?? ""}
                        onChange={(e) =>
                          setDepositOutcomes((m) => ({
                            ...m,
                            [d.id]: e.target.value as "release_renter" | "release_owner" | "",
                          }))
                        }
                      >
                        <option value="">No change</option>
                        <option value="release_renter">Refund deposit to renter</option>
                        <option value="release_owner">Pay deposit to owner</option>
                      </select>
                    </label>
                  ) : null}
                  <div className="nl-admin-queue__actions">
                    <Button
                      onClick={() =>
                        void resolveAdminDispute(
                          d.id,
                          "resolved",
                          resolveNotes[d.id] ?? "Resolved per policy.",
                          depositOutcomes[d.id] || undefined
                        ).then(loadDisputes)
                      }
                    >
                      Mark resolved
                    </Button>
                  </div>
                </>
              ) : (
                <p className="nl-text-muted">{d.resolution_notes}</p>
              )}
            </li>
          ))}
        </ul>
      ) : null}

      {tab === "community" ? (
        <ul className="nl-admin-queue">
          {communityPosts.length === 0 ? <p className="nl-text-muted">No community posts.</p> : null}
          {communityPosts.map((p) => (
            <li key={p.id} className="nl-admin-queue__card">
              <strong>{p.title}</strong>
              <p className="nl-text-muted">
                {p.kind} · {p.author_name}
              </p>
              <p>{p.body.slice(0, 200)}</p>
              <textarea
                className="nl-profile-textarea"
                rows={2}
                placeholder="Moderation reason"
                value={hideReasons[p.id] ?? ""}
                onChange={(e) => setHideReasons((m) => ({ ...m, [p.id]: e.target.value }))}
              />
              <Button
                variant="danger"
                onClick={() =>
                  void hideCommunityPost(p.id, hideReasons[p.id] ?? "Removed for policy violation.").then(loadCommunity)
                }
              >
                Hide post
              </Button>
            </li>
          ))}
        </ul>
      ) : null}

      {tab === "audit" ? (
        <ul className="nl-admin-audit">
          {audit.map((a) => (
            <li key={a.id}>
              <time>{new Date(a.created_at).toLocaleString()}</time>
              <span>
                {a.action} · {a.target_type}/{a.target_id}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}