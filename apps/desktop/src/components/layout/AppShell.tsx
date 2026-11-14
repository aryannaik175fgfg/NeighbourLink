import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { fetchUnreadNotificationCount } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useMarketplaceMode, type MarketplaceMode } from "@/context/MarketplaceModeContext";
import { Button } from "@/components/ui/Button";
import { useNotificationToasts } from "@/hooks/useNotificationToasts";
import { useLocale } from "@/context/LocaleContext";
import type { MessageKey } from "@/i18n/locales/en";
import "./AppShell.css";

function navForMode(mode: MarketplaceMode, t: (key: MessageKey) => string) {
  const explore =
    mode === "rental"
      ? { to: "/app/explore", label: t("nav_explore_rentals") }
      : { to: "/app/explore", label: t("nav_find_services") };

  const items = [
    explore,
    { to: "/app/activity", label: t("nav_activity") },
    { to: "/app/messages", label: t("nav_messages") },
    { to: "/app/notifications", label: t("nav_notifications") },
    { to: "/app/community", label: t("nav_community") },
    { to: "/app/disputes", label: t("nav_disputes") },
    { to: "/app/mentorship", label: t("nav_mentorship") },
  ];

  if (mode === "rental") {
    items.push({ to: "/app/listings", label: t("nav_listings") });
    items.push({ to: "/app/saved", label: t("nav_saved") });
  }
  return items;
}

export function AppShell() {
  const { user, logout, hasRole } = useAuth();
  const { t } = useLocale();
  const { mode, setMode } = useMarketplaceMode();
  const [unread, setUnread] = useState(0);

  useNotificationToasts();

  const navItems = navForMode(mode, t);

  useEffect(() => {
    if (!user) return;
    void fetchUnreadNotificationCount()
      .then((r) => setUnread(r.count))
      .catch(() => setUnread(0));
    const id = window.setInterval(() => {
      void fetchUnreadNotificationCount()
        .then((r) => setUnread(r.count))
        .catch(() => undefined);
    }, 60_000);
    return () => window.clearInterval(id);
  }, [user]);

  return (
    <div className="nl-shell">
      <aside className="nl-shell__sidebar">
        <div className="nl-shell__brand">
          <span className="nl-shell__logo">NeighbourLink</span>
          <span className="nl-shell__tagline">{t("tagline")}</span>
        </div>

        <div className="nl-shell__mode" role="tablist" aria-label="Marketplace mode">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "rental"}
            className={`nl-shell__mode-btn ${mode === "rental" ? "is-active" : ""}`}
            onClick={() => setMode("rental")}
          >
            {t("mode_rental")}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "assistance"}
            className={`nl-shell__mode-btn ${mode === "assistance" ? "is-active" : ""}`}
            onClick={() => setMode("assistance")}
          >
            {t("mode_assistance")}
          </button>
        </div>

        <nav className="nl-shell__nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to + item.label}
              to={item.to}
              className={({ isActive }) => `nl-shell__nav-link ${isActive ? "is-active" : ""}`}
            >
              {item.label}
              {item.to === "/app/notifications" && unread > 0 ? (
                <span className="nl-shell__badge">{unread > 99 ? "99+" : unread}</span>
              ) : null}
            </NavLink>
          ))}
          <div className="nl-shell__nav-divider" />
          <NavLink to="/app/profile" className={({ isActive }) => `nl-shell__nav-link ${isActive ? "is-active" : ""}`}>
            {t("nav_profile")}
          </NavLink>
          <NavLink to="/app/settings" className={({ isActive }) => `nl-shell__nav-link ${isActive ? "is-active" : ""}`}>
            {t("nav_settings")}
          </NavLink>
          {hasRole("administrator") ? (
            <NavLink to="/app/admin" className={({ isActive }) => `nl-shell__nav-link ${isActive ? "is-active" : ""}`}>
              {t("nav_admin")}
            </NavLink>
          ) : null}
        </nav>

        <div className="nl-shell__footer">
          <div className="nl-shell__user">
            <span className="nl-shell__user-name">{user?.profile.display_name}</span>
            <span className="nl-shell__user-email">{user?.email}</span>
          </div>
          <Button variant="ghost" onClick={() => void logout()}>
            {t("sign_out")}
          </Button>
        </div>
      </aside>

      <main className="nl-shell__main">
        <Outlet />
      </main>
    </div>
  );
}
