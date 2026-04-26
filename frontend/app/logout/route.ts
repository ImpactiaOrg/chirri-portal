import { NextResponse } from "next/server";
import { clearAuthCookies } from "@/lib/auth";

// En prod estamos detrás de nginx: `request.url` lleva el host interno
// de docker (p.ej. `http://frontend:3000`), no `chirri.impactia.ai`.
// Si redirigimos contra ese, el browser intenta resolver un host privado
// y muestra `chrome-error://chromewebdata/`. Reconstruimos el origin a
// partir de los headers X-Forwarded-* que nginx setea, con fallback
// a request.url para dev (donde no hay proxy).
function publicLoginUrl(request: Request): URL {
  const fwdHost = request.headers.get("x-forwarded-host");
  const fwdProto = request.headers.get("x-forwarded-proto");
  if (fwdHost) {
    return new URL("/login", `${fwdProto ?? "https"}://${fwdHost}`);
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
