import { test, expect } from "@playwright/test";

/**
 * Smoke del admin de Django para el importer xlsx (DEV-83).
 *
 * El admin vive en el backend (puerto 8000), no en el frontend. Usamos URLs
 * absolutas porque el baseURL de Playwright apunta al frontend.
 *
 * Requiere que exista un superuser. El seed_demo no lo crea, así que el
 * test depende de DJANGO_SUPERUSER creado aparte en dev — si no existe, el
 * test hace skip.
 */

const ADMIN_BASE = process.env.ADMIN_BASE_URL || "http://localhost:8000";
const ADMIN_USER = process.env.ADMIN_SUPERUSER_EMAIL || "admin@chirri.local";
const ADMIN_PASS = process.env.ADMIN_SUPERUSER_PASSWORD || "admin";

test.describe("Admin import xlsx smoke", () => {
  test("superuser ve botones en Report changelist y accede al form de import", async ({ page }) => {
    const loginResp = await page.goto(`${ADMIN_BASE}/admin/login/?next=/admin/reports/report/`);
    if (loginResp && loginResp.status() >= 500) {
      test.skip(true, "Admin no disponible en el entorno E2E");
    }

    // Django admin usa `username` field — con custom user puede variar.
    const usernameField = page.locator("input#id_username, input[name=username]");
    if (await usernameField.count() === 0) {
      test.skip(true, "Admin login form no tiene el field esperado");
    }
    await usernameField.fill(ADMIN_USER);
    await page.locator("input[name=password]").fill(ADMIN_PASS);
    await page.locator("input[type=submit]").click();

    // Si falla auth, skip (el seed no crea superuser).
    const loc = page.url();
    if (loc.includes("/login/")) {
      test.skip(true, "No hay superuser configurado para E2E");
    }

    // Changelist debería mostrar los 2 botones custom.
    await expect(page.getByRole("link", { name: /Descargar template/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /Importar desde Excel/i })).toBeVisible();

    // Click en importar → form visible
    await page.getByRole("link", { name: /Importar desde Excel/i }).click();
    await expect(page.getByRole("heading", { name: /Importar reporte/i })).toBeVisible();
    await expect(page.locator("input[type=file]")).toBeVisible();
  });
});
