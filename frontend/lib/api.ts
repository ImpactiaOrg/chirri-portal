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

export type Network = "INSTAGRAM" | "TIKTOK" | "X";
export type SourceType = "ORGANIC" | "INFLUENCER" | "PAID";

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
  reach_total: string | number | null;
};

export type CampaignReportRowDto = {
  id: number;
  title: string;
  display_title: string;
  kind: "INFLUENCER" | "GENERAL" | "QUINCENAL" | "MENSUAL" | "CIERRE_ETAPA";
  period_start: string;
  period_end: string;
  published_at: string;
  reach_total: string | null;
};

export type StageWithReportsDto = {
  id: number;
  order: number;
  kind: "AWARENESS" | "EDUCATION" | "VALIDATION" | "CONVERSION" | "ONGOING" | "OTHER";
  name: string;
  description: string;
  start_date: string | null;
  end_date: string | null;
  reports: CampaignReportRowDto[];
  reach_total: string | number | null;
};

export type CampaignDetailDto = {
  id: number;
  brand_name: string;
  name: string;
  brief: string;
  status: "ACTIVE" | "FINISHED" | "PAUSED";
  start_date: string | null;
  end_date: string | null;
  is_ongoing_operation: boolean;
  stages_with_reports: StageWithReportsDto[];
};

// -- Child DTOs --

export type KpiTileDto = {
  label: string;
  value: string;
  unit: string;
  period_comparison: string | null;
  period_comparison_label: string;
  order: number;
};

export type TableRowDto = {
  order: number;
  is_header: boolean;
  cells: string[];
};

export type ChartDataPointDto = {
  label: string;
  value: string;
  order: number;
};

export type TopContentItemDto = {
  order: number;
  thumbnail_url: string | null;
  caption: string;
  post_url: string;
  source_type: SourceType;
  views: number | null;
  likes: number | null;
  comments: number | null;
  shares: number | null;
  saves: number | null;
};

export type TopCreatorItemDto = {
  order: number;
  thumbnail_url: string | null;
  handle: string;
  post_url: string;
  views: number | null;
  likes: number | null;
  comments: number | null;
  shares: number | null;
};

// -- Widget subtype DTOs (discriminated union on `type`) --

type BaseWidgetFields = {
  id: number;
  order: number;
  title: string;
  instructions: string;
};

export type TextWidgetDto = BaseWidgetFields & {
  type: "TextWidget";
  body: string;
};

export type ImageWidgetDto = BaseWidgetFields & {
  type: "ImageWidget";
  image_url: string | null;
  image_alt: string;
  caption: string;
};

export type TextImageWidgetDto = BaseWidgetFields & {
  type: "TextImageWidget";
  body: string;
  columns: 1 | 2 | 3;
  image_position: "left" | "right" | "top";
  image_alt: string;
  image_url: string | null;
};

export type KpiGridWidgetDto = BaseWidgetFields & {
  type: "KpiGridWidget";
  tiles: KpiTileDto[];
};

export type TableWidgetDto = BaseWidgetFields & {
  type: "TableWidget";
  show_total: boolean;
  rows: TableRowDto[];
};

export type ChartWidgetDto = BaseWidgetFields & {
  type: "ChartWidget";
  network: Network | null;
  chart_type: "bar" | "line";
  description: string;
  data_points: ChartDataPointDto[];
};

export type TopContentsWidgetDto = BaseWidgetFields & {
  type: "TopContentsWidget";
  network: Network | null;
  period_label: string;
  items: TopContentItemDto[];
};

export type TopCreatorsWidgetDto = BaseWidgetFields & {
  type: "TopCreatorsWidget";
  network: Network | null;
  period_label: string;
  items: TopCreatorItemDto[];
};

export type WidgetDto =
  | TextWidgetDto
  | ImageWidgetDto
  | TextImageWidgetDto
  | KpiGridWidgetDto
  | TableWidgetDto
  | ChartWidgetDto
  | TopContentsWidgetDto
  | TopCreatorsWidgetDto;

// -- Section --

export type SectionLayout = "stack" | "columns_2" | "columns_3";

export type SectionDto = {
  id: number;
  order: number;
  title: string;
  layout: SectionLayout;
  instructions: string;
  widgets: WidgetDto[];
};

export type ReportAttachmentKind = "PDF_REPORT" | "DATA_EXPORT" | "ANNEX" | "OTHER";

export type ReportAttachmentDto = {
  id: number;
  title: string;
  url: string | null;
  mime_type: string;
  size_bytes: number;
  kind: ReportAttachmentKind;
  order: number;
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
  intro_text: string;
  conclusions_text: string;
  stage_id: number;
  stage_name: string;
  campaign_id: number;
  campaign_name: string;
  brand_name: string;
  sections: SectionDto[];
  attachments: ReportAttachmentDto[];
};

export type PagedResponse<T> = { count: number; next: string | null; previous: string | null; results: T[] };
