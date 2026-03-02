"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { PositionCreate, PositionUpdate } from "@traderrr/types";

export function usePositions() {
  return useQuery({
    queryKey: ["positions"],
    queryFn: () => apiClient.getPositions(),
  });
}

export function usePerformance() {
  return useQuery({
    queryKey: ["performance"],
    queryFn: () => apiClient.getPerformance(),
  });
}

export function useAddPosition() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PositionCreate) => apiClient.addPosition(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["positions"] }),
  });
}

export function useUpdatePosition() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: PositionUpdate }) => apiClient.updatePosition(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["positions"] }),
  });
}

export function useDeletePosition() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiClient.deletePosition(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["positions"] }),
  });
}
