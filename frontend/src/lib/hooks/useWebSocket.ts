"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useAuthStore } from "@/lib/store/auth";

export type ConnectionStatus = "connected" | "connecting" | "disconnected";

interface UseWebSocketReturn {
  lastMessage: MessageEvent | null;
  connectionStatus: ConnectionStatus;
  send: (message: string) => void;
}

export function useWebSocket(): UseWebSocketReturn {
  const { accessToken, isAuthenticated, logout } = useAuthStore();
  const [lastMessage, setLastMessage] = useState<MessageEvent | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected");
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptRef = useRef(0);
  const maxReconnectAttempts = 10;

  const connect = useCallback(() => {
    if (!accessToken || !isAuthenticated) return;

    const wsUrl = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
      .replace(/^http/, "ws");

    setConnectionStatus("connecting");
    const ws = new WebSocket(`${wsUrl}/ws?token=${accessToken}`);

    ws.onopen = () => {
      setConnectionStatus("connected");
      reconnectAttemptRef.current = 0;
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "ping") {
        ws.send(JSON.stringify({ type: "pong" }));
        return;
      }
      setLastMessage(event);
    };

    ws.onclose = (event) => {
      setConnectionStatus("disconnected");
      wsRef.current = null;

      if (event.code === 4001) {
        logout();
        return;
      }

      if (reconnectAttemptRef.current < maxReconnectAttempts) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttemptRef.current), 30000);
        reconnectAttemptRef.current += 1;
        reconnectTimeoutRef.current = setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [accessToken, isAuthenticated, logout]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const send = useCallback((message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    }
  }, []);

  return { lastMessage, connectionStatus, send };
}
