import type { ReportBlockDto, ReportDto } from "@/lib/api";
import TextImageBlock from "./TextImageBlock";
import KpiGridBlock from "./KpiGridBlock";
import MetricsTableBlock from "./MetricsTableBlock";
import TopContentBlock from "./TopContentBlock";
import AttributionTableBlock from "./AttributionTableBlock";
import ChartBlock from "./ChartBlock";

const BLOCK_COMPONENTS = {
  TEXT_IMAGE: TextImageBlock,
  KPI_GRID: KpiGridBlock,
  METRICS_TABLE: MetricsTableBlock,
  TOP_CONTENT: TopContentBlock,
  ATTRIBUTION_TABLE: AttributionTableBlock,
  CHART: ChartBlock,
} as const;

export default function BlockRenderer({
  block,
  report,
}: {
  block: ReportBlockDto;
  report: ReportDto;
}) {
  const Component = BLOCK_COMPONENTS[block.type as keyof typeof BLOCK_COMPONENTS];
  if (!Component) {
    console.warn("unknown_block_type", block.type);
    return null;
  }
  return <Component block={block} report={report} />;
}
