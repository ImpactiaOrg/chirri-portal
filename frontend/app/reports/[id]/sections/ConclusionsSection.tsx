import type { ReportDto } from "@/lib/api";
import { hasConclusions } from "@/lib/has-data";

export default function ConclusionsSection({ report }: { report: ReportDto }) {
  if (!hasConclusions(report)) return null;
  return (
    <section style={{ marginBottom: 48, maxWidth: 720 }}>
      <span className="pill-title mint">CONCLUSIONES</span>
      <div className="chirri-note" style={{ marginTop: 16 }}>
        {report.conclusions_text}
        <span className="sig">— CHIRRI</span>
      </div>
    </section>
  );
}
