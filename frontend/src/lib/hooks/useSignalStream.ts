"use client";

import { useSyncExternalStore } from "react";
import type { SignalResponse } from "@traderrr/types";

const MAX_SIGNALS = 100;

let signals: SignalResponse[] = [];
const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((l) => l());
}

export function pushSignal(signal: SignalResponse) {
  signals = [signal, ...signals].slice(0, MAX_SIGNALS);
  notify();
}

export function useSignalStream() {
  const snapshot = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => signals,
    () => [] as SignalResponse[]
  );

  return { signals: snapshot };
}
