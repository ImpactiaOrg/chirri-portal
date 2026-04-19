import { cookies } from "next/headers";
import { apiFetch, type ClientUserDto } from "./api";

const ACCESS_COOKIE = "chirri_access";
const REFRESH_COOKIE = "chirri_refresh";

export function getAccessToken(): string | null {
  return cookies().get(ACCESS_COOKIE)?.value ?? null;
}

export function setAuthCookies(access: string, refresh: string) {
  const store = cookies();
  const isProd = process.env.NODE_ENV === "production";
  store.set(ACCESS_COOKIE, access, {
    httpOnly: true,
    sameSite: "lax",
    secure: isProd,
    path: "/",
    maxAge: 60 * 60,
  });
  store.set(REFRESH_COOKIE, refresh, {
    httpOnly: true,
    sameSite: "lax",
    secure: isProd,
    path: "/",
    maxAge: 60 * 60 * 24 * 14,
  });
}

export function clearAuthCookies() {
  const store = cookies();
  store.delete(ACCESS_COOKIE);
  store.delete(REFRESH_COOKIE);
}

export async function getCurrentUser(): Promise<ClientUserDto | null> {
  const token = getAccessToken();
  if (!token) return null;
  try {
    return await apiFetch<ClientUserDto>("/api/auth/me/", { token });
  } catch {
    return null;
  }
}
