import { test, expect } from "@playwright/test";
import { login, trackConsoleErrors } from "./helpers";

test.describe("Report viewer · blocks", () => {
  test("seeded report renders all block sections in order", async ({ page }) => {
    const errors = trackConsoleErrors(page);

    await login(page);
    await page.goto("/campaigns");
    const activeSection = page
      .locator("section")
      .filter({ has: page.getByText(/activas ·/i) });
    await activeSection.getByRole("link").first().click();
    await expect(page).toHaveURL(/\/campaigns\/\d+$/);

    // Open the first "Reporte general · Marzo" report — this is the seeded
    // full report that carries the 11 block layout. Other reports on this
    // page are placeholders without blocks.
    await page
      .locator('a[href^="/reports/"]')
      .filter({ hasText: /reporte general · marzo/i })
      .first()
      .click();
    await expect(page).toHaveURL(/\/reports\/\d+$/);

    // Pill-titles we expect in order (from seed_demo blocks).
    // NOTE: the YoY block is present in seed_demo but renders null because
    // seed data has no prior-year reports — its pill correctly does not appear.
    const expectedPills = [
      /KPIS DEL MES/i,
      /MES A MES/i,
      /INSTAGRAM/i,
      /TIKTOK/i,
      /X \/ TWITTER/i,
      /POSTS DEL MES/i,
      /CREATORS DEL MES/i,
      /ATRIBUCIÓN ONELINK/i,
      /FOLLOWERS/i,
      /Q1 ROLLUP/i,
    ];
    for (const pill of expectedPills) {
      await expect(page.getByText(pill).first()).toBeVisible();
    }

    // Verify DOM order: first pill appears before last in DOM.
    const firstPill = page.getByText(expectedPills[0]).first();
    const lastPill = page.getByText(expectedPills[expectedPills.length - 1]).first();
    const firstBox = await firstPill.boundingBox();
    const lastBox = await lastPill.boundingBox();
    expect(firstBox && lastBox && firstBox.y < lastBox.y).toBeTruthy();

    expect(
      errors,
      `console/page errors on /reports/<id>:\n${errors.join("\n")}`,
    ).toEqual([]);
  });

  test("PDF download button absent when report has no original_pdf", async ({ page }) => {
    await login(page);
    await page.goto("/campaigns");
    const activeSection = page
      .locator("section")
      .filter({ has: page.getByText(/activas ·/i) });
    await activeSection.getByRole("link").first().click();
    await page.locator('a[href^="/reports/"]').first().click();
    await expect(page).toHaveURL(/\/reports\/\d+$/);

    // seed_demo doesn't upload PDFs, so button should not appear.
    await expect(page.getByRole("link", { name: /descargar pdf original/i })).toHaveCount(0);
  });
});
