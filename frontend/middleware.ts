import { NextResponse, type NextRequest } from "next/server";

const BACKEND = process.env.BACKEND_INTERNAL_URL || "http://backend:8000";
const ACCESS_COOKIE = "chirri_access";
const REFRESH_COOKIE = "chirri_refresh";
const REFRESH_LEAD_SECONDS = 120;
const PROXY_PREFIXES = ["/api/", "/admin", "/static/", "/media/"];

function decodeExp(jwt: string): number | null {
  try {
    const payload = jwt.split(".")[1];
    if (!payload) return null;
    const b64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const parsed = JSON.parse(atob(b64));
    return typeof parsed.exp === "number" ? parsed.exp : null;
  } catch {
    return null;
  }
}

async function refreshAccessToken(refresh: string): Promise<string | null> {
  try {
    const res = await fetch(`${BACKEND}/api/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
      cache: "no-store",
    });
    if (!res.ok) return null;
    const body = (await res.json()) as { access?: unknown };
    return typeof body.access === "string" ? body.access : null;
  } catch {
    return null;
  }
}

export async function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;

  const isProxied = PROXY_PREFIXES.some(
    (p) => pathname.startsWith(p) || pathname === p.replace(/\/$/, ""),
  );
  if (isProxied) {
    return NextResponse.rewrite(new URL(pathname + search, BACKEND));
  }

  const refresh = req.cookies.get(REFRESH_COOKIE)?.value;
  if (!refresh) return NextResponse.next();

  const access = req.cookies.get(ACCESS_COOKIE)?.value;
  const now = Math.floor(Date.now() / 1000);
  const exp = access ? decodeExp(access) : null;
  const expiringSoon = !exp || exp - now <= REFRESH_LEAD_SECONDS;
  if (!expiringSoon) return NextResponse.next();

  const newAccess = await refreshAccessToken(refresh);
  if (!newAccess) {
    const res = NextResponse.next();
    res.cookies.delete(ACCESS_COOKIE);
    res.cookies.delete(REFRESH_COOKIE);
    return res;
  }

  // Forward the new cookie to the current request so Server Components see it,
  // AND set it on the response so the browser keeps the fresh token.
  req.cookies.set(ACCESS_COOKIE, newAccess);
  const res = NextResponse.next({ request: { headers: req.headers } });
  res.cookies.set(ACCESS_COOKIE, newAccess, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60,
  });
  return res;
}

export const config = {
  matcher: [
    "/admin/:path*",
    "/static/:path*",
    "/media/:path*",
    "/api/:path*",
    "/home",
    "/home/:path*",
    "/campaigns",
    "/campaigns/:path*",
    "/reports",
    "/reports/:path*",
  ],
};
