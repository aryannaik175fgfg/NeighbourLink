import type { ServiceJobEvent } from "@/lib/api";
import "./ServiceJobTimeline.css";

type Props = { events: ServiceJobEvent[] };

export function ServiceJobTimeline({ events }: Props) {
  if (!events.length) return null;
  return (
    <ol className="nl-job-timeline">
      {events.map((e) => (
        <li key={`${e.event_type}-${e.created_at}`}>
          <span className="nl-job-timeline__dot" aria-hidden />
          <div>
            <span className="nl-job-timeline__summary">{e.summary}</span>
            <time className="nl-job-timeline__time" dateTime={e.created_at}>
              {new Date(e.created_at).toLocaleString()}
            </time>
          </div>
        </li>
      ))}
    </ol>
  );
}