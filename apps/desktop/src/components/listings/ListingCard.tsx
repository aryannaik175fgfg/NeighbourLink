import { Link } from "react-router-dom";
import type { ListingPublic } from "@/lib/api";
import { mediaUrl } from "@/lib/media";
import "./ListingCard.css";

function formatInr(cents: number) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(
    cents / 100
  );
}

type Props = {
  listing: ListingPublic;
  compact?: boolean;
  isSaved?: boolean;
  onToggleSave?: (listingId: string, nowSaved: boolean) => void;
};

export function ListingCard({ listing, compact = false, isSaved, onToggleSave }: Props) {
  return (
    <article className={`nl-listing-card ${compact ? "nl-listing-card--compact" : ""}`}>
      {onToggleSave ? (
        <button
          type="button"
          className={`nl-listing-card__save ${isSaved ? "is-saved" : ""}`}
          aria-pressed={isSaved}
          aria-label={isSaved ? "Remove from saved" : "Save listing"}
          onClick={() => onToggleSave(listing.id, !isSaved)}
        >
          {isSaved ? "Saved" : "Save"}
        </button>
      ) : null}
      <div className={`nl-listing-card__media ${listing.photo_urls?.[0] ? "" : "nl-listing-card__media--empty"}`}>
        {listing.photo_urls?.[0] ? (
          <img src={mediaUrl(listing.photo_urls[0])} alt="" className="nl-listing-card__img" />
        ) : (
          <span className="nl-listing-card__category-pill">{listing.category.name}</span>
        )}
      </div>
      <div className="nl-listing-card__body">
        <div className="nl-listing-card__meta">
          <span className="nl-listing-card__category">{listing.category.name}</span>
          {listing.distance_meters != null ? (
            <span className="nl-listing-card__distance">{(listing.distance_meters / 1000).toFixed(1)} km</span>
          ) : null}
        </div>
        <h3 className="nl-listing-card__title">
          <Link to={`/app/rentals/${listing.id}`} className="nl-listing-card__link">
            {listing.title}
          </Link>
        </h3>
        <p className="nl-listing-card__area">{listing.public_area_label}</p>
        <p className="nl-listing-card__desc">{listing.description}</p>
        <div className="nl-listing-card__footer">
          <span className="nl-listing-card__price">
            {formatInr(listing.daily_price_cents)}
            <span className="nl-listing-card__price-unit">/day</span>
          </span>
          <span className="nl-listing-card__owner">· {listing.owner_display_name}</span>
        </div>
      </div>
    </article>
  );
}