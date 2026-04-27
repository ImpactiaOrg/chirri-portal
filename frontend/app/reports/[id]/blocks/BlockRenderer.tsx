import type { ReportBlockDto } from "@/lib/api";
import TextImageBlock from "./TextImageBlock";
import ImageBlock from "./ImageBlock";
import KpiGridBlock from "./KpiGridBlock";
import TableBlock from "./TableBlock";
import TopContentsBlock from "./TopContentsBlock";
import TopCreatorsBlock from "./TopCreatorsBlock";
import ChartBlock from "./ChartBlock";

export default function BlockRenderer({ block }: { block: ReportBlockDto }) {
  switch (block.type) {
    case "TextImageBlock":
      return <TextImageBlock block={block} />;
    case "ImageBlock":
      return <ImageBlock block={block} />;
    case "KpiGridBlock":
      return <KpiGridBlock block={block} />;
    case "TableBlock":
      return <TableBlock block={block} />;
    case "TopContentsBlock":
      return <TopContentsBlock block={block} />;
    case "TopCreatorsBlock":
      return <TopCreatorsBlock block={block} />;
    case "ChartBlock":
      return <ChartBlock block={block} />;
    default: {
      const _exhaustive: never = block;
      console.warn("unknown_block_type", (_exhaustive as { type: string }).type);
      return null;
    }
  }
}
