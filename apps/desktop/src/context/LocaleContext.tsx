import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { en, type MessageKey } from "@/i18n/locales/en";
import { hi } from "@/i18n/locales/hi";
import { mr } from "@/i18n/locales/mr";
import { useAuth } from "@/context/AuthContext";
import { fetchUserSettings } from "@/lib/api";

export type LocaleCode = "en" | "hi" | "mr";

const catalogs: Record<LocaleCode, Record<MessageKey, string>> = { en, hi, mr };

type LocaleState = {
  locale: LocaleCode;
  t: (key: MessageKey) => string;
};

const LocaleContext = createContext<LocaleState | null>(null);

export function LocaleProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [locale, setLocale] = useState<LocaleCode>("en");

  useEffect(() => {
    const fromProfile = user?.profile.preferred_locale;
    if (fromProfile === "hi" || fromProfile === "mr" || fromProfile === "en") {
      setLocale(fromProfile);
      return;
    }
    if (!user) {
      setLocale("en");
      return;
    }
    void fetchUserSettings()
      .then((s) => {
        if (s.preferred_locale === "hi" || s.preferred_locale === "mr") {
          setLocale(s.preferred_locale);
        } else {
          setLocale("en");
        }
      })
      .catch(() => setLocale("en"));
  }, [user]);

  const value = useMemo(
    () => ({
      locale,
      t: (key: MessageKey) => catalogs[locale][key] ?? en[key],
    }),
    [locale]
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  const ctx = useContext(LocaleContext);
  if (!ctx) throw new Error("useLocale requires LocaleProvider");
  return ctx;
}