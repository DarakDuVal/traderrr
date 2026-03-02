"use client";

import { useRef, useCallback, useSyncExternalStore } from "react";
import { useWebSocket } from "./useWebSocket";
import type { SignalResponse } from "@traderrr/types";

const MAX_SIGNALS = 100;

export function useSignalStream() {
  const { lastMessage, connectionStatus } = useWebSocket();
  const signalsRef = useRef<SignalResponse[]>([]);
  const lastProcessedRef = useRef<MessageEvent | null>(null);

  const getSnapshot = useCallback(() => {
    if (lastMessage && lastMessage !== lastProcessedRef.current) {
      lastProcessedRef.current = lastMessage;
      try {
        const data = JSON.parse(lastMessage.data);
        if (data.type === "signal" && data.payload) {
          signalsRef.current = [data.payload as SignalResponse, ...signalsRef.current].slice(0, MAX_SIGNALS);
        }
      } catch {
        // Ignore parse errors
      }
    }
    return signalsRef.current;
  }, [lastMessage]);

  const signals = useSyncExternalStore(
    (cb) => {
      // Re-subscribe whenever lastMessage changes
      cb();
      return () => {};
    },
    getSnapshot,
    () => [] as SignalResponse[]
  );

  return { signals, connectionStatus };
}
