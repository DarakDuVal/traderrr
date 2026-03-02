"use client";

import { useEffect, useState } from "react";
import { useWebSocket } from "./useWebSocket";
import type { SignalResponse } from "@traderrr/types";

const MAX_SIGNALS = 100;

export function useSignalStream() {
  const { lastMessage, connectionStatus } = useWebSocket();
  const [signals, setSignals] = useState<SignalResponse[]>([]);

  useEffect(() => {
    if (!lastMessage) return;

    try {
      const data = JSON.parse(lastMessage.data);
      if (data.type === "signal" && data.payload) {
        setSignals((prev) => [data.payload as SignalResponse, ...prev].slice(0, MAX_SIGNALS));
      }
    } catch {
      // Ignore parse errors
    }
  }, [lastMessage]);

  return { signals, connectionStatus };
}
