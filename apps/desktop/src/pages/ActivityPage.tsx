import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import {
  acceptBooking,
  cancelBooking,
  confirmRentalComplete,
  createPaymentIntent,
  declineBooking,
  fetchMyRentalBookings,
  fetchOwnerBookingRequests,
  confirmServiceCompletion,
  createServicePaymentIntent,
  fetchMyServiceJobs,
  fetchRentalBookingConversation,
  sandboxPayServiceJob,
  startServiceJob,
  submitServiceCompletion,
  recordPickup,
  recordReturn,
  sandboxPayBooking,
  type RentalBooking,
  type ServiceJob,
} from "@/lib/api";
import { ServiceJobTimeline } from "@/components/assistance/ServiceJobTimeline";
import { ServiceJobReviewForm } from "@/components/assistance/ServiceJobReviewForm";
import { Link, useNavigate } from "react-router-dom";
import { ConditionReportForm } from "@/components/bookings/ConditionReportForm";
import { OpenDisputeButton } from "@/components/disputes/OpenDisputeButton";
import { Button } from "@/components/ui/Button";
import { useLocale } from "@/context/LocaleContext";
import type { MessageKey } from "@/i18n/locales/en";
import "@/pages/ProfilePage.css";
import "./ActivityPage.css";

function formatInr(cents: number) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(
    cents / 100
  );
}

function statusLabel(status: string) {
  return status.replace(/_/g, " ");
}

const RENTAL_DISPUTE_BLOCK = new Set(["declined", "cancelled", "expired", "completed", "disputed"]);
const RENTAL_MSG_BLOCK = new Set(["requested", "declined", "cancelled", "expired"]);
const JOB_DISPUTE_BLOCK = new Set(["completed", "cancelled", "disputed"]);

function escrowLabel(status: string | null | undefined, t: (k: MessageKey) => string): string | null {
  if (!status) return null;
  if (status === "held") return t("escrow_held");
  if (status === "released_to_renter") return t("escrow_released_renter");
  if (status === "released_to_owner") return t("escrow_released_owner");
  return status.replace(/_/g, " ");
}

export function ActivityPage() {
  const navigate = useNavigate();
  const { t } = useLocale();
  const { hasRole } = useAuth();
  const [asRenter, setAsRenter] = useState<RentalBooking[]>([]);
  const [asOwner, setAsOwner] = useState<RentalBooking[]>([]);
  const [serviceJobs, setServiceJobs] = useState<ServiceJob[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const showOwner = hasRole("item_owner");

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const renter = await fetchMyRentalBookings();
      setAsRenter(renter);
      if (showOwner) {
        setAsOwner(await fetchOwnerBookingRequests());
      }
      setServiceJobs(await fetchMyServiceJobs());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load activity");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void reload();
  }, [showOwner]);

  async function onAccept(id: string) {
    await acceptBooking(id);
    await reload();
  }

  async function onDecline(id: string) {
    await declineBooking(id);
    await reload();
  }

  async function onCancel(id: string) {
    await cancelBooking(id);
    await reload();
  }

  async function onPay(id: string) {
    const intent = await createPaymentIntent(id);
    await sandboxPayBooking(id, intent.payment_id);
    await reload();
  }

  async function onPayJob(jobId: string) {
    const intent = await createServicePaymentIntent(jobId);
    await sandboxPayServiceJob(jobId, intent.payment_id);
    await reload();
  }

  async function onPickup(id: string) {
    await recordPickup(id);
    await reload();
  }

  async function onReturn(id: string) {
    await recordReturn(id);
    await reload();
  }

  async function onComplete(id: string) {
    await confirmRentalComplete(id);
    await reload();
  }

  async function openRentalMessages(bookingId: string) {
    const conv = await fetchRentalBookingConversation(bookingId);
    navigate(`/app/messages/${conv.id}`);
  }

  return (
    <div className="nl-activity">
      <header className="nl-page__header">
        <h1 className="nl-page__title">My activity</h1>
        <p className="nl-page__desc">
          Full rental flow: accept → pay (sandbox) → pickup → return → confirm complete. Holds expire if payment is late.
        </p>
      </header>

      {loading ? <p className="nl-text-muted">Loading…</p> : null}
      {error ? <p className="nl-auth-form__error">{error}</p> : null}

      <section className="nl-activity__section">
        <h2>My rentals</h2>
        {asRenter.length === 0 ? <p className="nl-text-muted">No rental requests yet.</p> : null}
        <ul className="nl-activity__list">
          {asRenter.map((b) => (
            <li key={b.id} className="nl-activity__card">
              <div className="nl-activity__head">
                <strong>{b.item_title}</strong>
                <span className="nl-activity__status">{statusLabel(b.status)}</span>
              </div>
              <p className="nl-activity__meta">
                {b.start_date} → {b.end_date} · {formatInr(b.total_cents)} total
              </p>
              {escrowLabel(b.deposit_escrow_status, t) ? (
                <p className="nl-activity__meta nl-text-muted">{escrowLabel(b.deposit_escrow_status, t)}</p>
              ) : null}
              {b.hold_expires_at && b.status === "awaiting_payment" ? (
                <p className="nl-activity__meta">Pay before {new Date(b.hold_expires_at).toLocaleString()}</p>
              ) : null}
              {b.status === "awaiting_payment" ? (
                <div className="nl-activity__actions">
                  <Button onClick={() => void onPay(b.id)}>Pay with sandbox</Button>
                  <Button variant="ghost" onClick={() => void onCancel(b.id)}>
                    Cancel
                  </Button>
                </div>
              ) : null}
              {b.status === "requested" ? (
                <Button variant="ghost" onClick={() => void onCancel(b.id)}>
                  Cancel
                </Button>
              ) : null}
              {b.status === "returned" ? (
                <Button onClick={() => void onComplete(b.id)}>Confirm completion</Button>
              ) : null}
              {["confirmed", "active", "returned", "completed"].includes(b.status) ? (
                <ConditionReportForm
                  bookingId={b.id}
                  canPickupReport={b.status === "confirmed" || b.status === "active"}
                  canReturnReport={b.status === "active" || b.status === "returned" || b.status === "completed"}
                />
              ) : null}
              {!RENTAL_MSG_BLOCK.has(b.status) ? (
                <Button variant="ghost" type="button" onClick={() => void openRentalMessages(b.id)}>
                  Messages
                </Button>
              ) : null}
              {!RENTAL_DISPUTE_BLOCK.has(b.status) ? (
                <OpenDisputeButton subjectType="rental_booking" subjectId={b.id} onOpened={() => void reload()} />
              ) : null}
            </li>
          ))}
        </ul>
      </section>

      {showOwner ? (
        <section className="nl-activity__section">
          <h2>Requests for my listings</h2>
          {asOwner.length === 0 ? <p className="nl-text-muted">No incoming requests.</p> : null}
          <ul className="nl-activity__list">
            {asOwner.map((b) => (
              <li key={b.id} className="nl-activity__card">
                <div className="nl-activity__head">
                  <strong>{b.item_title}</strong>
                  <span className="nl-activity__status">{statusLabel(b.status)}</span>
                </div>
                <p className="nl-activity__meta">
                  {b.renter_display_name ?? "Renter"} · {b.start_date} → {b.end_date} · {formatInr(b.total_cents)}
                </p>
                {b.status === "requested" ? (
                  <div className="nl-activity__actions">
                    <Button onClick={() => void onAccept(b.id)}>Accept</Button>
                    <Button variant="secondary" onClick={() => void onDecline(b.id)}>
                      Decline
                    </Button>
                  </div>
                ) : null}
                {b.status === "confirmed" ? (
                  <Button onClick={() => void onPickup(b.id)}>Record pickup</Button>
                ) : null}
                {b.status === "active" ? (
                  <Button onClick={() => void onReturn(b.id)}>Record return</Button>
                ) : null}
                {["confirmed", "active", "returned", "completed"].includes(b.status) ? (
                  <ConditionReportForm
                    bookingId={b.id}
                    canPickupReport={b.status === "confirmed" || b.status === "active"}
                    canReturnReport={b.status === "active" || b.status === "returned" || b.status === "completed"}
                  />
                ) : null}
                {!RENTAL_MSG_BLOCK.has(b.status) ? (
                  <Button variant="ghost" type="button" onClick={() => void openRentalMessages(b.id)}>
                    Messages
                  </Button>
                ) : null}
                {!RENTAL_DISPUTE_BLOCK.has(b.status) ? (
                  <OpenDisputeButton subjectType="rental_booking" subjectId={b.id} onOpened={() => void reload()} />
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="nl-activity__section">
        <h2>Service jobs</h2>
        {serviceJobs.length === 0 ? <p className="nl-text-muted">No service jobs yet.</p> : null}
        <ul className="nl-activity__list">
          {serviceJobs.map((j) => (
            <li key={j.id} className="nl-activity__card">
              <div className="nl-activity__head">
                <strong>{j.request_title}</strong>
                <span className="nl-activity__status">{j.status.replace(/_/g, " ")}</span>
              </div>
              <p className="nl-activity__meta">
                {formatInr(j.price_cents_snapshot)} · {j.is_provider_view ? j.customer_name : j.provider_name}
              </p>
              {j.hold_expires_at && j.status === "awaiting_payment" ? (
                <p className="nl-activity__meta nl-text-muted">
                  Pay before {new Date(j.hold_expires_at).toLocaleString()}
                </p>
              ) : null}
              {!j.is_provider_view && j.status === "awaiting_payment" ? (
                <Button onClick={() => void onPayJob(j.id)}>Pay (sandbox)</Button>
              ) : null}
              <ServiceJobTimeline events={j.timeline ?? []} />
              {j.is_provider_view && j.status === "confirmed" ? (
                <Button onClick={() => void startServiceJob(j.id).then(reload)}>Start job</Button>
              ) : null}
              {j.is_provider_view && j.status === "in_progress" ? (
                <Button onClick={() => void submitServiceCompletion(j.id).then(reload)}>Submit completion</Button>
              ) : null}
              {!j.is_provider_view && j.status === "completion_submitted" ? (
                <Button onClick={() => void confirmServiceCompletion(j.id).then(reload)}>Confirm completion</Button>
              ) : null}
              {j.conversation_id ? (
                <Link to={`/app/messages/${j.conversation_id}`} className="nl-activity__link">
                  Open messages
                </Link>
              ) : null}
              {!j.is_provider_view && j.status === "completed" && !j.has_review ? (
                <ServiceJobReviewForm jobId={j.id} onDone={() => void reload()} />
              ) : null}
              {!JOB_DISPUTE_BLOCK.has(j.status) ? (
                <OpenDisputeButton subjectType="service_job" subjectId={j.id} onOpened={() => void reload()} />
              ) : null}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}