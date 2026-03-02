"use client";

import { useSyncExternalStore } from "react";

interface PriceData {
  ticker: string;
  price: number;
  change: number;
  changePercent: number;
}

let prices = new Map<string, PriceData>();
const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((l) => l());
}

export function updatePrice(data: PriceData) {
  prices = new Map(prices).set(data.ticker, data);
  notify();
}

export function usePriceStream() {
  const snapshot = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => prices,
    () => new Map<string, PriceData>()
  );

  return { prices: snapshot };
}
