import type { WidgetDto } from "@/lib/api";
import TextWidget from "./TextWidget";
import ImageWidget from "./ImageWidget";
import TextImageWidget from "./TextImageWidget";
import KpiGridWidget from "./KpiGridWidget";
import TableWidget from "./TableWidget";
import ChartWidget from "./ChartWidget";
import TopContentsWidget from "./TopContentsWidget";
import TopCreatorsWidget from "./TopCreatorsWidget";

export default function WidgetRenderer({ widget }: { widget: WidgetDto }) {
  switch (widget.type) {
    case "TextWidget":
      return <TextWidget widget={widget} />;
    case "ImageWidget":
      return <ImageWidget widget={widget} />;
    case "TextImageWidget":
      return <TextImageWidget widget={widget} />;
    case "KpiGridWidget":
      return <KpiGridWidget widget={widget} />;
    case "TableWidget":
      return <TableWidget widget={widget} />;
    case "ChartWidget":
      return <ChartWidget widget={widget} />;
    case "TopContentsWidget":
      return <TopContentsWidget widget={widget} />;
    case "TopCreatorsWidget":
      return <TopCreatorsWidget widget={widget} />;
    default: {
      const _exhaustive: never = widget;
      console.warn("unknown_widget_type", (_exhaustive as { type: string }).type);
      return null;
    }
  }
}
