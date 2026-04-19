const BACKEND = process.env.BACKEND_INTERNAL_URL || "http://backend:8000";

type FetchOpts = RequestInit & { token?: string | null };

export async function apiFetch<T = unknown>(path: string, opts: FetchOpts = {}): Promise<T> {
  const { token, headers, ...rest } = opts;
  const res = await fetch(`${BACKEND}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export class ApiError extends Error {
  status: number;
  body: string;
  constructor(status: number, body: string) {
    super(`API ${status}: ${body}`);
    this.status = status;
    this.body = body;
  }
}

export type ClientUserDto = {
  id: number;
  email: string;
  full_name: string;
  role: "VIEWER" | "ADMIN_CLIENT";
  is_staff: boolean;
  client: {
    id: number;
    name: string;
    logo_url: string;
    primary_color: string;
    secondary_color: string;
    brands: { id: number; name: string; logo_url: string }[];
  } | null;
};

export type LoginResponse = {
  access: string;
  refresh: string;
  user: ClientUserDto;
};

export type StageSummary = {
  id: number;
  order: number;
  kind: string;
  name: string;
};

export type CampaignDto = {
  id: number;
  brand_name: string;
  name: string;
  brief: string;
  status: "ACTIVE" | "FINISHED" | "PAUSED";
  start_date: string | null;
  end_date: string | null;
  is_ongoing_operation: boolean;
  stages: StageSummary[];
  stage_count: number;
  published_report_count: number;
  last_published_at: string | null;
};

export type ReportMetricDto = {
  network: "INSTAGRAM" | "TIKTOK" | "X";
  source_type: "ORGANIC" | "INFLUENCER" | "PAID";
  metric_name: string;
  value: string;
  period_comparison: string | null;
};

export type ReportDto = {
  id: number;
  kind: "INFLUENCER" | "GENERAL" | "QUINCENAL" | "MENSUAL" | "CIERRE_ETAPA";
  period_start: string;
  period_end: string;
  title: string;
  display_title: string;
  status: "DRAFT" | "PUBLISHED";
  published_at: string | null;
  conclusions_text: string;
  stage_id: number;
  stage_name: string;
  campaign_id: number;
  campaign_name: string;
  metrics: ReportMetricDto[];
};

export type PagedResponse<T> = { count: number; next: string | null; previous: string | null; results: T[] };
