import type { ReportBlockDto } from "@/lib/api";
import TextImageBlock from "./TextImageBlock";
import KpiGridBlock from "./KpiGridBlock";
import MetricsTableBlock from "./MetricsTableBlock";
import TopContentBlock from "./TopContentBlock";
import AttributionTableBlock from "./AttributionTableBlock";
import ChartBlock from "./ChartBlock";

export default function BlockRenderer({ block }: { block: ReportBlockDto }) {
  switch (block.type) {
    case "TextImageBlock":
      return <TextImageBlock block={block} />;
    case "KpiGridBlock":
      return <KpiGridBlock block={block} />;
    case "MetricsTableBlock":
      return <MetricsTableBlock block={block} />;
    case "TopContentBlock":
      return <TopContentBlock block={block} />;
    case "AttributionTableBlock":
      return <AttributionTableBlock block={block} />;
    case "ChartBlock":
      return <ChartBlock block={block} />;
    default: {
      // Exhaustiveness check — all union members are handled above.
      const _exhaustive: never = block;
      console.warn("unknown_block_type", (_exhaustive as { type: string }).type);
      return null;
    }
  }
}
