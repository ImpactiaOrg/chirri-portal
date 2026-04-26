import { test, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

/**
 * Smoke for the PDF importer admin view (DEV-84).
 *
 * Requires a superuser to exist (same convention as admin-import.spec.ts).
 * Mocks the Fireworks endpoint via page.route — no real LLM call.
 */

const ADMIN_BASE = process.env.ADMIN_BASE_URL || "http://localhost:8000";
const ADMIN_USER = process.env.ADMIN_SUPERUSER_EMAIL || "admin@chirri.local";
const ADMIN_PASS = process.env.ADMIN_SUPERUSER_PASSWORD || "admin";

const PARSED = {
  kind: "MENSUAL",
  period_start: "2026-04-01",
  period_end: "2026-04-30",
  title: "Reporte E2E PDF",
  intro_text: "",
  conclusions_text: "OK",
  layout: [[1, "intro"]],
  blocks: {
    intro: {
      type_name: "TextImageBlock",
      nombre: "intro",
      fields: {
        title: "Hola", body: "Body", image_alt: "",
        image_position: "top", columns: 1, imagen: "",
      },
      items: [],
    },
  },
};

test.describe("Admin import PDF (AI) smoke", () => {
  test("superuser sube un PDF, ve el job pollear, y aterriza en el Report", async ({ page }) => {
    // 1) Mock Fireworks BEFORE login (page.route persists across nav).
    await page.route("**/api.fireworks.ai/**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "x", object: "chat.completion", created: 0, model: "kimi",
          choices: [{
            index: 0, finish_reason: "stop",
            message: { role: "assistant", content: JSON.stringify(PARSED) },
          }],
          usage: { prompt_tokens: 100, completion_tokens: 200, total_tokens: 300 },
        }),
      });
    });

    // 2) Login.
    const loginResp = await page.goto(`${ADMIN_BASE}/admin/login/?next=/admin/reports/report/import-pdf/`);
    if (loginResp && loginResp.status() >= 500) test.skip(true, "Admin no disponible");
    const usernameField = page.locator("input#id_username, input[name=username]");
    if (await usernameField.count() === 0) test.skip(true, "Login form missing");
    await usernameField.fill(ADMIN_USER);
    await page.locator("input[name=password]").fill(ADMIN_PASS);
    await page.locator("input[type=submit]").click();
    if (page.url().includes("/login/")) test.skip(true, "No superuser configured");

    // 3) Form should be visible.
    await expect(page.getByRole("heading", { name: /Importar reporte desde PDF/i })).toBeVisible();

    // 4) Pick the first available stage (cascade Client → Brand → Campaign → Stage).
    const clientSelect = page.locator("select[name=client]");
    await clientSelect.selectOption({ index: 1 });
    await page.locator("select[name=brand] option:not([value=''])").first().waitFor();
    await page.locator("select[name=brand]").selectOption({ index: 1 });
    await page.locator("select[name=campaign] option:not([value=''])").first().waitFor();
    await page.locator("select[name=campaign]").selectOption({ index: 1 });
    await page.locator("select[name=stage] option:not([value=''])").first().waitFor();
    await page.locator("select[name=stage]").selectOption({ index: 1 });

    // 5) Upload a tiny PDF generated on the fly.
    const tmpPdf = path.join(__dirname, "tmp-sample.pdf");
    if (!fs.existsSync(tmpPdf)) {
      // Minimal 1-page PDF (hand-crafted, valid).
      fs.writeFileSync(tmpPdf, Buffer.from(
        "%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n" +
        "2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n" +
        "3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 100 100]>>endobj\n" +
        "xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n" +
        "0000000053 00000 n \n0000000098 00000 n \n" +
        "trailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%%EOF\n",
        "binary",
      ));
    }
    await page.locator("input[type=file]").setInputFiles(tmpPdf);
    await page.locator("input[type=submit]").click();

    // 6) Should land on /admin/llm/llmjob/<id>/
    await expect(page).toHaveURL(/\/admin\/llm\/llmjob\/\d+\/$/);

    // 7) Wait for SUCCESS (CELERY_TASK_ALWAYS_EAGER in dev makes this fast).
    await expect(page.locator("#llm-job-status")).toHaveText(/SUCCESS|FAILED/, {
      timeout: 30_000,
    });
    await expect(page.locator("#llm-job-status")).toHaveText("SUCCESS");

    // 8) "Ver resultado →" link visible and points to the new report.
    await expect(page.locator("#llm-job-result-link")).toBeVisible();
    await expect(page.locator("#llm-job-result-anchor"))
      .toHaveAttribute("href", /\/admin\/reports\/report\/\d+\/change\/$/);
  });
});
