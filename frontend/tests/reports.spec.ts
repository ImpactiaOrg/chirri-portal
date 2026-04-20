import { test, expect } from "@playwright/test";
import { login, trackConsoleErrors } from "./helpers";

test.describe("Report viewer smoke", () => {
  test("login → home → click latest report → /reports/<id> renders", async ({ page }) => {
    const errors = trackConsoleErrors(page);

    await login(page);

    // "Leer reporte" on home is inside the latest-report hero link.
    await page.getByRole("link", { name: /leer reporte/i }).first().click();

    await expect(page).toHaveURL(/\/reports\/\d+$/);

    // Header
    await expect(page.locator("h1").first()).toBeVisible();
    // Brand + campaign eyebrow
    await expect(page.getByText(/balanz/i).first()).toBeVisible();
    // At least one KPI tile
    await expect(page.getByText(/total reach/i).first()).toBeVisible();
    // Best content section heading (seed has 2 posts + 1 creator).
    await expect(page.getByText(/posts del mes/i).first()).toBeVisible();

    expect(errors, `console/page errors on /reports/<id>:\n${errors.join("\n")}`).toEqual([]);
  });

  test("unknown report id returns 404", async ({ page }) => {
    await login(page);
    const response = await page.goto("/reports/99999");
    expect(response?.status()).toBe(404);
  });

  test("cross-tenant report access is 404", async ({ page }) => {
    // We don't have a rival user configured for E2E; skip if not seeded.
    // Kept here as a placeholder for future seed extension.
    test.skip(true, "Rival user not in E2E seed");
  });
});
