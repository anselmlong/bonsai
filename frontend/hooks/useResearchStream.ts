"use client";
import { useEffect, useRef, useState } from "react";
import type { NodeEvent } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function useResearchStream(jobId: string | null) {
  const [events, setEvents] = useState<NodeEvent[]>([]);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!jobId) return;
    setEvents([]);
    setDone(false);
    setError(null);

    const es = new EventSource(`${API_BASE}/research/${jobId}/stream`);
    esRef.current = es;

    es.onmessage = (e) => {
      try {
        const event: NodeEvent = JSON.parse(e.data);
        setEvents((prev) => [...prev, event]);
        if (event.type === "research_complete" || event.type === "error") {
          setDone(true);
          es.close();
        }
      } catch {
        // ignore malformed events
      }
    };

    es.onerror = () => {
      setError("Stream connection lost.");
      setDone(true);
      es.close();
    };

    return () => {
      es.close();
    };
  }, [jobId]);

  return { events, done, error };
}
