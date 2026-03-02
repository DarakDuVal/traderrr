"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { StressTestRequest } from "@traderrr/types";

export function useRiskMetrics() {
  return useQuery({
    queryKey: ["risk-metrics"],
    queryFn: () => apiClient.getRiskMetrics(),
  });
}

export function useCorrelation() {
  return useQuery({
    queryKey: ["correlation"],
    queryFn: () => apiClient.getCorrelation(),
  });
}

export function useStressTest() {
  return useMutation({
    mutationFn: (data: StressTestRequest) => apiClient.stressTest(data),
  });
}
