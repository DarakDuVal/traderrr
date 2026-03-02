import { ApiClient } from "@traderrr/api-client";
import { useAuthStore } from "@/lib/store/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient = new ApiClient(API_URL, () => useAuthStore.getState().accessToken);
