"use client";

import { useRef, useCallback, useSyncExternalStore } from "react";
import { useWebSocket } from "./useWebSocket";

interface PriceData {
  ticker: string;
  price: number;
  change: number;
  changePercent: number;
}

export function usePriceStream() {
  const { lastMessage, connectionStatus } = useWebSocket();
  const pricesRef = useRef<Map<string, PriceData>>(new Map());
  const lastProcessedRef = useRef<MessageEvent | null>(null);

  const getSnapshot = useCallback(() => {
    if (lastMessage && lastMessage !== lastProcessedRef.current) {
      lastProcessedRef.current = lastMessage;
      try {
        const data = JSON.parse(lastMessage.data);
        if (data.type === "price" && data.payload) {
          const price = data.payload as PriceData;
          pricesRef.current = new Map(pricesRef.current).set(price.ticker, price);
        }
      } catch {
        // Ignore parse errors
      }
    }
    return pricesRef.current;
  }, [lastMessage]);

  const prices = useSyncExternalStore(
    (cb) => {
      cb();
      return () => {};
    },
    getSnapshot,
    () => new Map<string, PriceData>()
  );

  return { prices, connectionStatus };
}
