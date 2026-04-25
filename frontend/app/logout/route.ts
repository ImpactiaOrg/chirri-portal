import { NextResponse } from "next/server";
import { clearAuthCookies } from "@/lib/auth";

// Resolver el origin desde el request mismo evita depender de APP_URL en
// .env (que puede no estar seteado en dev y rompe `new URL("/login", undefined)`
// con TypeError: Invalid URL al hacer logout).
export async function POST(request: Request) {
  clearAuthCookies();
  return NextResponse.redirect(new URL("/login", request.url));
}

export async function GET(request: Request) {
  clearAuthCookies();
  return NextResponse.redirect(new URL("/login", request.url));
}
