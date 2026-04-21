import type { ReportBlockDto } from "@/lib/api";

type TextImageConfig = {
  title?: string;
  text?: string;
  columns: 1 | 2 | 3;
  image_position: "left" | "right" | "top";
};

export default function TextImageBlock({ block }: { block: ReportBlockDto }) {
  const cfg = block.config as unknown as TextImageConfig;
  if (!cfg || ![1, 2, 3].includes(cfg.columns as number)) {
    console.warn("invalid_text_image_config", block.id, cfg);
    return null;
  }
  const hasImage = !!block.image_url;
  const hasText = !!(cfg.text || cfg.title);
  if (!hasImage && !hasText) return null;

  const position = cfg.image_position ?? "top";
  const direction =
    position === "top" || !hasImage
      ? "column"
      : position === "right"
        ? "row"
        : "row-reverse";

  return (
    <section style={{ marginBottom: 48 }}>
      {cfg.title && <span className="pill-title">{cfg.title.toUpperCase()}</span>}
      <div
        style={{
          display: "flex",
          flexDirection: direction,
          gap: 24,
          alignItems: "flex-start",
          marginTop: 16,
        }}
      >
        {hasImage && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={block.image_url!}
            alt=""
            style={{ maxWidth: hasText ? "50%" : "100%", borderRadius: 8 }}
          />
        )}
        {cfg.text && (
          <div
            style={{
              columnCount: cfg.columns,
              columnGap: 24,
              maxWidth: 720,
              whiteSpace: "pre-wrap",
            }}
          >
            {cfg.text}
          </div>
        )}
      </div>
    </section>
  );
}
