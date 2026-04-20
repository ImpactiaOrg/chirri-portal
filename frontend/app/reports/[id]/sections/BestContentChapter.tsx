import type { ReportDto } from "@/lib/api";
import { hasTopContent } from "@/lib/has-data";
import ContentCard from "../components/ContentCard";

export default function BestContentChapter({ report }: { report: ReportDto }) {
  const posts = report.top_content.filter((c) => c.kind === "POST");
  const creators = report.top_content.filter((c) => c.kind === "CREATOR");
  if (posts.length === 0 && creators.length === 0) return null;

  return (
    <section style={{ marginBottom: 48 }}>
      <span className="pill-title mint">BEST CONTENT</span>
      {hasTopContent(report, "POST") && (
        <>
          <h3 className="font-display" style={{ fontSize: 32, margin: "16px 0", textTransform: "lowercase" }}>
            posts del mes
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
            {posts.map((c, i) => <ContentCard key={`p${i}`} content={c} />)}
          </div>
        </>
      )}
      {hasTopContent(report, "CREATOR") && (
        <>
          <h3 className="font-display" style={{ fontSize: 32, margin: "24px 0 16px", textTransform: "lowercase" }}>
            creators del mes
          </h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
            {creators.map((c, i) => <ContentCard key={`c${i}`} content={c} />)}
          </div>
        </>
      )}
    </section>
  );
}
