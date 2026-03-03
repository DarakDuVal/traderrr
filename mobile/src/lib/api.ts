import { ApiClient } from "@traderrr/api-client";
import { getAccessToken } from "@/lib/auth";

const API_URL = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000";

let cachedToken: string | null = null;

/** Refresh the in-memory token cache (call after login / token refresh). */
export async function refreshCachedToken(): Promise<void> {
  cachedToken = await getAccessToken();
}

export const apiClient = new ApiClient(API_URL, () => cachedToken);
