import { FormEvent, useState } from "react";
import { createDispute } from "@/lib/api";
import { Button } from "@/components/ui/Button";

type Props = {
  subjectType: "rental_booking" | "service_job";
  subjectId: string;
  onOpened?: () => void;
};

export function OpenDisputeButton({ subjectType, subjectId, onOpened }: Props) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await createDispute({ subject_type: subjectType, subject_id: subjectId, reason: reason.trim() });
      setOpen(false);
      setReason("");
      onOpened?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open dispute");
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <Button variant="ghost" type="button" onClick={() => setOpen(true)}>
        Open dispute
      </Button>
    );
  }

  return (
    <form className="nl-dispute-form" onSubmit={(e) => void submit(e)}>
      <label className="nl-field">
        <span className="nl-field__label">What went wrong?</span>
        <textarea
          className="nl-profile-textarea"
          rows={3}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          minLength={10}
          required
        />
      </label>
      {error ? <p className="nl-auth-form__error">{error}</p> : null}
      <div className="nl-activity__actions">
        <Button type="submit" disabled={busy}>
          Submit dispute
        </Button>
        <Button variant="ghost" type="button" onClick={() => setOpen(false)}>
          Cancel
        </Button>
      </div>
    </form>
  );
}