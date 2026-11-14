import { useState } from "react";
import { submitAssistanceReview } from "@/lib/api";
import { Button } from "@/components/ui/Button";

type Props = { jobId: string; onDone: () => void };

export function ServiceJobReviewForm({ jobId, onDone }: Props) {
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);
    try {
      await submitAssistanceReview(jobId, { rating, comment });
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit review");
    }
  }

  return (
    <div className="nl-review-form">
      <p className="nl-field__label">Rate this provider</p>
      <label className="nl-field">
        <span className="nl-field__label">Stars (1–5)</span>
        <input
          type="number"
          min={1}
          max={5}
          value={rating}
          onChange={(e) => setRating(Number(e.target.value))}
        />
      </label>
      <label className="nl-field">
        <span className="nl-field__label">Comment</span>
        <textarea rows={3} value={comment} onChange={(e) => setComment(e.target.value)} />
      </label>
      {error ? <p className="nl-auth-form__error">{error}</p> : null}
      <Button onClick={() => void submit()}>Submit review</Button>
    </div>
  );
}