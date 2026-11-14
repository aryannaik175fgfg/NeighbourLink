import "./PlaceholderPage.css";

type Props = {
  title: string;
  description: string;
  phase?: number;
};

export function PlaceholderPage({ title, description, phase = 2 }: Props) {
  return (
    <div className="nl-page">
      <header className="nl-page__header">
        <h1 className="nl-page__title">{title}</h1>
        <p className="nl-page__desc">{description}</p>
      </header>
      <div className="nl-page__empty">
        <p className="nl-page__empty-title">Coming in Phase {phase}</p>
        <p className="nl-page__empty-body">
          This area is wired in navigation but intentionally not faked. Functionality will arrive with the
          corresponding backend modules.
        </p>
      </div>
    </div>
  );
}
