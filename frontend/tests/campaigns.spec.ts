import { test, expect } from "@playwright/test";
import { login, trackConsoleErrors } from "./helpers";

test.describe("Campaign detail smoke", () => {
  test("login → /campaigns → click active campaign → detail renders", async ({ page }) => {
    const errors = trackConsoleErrors(page);

    await login(page);

    await page.goto("/campaigns");
    await page.getByRole("link", { name: /abrir/i }).first().click();

    await expect(page).toHaveURL(/\/campaigns\/\d+$/);

    await expect(page.locator("h1").first()).toBeVisible();
    await expect(page.getByText(/balanz/i).first()).toBeVisible();
    await expect(page.locator("h3").first()).toBeVisible();
    await expect(page.locator('a[href^="/reports/"]').first()).toBeVisible();

    expect(
      errors,
      `console/page errors on /campaigns/<id>:\n${errors.join("\n")}`,
    ).toEqual([]);
  });

  test("report row navigates to /reports/<id>", async ({ page }) => {
    await login(page);
    await page.goto("/campaigns");
    await page.getByRole("link", { name: /abrir/i }).first().click();
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
    await page.getByRole("link", { name: /abrir/i }).first().click();
    await expect(page).toHaveURL(/\/campaigns\/\d+$/);

    const firstReport = page.locator('a[href^="/reports/"]').first();
    await firstReport.focus();
    await expect(firstReport).toBeFocused();

    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/reports\/\d+$/);
  });
});
