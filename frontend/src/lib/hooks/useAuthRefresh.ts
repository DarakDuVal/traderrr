"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store/auth";
import { apiClient } from "@/lib/api";

export function useAuthRefresh() {
  const router = useRouter();
  const { setToken, setUser, logout } = useAuthStore();
  const attempted = useRef(false);

  useEffect(() => {
    if (attempted.current) return;
    attempted.current = true;

    async function refresh() {
      try {
        const tokenRes = await apiClient.refresh();
        setToken(tokenRes.access_token);
        const user = await apiClient.me();
        setUser(user);
      } catch {
        logout();
        router.push("/login");
      }
    }

    refresh();
  }, [setToken, setUser, logout, router]);
}
