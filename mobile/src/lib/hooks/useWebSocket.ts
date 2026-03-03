import { useEffect, useRef, useCallback, useState } from "react";
import { getAccessToken, clearTokens } from "@/lib/auth";

export type ConnectionStatus = "connected" | "connecting" | "disconnected";

const MAX_RECONNECT_ATTEMPTS = 10;

export function useWebSocket(onMessage: (data: Record<string, unknown>) => void) {
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempt = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onMessageRef = useRef(onMessage);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    reconnectAttempt.current = 0;
    setStatus("disconnected");
  }, []);

  const connect = useCallback(async () => {
    const token = await getAccessToken();
    if (!token) {
      setStatus("disconnected");
      return;
    }

    if (wsRef.current && wsRef.current.readyState <= WebSocket.OPEN) return;

    const apiUrl = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000";
    const wsUrl = apiUrl.replace(/^https/, "wss").replace(/^http/, "ws");

    setStatus("connecting");

    const socket = new WebSocket(`${wsUrl}/ws?token=${encodeURIComponent(token)}`);

    socket.onopen = () => {
      reconnectAttempt.current = 0;
      setStatus("connected");
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string);
        if (data.type === "ping") {
          socket.send(JSON.stringify({ type: "pong" }));
          return;
        }
        onMessageRef.current(data);
      } catch {
        // ignore parse errors
      }
    };

    socket.onclose = (event) => {
      wsRef.current = null;
      setStatus("disconnected");

      if (event.code === 4001) {
        clearTokens();
        return;
      }

      if (reconnectAttempt.current < MAX_RECONNECT_ATTEMPTS) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempt.current), 30_000);
        reconnectAttempt.current += 1;
        reconnectTimer.current = setTimeout(() => {
          void connect();
        }, delay);
      }
    };

    socket.onerror = () => {
      socket.close();
    };

    wsRef.current = socket;
  }, []);

  const send = useCallback((message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    }
  }, []);

  useEffect(() => {
    void connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { connectionStatus: status, send, reconnect: connect };
}
