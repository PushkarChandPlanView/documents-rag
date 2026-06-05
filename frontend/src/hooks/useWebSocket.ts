import { useCallback, useEffect, useRef, useState } from "react";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost/ws";

export function useDocumentStatus(documentId: string | null) {
  const [stages, setStages] = useState<
    Array<{ stage: string; status: string; error: string | null }>
  >([]);
  const [isComplete, setIsComplete] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (!documentId) return;
    const ws = new WebSocket(`${WS_URL}/documents/${documentId}/ws`);
    wsRef.current = ws;

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as Array<{
          stage: string;
          status: string;
          error: string | null;
        }>;
        setStages(data);
        const allDone = data.every(
          (j) => j.status === "COMPLETED" || j.status === "FAILED"
        );
        if (allDone) {
          setIsComplete(true);
          ws.close();
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onerror = () => ws.close();
  }, [documentId]);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return { stages, isComplete };
}
