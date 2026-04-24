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

    // Open the "Reporte general · Marzo" inside the Educación stage. Two
    // stages seed a report with this exact title (Educación and Validación),
    // and StagesTimeline renders stages in reverse order — so `first()` on
    // a page-wide match lands on Validación's, which only has INSTAGRAM
    // metrics and therefore hides the X/Twitter and TikTok METRICS_TABLE
    // blocks. We want the Educación one, which carries the full metric set.
    const educacionStage = page
      .locator('li[id^="stage-"]')
      .filter({ has: page.locator("h3", { hasText: /educación/i }) });
    await educacionStage
      .locator('a[href^="/reports/"]')
      .filter({ hasText: /reporte general · marzo/i })
      .first()
      .click();
    await expect(page).toHaveURL(/\/reports\/\d+$/);

    // Pill-titles we expect in order (from seed_demo typed blocks).
    // Post-DEV-116: YoY and Q1 rollup blocks no longer exist — their data
    // used to be computed from cross-report aggregates (ReportMetric) that
    // were removed when blocks became self-contained snapshots.
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

  test("Descargas section exposes the seeded PDF attachment", async ({ page }) => {
    await login(page);
    await page.goto("/campaigns");
    const activeSection = page
      .locator("section")
      .filter({ has: page.getByText(/activas ·/i) });
    await activeSection.getByRole("link").first().click();
    await page.locator('a[href^="/reports/"]').first().click();
    await expect(page).toHaveURL(/\/reports\/\d+$/);

    // seed_demo adjunta un PDF a todo reporte publicado (DEV-108).
    await expect(page.getByText(/^descargas$/i).first()).toBeVisible();
    const pdfLink = page
      .getByRole("link", { name: /reporte \(pdf\)/i })
      .first();
    await expect(pdfLink).toBeVisible();

    // The footer CTA points at the same first PDF_REPORT attachment.
    await expect(page.getByRole("link", { name: /descargar reporte/i })).toBeVisible();
  });
});
