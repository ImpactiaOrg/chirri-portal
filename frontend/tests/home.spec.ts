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
});
