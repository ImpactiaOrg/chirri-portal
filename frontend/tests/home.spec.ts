import { test, expect } from "@playwright/test";
import { login, trackConsoleErrors } from "./helpers";

test.describe("Home smoke", () => {
  test("login redirects to home and the page renders without runtime errors", async ({ page }) => {
    const errors = trackConsoleErrors(page);

    await login(page);

    await expect(page.getByText(/buen día/i)).toBeVisible();
    await expect(page.getByText(/Chirri Portal · Balanz/i)).toBeVisible();
    await expect(page.getByRole("link", { name: /Home/i })).toBeVisible();

    // If `apiFetch` throws ("Unexpected end of JSON input"), Next shows a
    // runtime error overlay in dev. We assert no errors made it through.
    expect(errors, `console/page errors on /home:\n${errors.join("\n")}`).toEqual([]);
  });

  test("wrong credentials stay on /login with an error banner", async ({ page }) => {
    await page.goto("/login");
    await page.fill("#email", "belen.rizzo@balanz.com");
    await page.fill("#password", "wrong-password");
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByText(/incorrectos/i)).toBeVisible();
  });

  test("logout clears session and returns to /login", async ({ page }) => {
    await login(page);
    await page.click('button.logout-btn');
    await expect(page).toHaveURL(/\/login$/);
  });

  test("expired access cookie is silently refreshed by middleware", async ({ page, context }) => {
    // Log in to obtain both cookies, then drop ONLY the access cookie to
    // simulate the access token having expired. A valid refresh cookie
    // remains — the middleware should swap in a fresh access transparently.
    await login(page);
    const before = await context.cookies();
    const refresh = before.find((c) => c.name === "chirri_refresh");
    expect(refresh, "refresh cookie must exist after login").toBeTruthy();

    const kept = before.filter((c) => c.name !== "chirri_access");
    await context.clearCookies();
    await context.addCookies(kept);

    await page.goto("/home");
    await expect(page).toHaveURL(/\/home$/);
    await expect(page.getByText(/buen día/i)).toBeVisible();

    const after = await context.cookies();
    const freshAccess = after.find((c) => c.name === "chirri_access");
    expect(freshAccess, "middleware must set a new access cookie").toBeTruthy();
  });

  test("campaigns list page renders active and archived sections", async ({ page }) => {
    const errors = trackConsoleErrors(page);

    await login(page);
    await page.goto("/campaigns");

    await expect(page.getByRole("heading", { name: /campañas\./i })).toBeVisible();
    await expect(page.getByText(/ACTIVAS ·/)).toBeVisible();
    await expect(page.getByText(/ARCHIVO ·/)).toBeVisible();
    await expect(page.getByText(/de ahorrista a inversor/i).first()).toBeVisible();

    expect(errors, `console/page errors on /campaigns:\n${errors.join("\n")}`).toEqual([]);
  });

  test("stale access cookie on /login shows the form instead of redirect-looping", async ({
    page,
    context,
  }) => {
    // Regression (abr 2026): after seed_demo --wipe, the browser keeps an
    // access cookie whose user_id no longer exists. /login used to redirect
    // to /home on cookie presence alone; /home would redirect back → loop.
    // /login must validate the user actually exists before redirecting.
    await context.clearCookies();
    await context.addCookies([
      {
        name: "chirri_access",
        // Well-formed JWT payload with a far-future exp and a bogus user_id.
        // Header + payload + signature are bogus — the backend rejects it,
        // getCurrentUser returns null, and /login should render the form.
        value:
          "eyJhbGciOiJIUzI1NiJ9." +
          "eyJ1c2VyX2lkIjo5OTk5OTksImV4cCI6OTk5OTk5OTk5OX0." +
          "sig",
        domain: "localhost",
        path: "/",
      },
    ]);

    const response = await page.goto("/login");
    await expect(page).toHaveURL(/\/login$/);
    expect(response?.status()).toBe(200);
    await expect(page.locator("#email")).toBeVisible();
  });

  test("invalid refresh cookie falls through to /login", async ({ page, context }) => {
    // Garbage refresh token — the refresh call fails, middleware clears both
    // cookies, and /home redirects to /login as expected.
    await context.clearCookies();
    await context.addCookies([
      {
        name: "chirri_refresh",
        value: "not-a-valid-jwt",
        domain: "localhost",
        path: "/",
      },
    ]);

    await page.goto("/home");
    await expect(page).toHaveURL(/\/login$/);
  });
});
