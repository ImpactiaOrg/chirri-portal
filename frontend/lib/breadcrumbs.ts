import type { ClientUserDto } from "./api";
import type { Crumb } from "@/components/breadcrumb";

/**
 * Breadcrumb builders para las vistas del portal.
 *
 * Regla de brand: si el cliente tiene 1 sola marca, no se muestra crumb de brand.
 * Si tiene 2+, se incluye `brandName` después del cliente.
 *
 * Las vistas son jerárquicas:
 *   Cliente › [Brand] › Campañas › <Campaign> › <Stage?>
 *
 * El último crumb nunca tiene href (es la vista actual).
 */

function needsBrandCrumb(user: ClientUserDto): boolean {
  return (user.client?.brands.length ?? 0) > 1;
}

function clientLabel(user: ClientUserDto): string {
  return user.client?.name ?? "—";
}

export function campaignsListCrumbs(user: ClientUserDto): Crumb[] {
  const out: Crumb[] = [{ label: clientLabel(user) }];
  if (needsBrandCrumb(user)) {
    // Sin /campaigns por-brand todavía — brand queda como texto pelado.
    out.push({ label: user.client!.brands[0].name });
  }
  out.push({ label: "Campañas" });
  return out;
}

export function campaignDetailCrumbs(
  user: ClientUserDto,
  brandName: string,
  campaignName: string,
): Crumb[] {
  // No incluimos "Campañas" como crumb intermedio: la topbar ya tiene un botón
  // de Campañas activo, y el label de sección solo aparece cuando la sección
  // es la página actual (la lista). Esto mantiene el breadcrumb de detalle
  // simétrico con el de reports: Cliente [› Brand] › <item>.
  const out: Crumb[] = [{ label: clientLabel(user) }];
  if (needsBrandCrumb(user)) {
    out.push({ label: brandName });
  }
  out.push({ label: campaignName });
  return out;
}

export function reportDetailCrumbs(
  user: ClientUserDto,
  opts: {
    brandName: string;
    campaignId: number;
    campaignName: string;
    stageId: number;
    stageName: string;
  },
): Crumb[] {
  const out: Crumb[] = [{ label: clientLabel(user) }];
  if (needsBrandCrumb(user)) {
    out.push({ label: opts.brandName });
  }
  out.push({ label: opts.campaignName, href: `/campaigns/${opts.campaignId}` });
  out.push({
    label: opts.stageName,
    href: `/campaigns/${opts.campaignId}#stage-${opts.stageId}`,
  });
  return out;
}
