/// <reference types="vite/client" />

import type { NeighbourLinkBridge } from "../electron/preload";

declare global {
  interface Window {
    neighbourlink: NeighbourLinkBridge;
  }
}
