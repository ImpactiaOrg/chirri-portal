import type { ReportDto } from "@/lib/api";
import { hasIntro } from "@/lib/has-data";

export default function IntroText({ report }: { report: ReportDto }) {
  if (!hasIntro(report)) return null;
  return (
    <section style={{ marginBottom: 40, maxWidth: 720 }}>
      <span className="pill-title">INTRO</span>
      <p style={{ fontSize: 18, lineHeight: 1.5, marginTop: 16, fontWeight: 500 }}>
        {report.intro_text}
      </p>
    </section>
  );
}
