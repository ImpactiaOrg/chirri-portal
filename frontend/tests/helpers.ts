import { expect, type Page } from "@playwright/test";

export const SEED_USER = {
  email: "belen.rizzo@balanz.com",
  password: "balanz2026",
};

export async function login(page: Page, creds = SEED_USER) {
  await page.goto("/login");
  await page.fill("#email", creds.email);
  await page.fill("#password", creds.password);
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL(/\/home$/);
}

/**
 * Fail the current test if any uncaught error or `console.error` fires on
 * the page while the test is running. Catches the class of bug we hit today
 * ("Unexpected end of JSON input") that would otherwise leave the test green.
 */
export function trackConsoleErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("pageerror", (err) => errors.push(`pageerror: ${err.message}`));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(`console.error: ${msg.text()}`);
  });
  return errors;
}
