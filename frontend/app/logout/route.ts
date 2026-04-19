import { NextResponse } from "next/server";
import { clearAuthCookies } from "@/lib/auth";

export async function POST() {
  clearAuthCookies();
  return NextResponse.redirect(new URL("/login", process.env.APP_URL || "http://localhost:3000"));
}

export async function GET() {
  clearAuthCookies();
  return NextResponse.redirect(new URL("/login", process.env.APP_URL || "http://localhost:3000"));
}
