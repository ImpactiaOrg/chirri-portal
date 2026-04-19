"use server";

import { redirect } from "next/navigation";
import { apiFetch, ApiError, type LoginResponse } from "@/lib/api";
import { setAuthCookies } from "@/lib/auth";

export async function loginAction(input: { email: string; password: string }) {
  try {
    const data = await apiFetch<LoginResponse>("/api/auth/login/", {
      method: "POST",
      body: JSON.stringify(input),
    });
    setAuthCookies(data.access, data.refresh);
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      return { error: "Email o contraseña incorrectos." };
    }
    return { error: "No pudimos iniciar sesión. Probá de nuevo." };
  }
  redirect("/home");
}
