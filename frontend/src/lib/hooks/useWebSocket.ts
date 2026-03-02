"use client";

import { useEffect, useRef, useCallback, useSyncExternalStore } from "react";
import { useAuthStore } from "@/lib/store/auth";
import { pushSignal } from "./useSignalStream";
import { updatePrice } from "./usePriceStream";

export type ConnectionStatus = "connected" | "connecting" | "disconnected";

interface UseWebSocketReturn {
  connectionStatus: ConnectionStatus;
  send: (message: string) => void;
}

let ws: WebSocket | null = null;
let currentStatus: ConnectionStatus = "disconnected";
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
let reconnectAttempt = 0;
const MAX_RECONNECT_ATTEMPTS = 10;
const statusListeners = new Set<() => void>();

function notifyStatusListeners() {
  statusListeners.forEach((l) => l());
}

function connectWs(token: string, onAuthFailure: () => void) {
  if (ws && ws.readyState <= WebSocket.OPEN) return;

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const wsUrl = apiUrl.replace(/^https/, "wss").replace(/^http/, "ws");

  currentStatus = "connecting";
  notifyStatusListeners();

  const socket = new WebSocket(`${wsUrl}/ws?token=${token}`);

  socket.onopen = () => {
    currentStatus = "connected";
    reconnectAttempt = 0;
    notifyStatusListeners();
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "ping") {
        socket.send(JSON.stringify({ type: "pong" }));
        return;
      }
      if (data.type === "signal" && data.payload) {
        pushSignal(data.payload);
      }
      if (data.type === "price" && data.payload) {
        updatePrice(data.payload);
      }
    } catch {
      // Ignore parse errors
    }
  };

  socket.onclose = (event) => {
    currentStatus = "disconnected";
    ws = null;
    notifyStatusListeners();

    if (event.code === 4001) {
      onAuthFailure();
      return;
    }

    if (reconnectAttempt < MAX_RECONNECT_ATTEMPTS) {
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempt), 30000);
      reconnectAttempt += 1;
      reconnectTimeout = setTimeout(() => connectWs(token, onAuthFailure), delay);
    }
  };

  socket.onerror = () => {
    socket.close();
  };

  ws = socket;
}

function disconnectWs() {
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout);
    reconnectTimeout = null;
  }
  if (ws) {
    ws.close();
    ws = null;
  }
  reconnectAttempt = 0;
  currentStatus = "disconnected";
  notifyStatusListeners();
}

export function useWebSocket(): UseWebSocketReturn {
  const { accessToken, isAuthenticated, logout } = useAuthStore();
  const logoutRef = useRef(logout);

  useEffect(() => {
    logoutRef.current = logout;
  }, [logout]);

  const connectionStatus = useSyncExternalStore(
    (cb) => {
      statusListeners.add(cb);
      return () => statusListeners.delete(cb);
    },
    () => currentStatus,
    () => "disconnected" as ConnectionStatus
  );

  useEffect(() => {
    if (!accessToken || !isAuthenticated) {
      disconnectWs();
      return;
    }

    connectWs(accessToken, () => logoutRef.current());

    return () => {
      disconnectWs();
    };
  }, [accessToken, isAuthenticated]);

  const send = useCallback((message: string) => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(message);
    }
  }, []);

  return { connectionStatus, send };
}
