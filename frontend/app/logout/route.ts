import { NextResponse } from "next/server";
import { clearAuthCookies } from "@/lib/auth";

// En prod estamos detrás de nginx: `request.url` lleva el host interno
// de docker (p.ej. `http://frontend:3000`), no `chirri.impactia.ai`.
// Si redirigimos contra ese, el browser intenta resolver un host privado
// y muestra `chrome-error://chromewebdata/`. Reconstruimos el origin a
// partir del Host header (nginx forwardea el host público con
// `proxy_set_header Host $host`) + X-Forwarded-Proto para el scheme.
// Fallback a request.url para dev sin proxy.
function publicLoginUrl(request: Request): URL {
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  const proto = request.headers.get("x-forwarded-proto");
  if (host) {
    return new URL("/login", `${proto ?? "https"}://${host}`);
  }
  return new URL("/login", request.url);
}

export async function POST(request: Request) {
  clearAuthCookies();
  return NextResponse.redirect(publicLoginUrl(request));
}

export async function GET(request: Request) {
  clearAuthCookies();
  return NextResponse.redirect(publicLoginUrl(request));
}
