import { Link } from "react-router-dom";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "./RentalMap.css";

export type MapPoint = {
  id: string;
  title: string;
  latitude: number;
  longitude: number;
  subtitle?: string;
  href?: string;
};

const icon = new L.Icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

function FitBounds({ points }: { points: MapPoint[] }) {
  const map = useMap();
  if (points.length === 0) return null;
  const bounds = L.latLngBounds(points.map((p) => [p.latitude, p.longitude] as [number, number]));
  map.fitBounds(bounds.pad(0.15));
  return null;
}

type Props = {
  points: MapPoint[];
  center?: [number, number];
};

export function DiscoveryMap({ points, center = [19.076, 72.8777] }: Props) {
  return (
    <div className="nl-map">
      <MapContainer center={center} zoom={12} className="nl-map__canvas" scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds points={points} />
        {points.map((p) => (
          <Marker key={p.id} position={[p.latitude, p.longitude]} icon={icon}>
            <Popup>
              <strong>{p.title}</strong>
              {p.subtitle ? <p className="nl-map__popup-area">{p.subtitle}</p> : null}
              {p.href?.startsWith("/") ? (
                <Link to={p.href}>Details</Link>
              ) : p.href ? (
                <a href={p.href}>Details</a>
              ) : null}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}