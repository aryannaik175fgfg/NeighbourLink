import { FormEvent, useEffect, useState } from "react";
import {
  changePassword,
  fetchMySessions,
  fetchUserSettings,
  revokeOtherSessions,
  revokeSession,
  updateUserSettings,
  type UserSessionRow,
  type UserSettings,
} from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import "./SettingsPage.css";

export function SettingsPage() {
  const { refreshUser } = useAuth();
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [sessions, setSessions] = useState<UserSessionRow[]>([]);

  useEffect(() => {
    void fetchUserSettings()
      .then(setSettings)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load"));
    void fetchMySessions()
      .then(setSessions)
      .catch(() => setSessions([]));
  }, []);

  async function savePrefs(e: FormEvent) {
    e.preventDefault();
    if (!settings) return;
    setError(null);
    setMessage(null);
    const updated = await updateUserSettings(settings);
    setSettings(updated);
    await refreshUser();
    setMessage("Preferences saved.");
  }

  async function onPassword(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    await changePassword(currentPassword, newPassword);
    setCurrentPassword("");
    setNewPassword("");
    setMessage("Password updated.");
  }

  if (!settings) return <p className="nl-text-muted">Loading settings…</p>;

  function toggle(key: keyof Pick<UserSettings, "notify_rentals" | "notify_assistance" | "notify_messages" | "notify_community">) {
    setSettings((s) => (s ? { ...s, [key]: !s[key] } : s));
  }

  return (
    <div className="nl-settings">
      <header className="nl-page__header">
        <h1 className="nl-page__title">Settings</h1>
        <p className="nl-page__desc">Language, neighbourhood defaults, in-app alerts, and password.</p>
      </header>

      {error ? <p className="nl-auth-form__error">{error}</p> : null}
      {message ? <p className="nl-profile-success">{message}</p> : null}

      <form className="nl-settings__card" onSubmit={(e) => void savePrefs(e)}>
        <h2>Regional</h2>
        <label className="nl-field">
          <span className="nl-field__label">Language</span>
          <select
            className="nl-settings__select"
            value={settings.preferred_locale}
            onChange={(e) => setSettings({ ...settings, preferred_locale: e.target.value })}
          >
            <option value="en">English</option>
            <option value="hi">हिन्दी</option>
            <option value="mr">मराठी</option>
          </select>
        </label>

        <h2>Default search area</h2>
        <p className="nl-settings__hint">Used as defaults on Explore and Community (you can still change per search).</p>
        <div className="nl-settings__row">
          <Input
            label="Latitude"
            value={settings.default_latitude?.toString() ?? ""}
            onChange={(e) =>
              setSettings({
                ...settings,
                default_latitude: e.target.value ? parseFloat(e.target.value) : null,
              })
            }
          />
          <Input
            label="Longitude"
            value={settings.default_longitude?.toString() ?? ""}
            onChange={(e) =>
              setSettings({
                ...settings,
                default_longitude: e.target.value ? parseFloat(e.target.value) : null,
              })
            }
          />
          <Input
            label="Radius (km)"
            value={String(settings.default_radius_km)}
            onChange={(e) => setSettings({ ...settings, default_radius_km: parseInt(e.target.value, 10) || 25 })}
          />
        </div>

        <h2>In-app notifications</h2>
        <ul className="nl-settings__toggles">
          {(
            [
              ["notify_rentals", "Rentals (bookings & payments)"],
              ["notify_assistance", "Assistance (jobs & skills)"],
              ["notify_messages", "Messages"],
              ["notify_community", "Community (reserved)"],
            ] as const
          ).map(([key, label]) => (
            <li key={key}>
              <label className="nl-settings__toggle">
                <input type="checkbox" checked={settings[key]} onChange={() => toggle(key)} />
                <span>{label}</span>
              </label>
            </li>
          ))}
        </ul>
        <Button type="submit">Save preferences</Button>
      </form>

      <section className="nl-settings__card">
        <h2>Signed-in devices</h2>
        <p className="nl-settings__hint">Revoke older sessions if you signed in on a shared PC.</p>
        <ul className="nl-settings__sessions">
          {sessions.map((s) => (
            <li key={s.id}>
              <span>{s.user_agent ?? "Unknown device"}</span>
              {s.is_current ? <span className="nl-text-muted">This device</span> : null}
              {!s.is_current ? (
                <Button type="button" variant="ghost" onClick={() => void revokeSession(s.id).then(() => fetchMySessions().then(setSessions))}>
                  Revoke
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
        <Button type="button" variant="secondary" onClick={() => void revokeOtherSessions().then(() => fetchMySessions().then(setSessions))}>
          Sign out other devices
        </Button>
      </section>

      <form className="nl-settings__card" onSubmit={(e) => void onPassword(e)}>
        <h2>Security</h2>
        <Input
          label="Current password"
          type="password"
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
          required
        />
        <Input
          label="New password"
          type="password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          required
        />
        <Button type="submit" variant="secondary">
          Change password
        </Button>
      </form>
    </div>
  );
}