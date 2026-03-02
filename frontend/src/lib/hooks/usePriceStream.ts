"use client";

import { useEffect, useState } from "react";
import { useWebSocket } from "./useWebSocket";

interface PriceData {
  ticker: string;
  price: number;
  change: number;
  changePercent: number;
}

export function usePriceStream() {
  const { lastMessage, connectionStatus } = useWebSocket();
  const [prices, setPrices] = useState<Map<string, PriceData>>(new Map());

  useEffect(() => {
    if (!lastMessage) return;

    try {
      const data = JSON.parse(lastMessage.data);
      if (data.type === "price" && data.payload) {
        const price = data.payload as PriceData;
        setPrices((prev) => new Map(prev).set(price.ticker, price));
      }
    } catch {
      // Ignore parse errors
    }
  }, [lastMessage]);

  return { prices, connectionStatus };
}
