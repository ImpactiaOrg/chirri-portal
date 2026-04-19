import { NextResponse, type NextRequest } from "next/server";

const BACKEND = process.env.BACKEND_INTERNAL_URL || "http://backend:8000";

export function middleware(req: NextRequest) {
  const target = new URL(req.nextUrl.pathname + req.nextUrl.search, BACKEND);
  return NextResponse.rewrite(target);
}

export const config = {
  matcher: ["/admin/:path*", "/static/:path*", "/media/:path*", "/api/:path*"],
};
