import { contextBridge, ipcRenderer } from "electron";

const apiBaseUrl = "http://127.0.0.1:8742/api/v1";

contextBridge.exposeInMainWorld("neighbourlink", {
  apiBaseUrl,
  platform: process.platform,
  version: "0.1.0",
  showNotification: (title: string, body: string) => ipcRenderer.invoke("show-notification", { title, body }),
});

export type NeighbourLinkBridge = {
  apiBaseUrl: string;
  platform: string;
  version: string;
  showNotification: (title: string, body: string) => Promise<void>;
};
