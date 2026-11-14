const API_ORIGIN = "http://127.0.0.1:8742";

export function mediaUrl(path: string): string {
  if (path.startsWith("http")) return path;
  return `${API_ORIGIN}${path}`;
}