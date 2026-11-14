import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

export type MarketplaceMode = "rental" | "assistance";

type ModeState = {
  mode: MarketplaceMode;
  setMode: (mode: MarketplaceMode) => void;
};

const MarketplaceModeContext = createContext<ModeState | null>(null);

const STORAGE_KEY = "nl_marketplace_mode";

export function MarketplaceModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<MarketplaceMode>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === "assistance" ? "assistance" : "rental";
  });

  const setMode = (next: MarketplaceMode) => {
    setModeState(next);
    localStorage.setItem(STORAGE_KEY, next);
  };

  const value = useMemo(() => ({ mode, setMode }), [mode]);

  return <MarketplaceModeContext.Provider value={value}>{children}</MarketplaceModeContext.Provider>;
}

export function useMarketplaceMode() {
  const ctx = useContext(MarketplaceModeContext);
  if (!ctx) throw new Error("useMarketplaceMode must be used within MarketplaceModeProvider");
  return ctx;
}
