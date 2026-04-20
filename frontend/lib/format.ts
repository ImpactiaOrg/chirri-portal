export const MONTHS_ES = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

export const MONTHS_ES_SHORT = [
  "ene", "feb", "mar", "abr", "may", "jun",
  "jul", "ago", "sep", "oct", "nov", "dic",
];

export function formatMonthYear(iso: string): { month: string; year: string } {
  const d = new Date(iso);
  return { month: MONTHS_ES[d.getUTCMonth()], year: String(d.getUTCFullYear()) };
}

/**
 * Formatea un período de campaña en español.
 *
 * Reglas:
 *  - is_ongoing_operation=true → "operación continua"
 *  - sin end_date            → "feb 2026 – en curso"
 *  - mismo año               → "feb – dic 2025"
 *  - cruza año               → "feb 2024 – dic 2025"
 *  - sin start_date          → "—" (defensivo)
 */
export function formatPeriod(
  startDate: string | null,
  endDate: string | null,
  isOngoing: boolean,
): string {
  if (isOngoing) return "operación continua";
  if (!startDate) return "—";

  const start = new Date(startDate);
  const startMonth = MONTHS_ES_SHORT[start.getUTCMonth()];
  const startYear = start.getUTCFullYear();

  if (!endDate) {
    return `${startMonth} ${startYear} – en curso`;
  }

  const end = new Date(endDate);
  const endMonth = MONTHS_ES_SHORT[end.getUTCMonth()];
  const endYear = end.getUTCFullYear();

  if (startYear === endYear) {
    return `${startMonth} – ${endMonth} ${endYear}`;
  }
  return `${startMonth} ${startYear} – ${endMonth} ${endYear}`;
}

/**
 * Formatea una fecha ISO de reporte publicado.
 *  - "2026-04-15T10:23:00Z" → "15 abr 2026"
 *  - null                    → "sin reportes"
 */
export function formatReportDate(iso: string | null): string {
  if (!iso) return "sin reportes";
  const d = new Date(iso);
  const day = d.getUTCDate();
  const month = MONTHS_ES_SHORT[d.getUTCMonth()];
  const year = d.getUTCFullYear();
  return `${day} ${month} ${year}`;
}
