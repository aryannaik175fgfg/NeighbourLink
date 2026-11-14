import type { ListingPublic } from "@/lib/api";
import { DiscoveryMap } from "@/components/map/DiscoveryMap";

type Props = {
  listings: ListingPublic[];
  center?: [number, number];
};

export function RentalMap({ listings, center }: Props) {
  const points = listings.map((l) => ({
    id: l.id,
    title: l.title,
    latitude: l.latitude,
    longitude: l.longitude,
    subtitle: l.public_area_label,
    href: `/app/rentals/${l.id}`,
  }));
  return <DiscoveryMap points={points} center={center} />;
}