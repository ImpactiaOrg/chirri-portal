import { test, expect } from "@playwright/test";
import { login, trackConsoleErrors } from "./helpers";

test.describe("Campaign detail smoke", () => {
  test("login → /campaigns → click active campaign → detail renders", async ({ page }) => {
    const errors = trackConsoleErrors(page);

    await login(page);

    await page.goto("/campaigns");
    // Scope to the ACTIVAS section so we never accidentally open an archived row.
    const activeSection = page
      .locator("section")
      .filter({ has: page.getByText(/activas ·/i) });
    await activeSection.getByRole("link").first().click();

    await expect(page).toHaveURL(/\/campaigns\/\d+$/);

    await expect(page.locator("h1").first()).toBeVisible();
    await expect(page.getByText(/balanz/i).first()).toBeVisible();
    await expect(page.locator("h3").first()).toBeVisible();
    await expect(page.locator('a[href^="/reports/"]').first()).toBeVisible();

    // "ÚLTIMO" pill marks the single most recent published report in the campaign.
    // Expect exactly one when the campaign has at least one report row.
    const latestPill = page.getByText("ÚLTIMO", { exact: true });
    await expect(latestPill).toHaveCount(1);

    expect(
      errors,
      `console/page errors on /campaigns/<id>:\n${errors.join("\n")}`,
    ).toEqual([]);
  });

  test("report row navigates to /reports/<id>", async ({ page }) => {
    await login(page);
    await page.goto("/campaigns");
    // Scope to the ACTIVAS section so we never accidentally open an archived row.
    const activeSection = page
      .locator("section")
      .filter({ has: page.getByText(/activas ·/i) });
    await activeSection.getByRole("link").first().click();
    await expect(page).toHaveURL(/\/campaigns\/\d+$/);

    await page.locator('a[href^="/reports/"]').first().click();
    await expect(page).toHaveURL(/\/reports\/\d+$/);
    await expect(page.locator("h1").first()).toBeVisible();
  });

  test("unknown campaign id returns 404", async ({ page }) => {
    await login(page);
    const response = await page.goto("/campaigns/999999");
    expect(response?.status()).toBe(404);
  });

  test("keyboard navigation: Tab reaches first report link and Enter opens it", async ({ page }) => {
    await login(page);
    await page.goto("/campaigns");
    // Scope to the ACTIVAS section so we never accidentally open an archived row.
    const activeSection = page
      .locator("section")
      .filter({ has: page.getByText(/activas ·/i) });
    await activeSection.getByRole("link").first().click();
    await expect(page).toHaveURL(/\/campaigns\/\d+$/);

    const firstReport = page.locator('a[href^="/reports/"]').first();
    await firstReport.focus();
    await expect(firstReport).toBeFocused();

    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/reports\/\d+$/);
  });
});
