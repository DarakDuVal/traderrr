"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { SignalFilter } from "@traderrr/types";

export function useSignals(filter?: SignalFilter) {
  return useQuery({
    queryKey: ["signals", filter],
    queryFn: () => apiClient.getSignals(filter),
  });
}

export function useSignalsByTicker(ticker: string) {
  return useQuery({
    queryKey: ["signals", ticker],
    queryFn: () => apiClient.getSignalsByTicker(ticker),
    enabled: !!ticker,
  });
}
