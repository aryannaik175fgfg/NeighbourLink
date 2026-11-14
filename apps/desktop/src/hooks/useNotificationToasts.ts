import { useEffect, useRef } from "react";
import { fetchNotifications } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export function useNotificationToasts() {
  const { user } = useAuth();
  const lastId = useRef<string | null>(null);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;

    async function poll() {
      try {
        const notes = await fetchNotifications();
        if (cancelled || notes.length === 0) return;
        const newest = notes[0];
        if (lastId.current === null) {
          lastId.current = newest.id;
          return;
        }
        if (newest.id !== lastId.current && newest.read_at == null) {
          lastId.current = newest.id;
          void window.neighbourlink?.showNotification?.(newest.title, newest.body);
        }
      } catch {
        /* offline */
      }
    }

    void poll();
    const id = window.setInterval(() => void poll(), 45_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [user]);
}