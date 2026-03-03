import * as SecureStore from "expo-secure-store";

const ACCESS_TOKEN_KEY = "traderrr_access_token";
const REFRESH_TOKEN_KEY = "traderrr_refresh_token";

export async function storeTokens(access: string, refresh?: string): Promise<void> {
  await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, access);
  if (refresh) {
    await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refresh);
  }
}

export async function getAccessToken(): Promise<string | null> {
  return SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
}

export async function getRefreshToken(): Promise<string | null> {
  return SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
}

export async function clearTokens(): Promise<void> {
  await Promise.all([
    SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY),
    SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY),
  ]);
}
