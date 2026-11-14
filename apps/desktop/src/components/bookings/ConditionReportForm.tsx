import { FormEvent, useEffect, useState } from "react";
import {
  acknowledgeConditionReport,
  fetchConditionReports,
  submitConditionReport,
  type ConditionReport,
} from "@/lib/api";
import { mediaUrl } from "@/lib/media";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import "./ConditionReportForm.css";

type Props = {
  bookingId: string;
  canPickupReport: boolean;
  canReturnReport: boolean;
};

export function ConditionReportForm({ bookingId, canPickupReport, canReturnReport }: Props) {
  const [reports, setReports] = useState<ConditionReport[]>([]);
  const [phase, setPhase] = useState<"pickup" | "return">("pickup");
  const [notes, setNotes] = useState("");
  const [damageNotes, setDamageNotes] = useState("");
  const [files, setFiles] = useState<FileList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    try {
      setReports(await fetchConditionReports(bookingId));
    } catch {
      setReports([]);
    }
  }

  useEffect(() => {
    void load();
  }, [bookingId]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!files?.length) {
      setError("Add at least one photo.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await submitConditionReport(bookingId, phase, Array.from(files), notes, damageNotes);
      setNotes("");
      setDamageNotes("");
      setFiles(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function onAck(reportId: string) {
    await acknowledgeConditionReport(bookingId, reportId);
    await load();
  }

  const hasPickup = reports.some((r) => r.phase === "pickup");
  const hasReturn = reports.some((r) => r.phase === "return");

  return (
    <div className="nl-condition">
      <h4 className="nl-condition__title">Condition reports</h4>
      {reports.length > 0 ? (
        <ul className="nl-condition__list">
          {reports.map((r) => (
            <li key={r.id}>
              <strong>{r.phase}</strong> — {r.notes ?? "No notes"}
              {r.damage_notes ? <p className="nl-condition__damage">Damage: {r.damage_notes}</p> : null}
              <div className="nl-condition__photos">
                {r.photos.map((p) => (
                  <img key={p.id} src={mediaUrl(p.url)} alt={p.original_filename} className="nl-condition__thumb" />
                ))}
              </div>
              <p className="nl-condition__ack">
                Owner ack: {r.owner_acknowledged_at ? "yes" : "pending"} · Renter ack:{" "}
                {r.renter_acknowledged_at ? "yes" : "pending"}
              </p>
              <Button variant="secondary" onClick={() => void onAck(r.id)}>
                Acknowledge
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="nl-text-muted">No reports yet.</p>
      )}

      {(canPickupReport && !hasPickup) || (canReturnReport && !hasReturn) ? (
        <form className="nl-condition__form" onSubmit={(e) => void onSubmit(e)}>
          <label className="nl-field">
            <span className="nl-field__label">Phase</span>
            <select
              className="nl-explore__select"
              value={phase}
              onChange={(e) => setPhase(e.target.value as "pickup" | "return")}
            >
              {canPickupReport && !hasPickup ? <option value="pickup">Pickup</option> : null}
              {canReturnReport && !hasReturn ? <option value="return">Return</option> : null}
            </select>
          </label>
          <Input label="Notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
          <Input label="Existing damage" value={damageNotes} onChange={(e) => setDamageNotes(e.target.value)} />
          <label className="nl-field">
            <span className="nl-field__label">Photos</span>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif"
              multiple
              onChange={(e) => setFiles(e.target.files)}
            />
          </label>
          {error ? <p className="nl-auth-form__error">{error}</p> : null}
          <Button type="submit" disabled={submitting}>
            {submitting ? "Uploading…" : "Submit report"}
          </Button>
        </form>
      ) : null}
    </div>
  );
}