# Reports Analysis - DEV-117

**Date:** 2026-04-23
**Reports analyzed:** 9
- P10 (Balanz): Abr 25, Aug 25, Jan 26, Mar 26
- UC (Ultracomb): Mar 26
- FW (Mundo FW): Nov 25, Ene 26, Feb 26, Mar 26

**Verdict:** Los 6 subtypes post-DEV-116 cubren ~95% del contenido observado. Aparecen 2 gaps menores: (1) ChartBlock.chart_type solo soporta bar pero los followers-growth charts de P10 son line; (2) en FW los TopContent items tienen metadata ads vs sin pauta que hoy vive en el JSONField metrics y gana mucho si se tipea como source_type. Ambos son extensiones triviales, no nuevos subtypes.

## Brands y layouts

### P10 (Balanz) - monthly GENERAL reports

**Shape observado** (consistente Abr 25 -> Mar 26, 4 meses):

1. Cover + title -> TextImageBlock (title + image)
2. Introduction ("analyze results of X vs Y") -> TextImageBlock (body)
3. Side-by-side month comparison (reach: organic/paid/influencer/total + views) -> MetricsTableBlock(network=INSTAGRAM) con period_comparison en rows
4. Likes/shared/comments/saved comparison IG -> MetricsTableBlock(network=INSTAGRAM) con rows y period_comparison
5. IG Followers growth chart (6-7 meses, LINE) -> ChartBlock(network=INSTAGRAM) - **gap 1**
6. Last 3 months engagement (3 cols con ER + likes/shared/comments/saved) -> MetricsTableBlock con rows repetidos
7. Best organic post -> TopContentBlock(kind=POST, limit=1)
8. Best influencer post -> TopContentBlock(kind=POST, limit=1) o kind=CREATOR
9. UTM Performance / ONELINK -> AttributionTableBlock (ya existe)
10. TikTok monthly card -> KpiGridBlock (tiles con views/likes/comments/shared/new_followers)
11. TikTok followers growth (cuando aparece) -> ChartBlock(network=TIKTOK) (line)
12. X followers growth (solo Mar 26) -> ChartBlock(network=X)
13. Conclusions (prosa 4-6 parrafos) -> TextImageBlock(body)

**Variations month-to-month:** agregado/quitado de network sections (X solo Mar 26; TikTok gana bloques en meses recientes). Last 3 months es consistente. En Aug 25 aparece Paid Reach 10x el organico (591k vs 11k) - el subtype cubre, la escala pide formateo frontend.

### UC (Ultracomb) - monthly

**Shape observado** (1 muestra, Mar 26):

1. Big Numbers -> KpiGridBlock (followers + delta, posts count, reach, views, likes/comments/shares)
2. Top Contenidos -> TopContentBlock(kind=POST, limit=3) - con metrica TASA RET (tasa retencion) cubierta por el JSONField actual
3. Top Creadores -> TopContentBlock(kind=CREATOR, limit=3)
4. Resumen del mes - patron interesante: el PDF muestra prosa de DOS brands lado a lado (Yelmo + Ultracomb). En el portal (single-brand por report) se colapsa a TextImageBlock(body) con solo la parte de la brand del report.

**Variations:** 1 sola muestra UC; se asume estabilidad por simetria con P10/FW.

### FW (Mundo FW) - monthly

**Shape observado** (Nov 25, Ene 26, Feb 26, Mar 26 - 4 meses):

Nov 25 es atipico - casi todo es imagen/diagrama sin texto extraible, solo conclusions visible. Los meses Ene/Feb/Mar 26 son mas ricos:

1. Estadisticas IG -> MetricsTableBlock(network=INSTAGRAM) con rows: seguidores + delta%, alcance, visualizaciones publicaciones/perfil, engagement, likes, comentarios, compartidos, repost, guardados
2. Top Reels -> TopContentBlock(kind=POST, limit=3) - cada item tiene flag ads vs sin pauta - **gap 2**
3. Top Reels sin pauta -> a veces bloque aparte, a veces mezclado
4. Top Posts -> TopContentBlock(kind=POST, limit=3) mismo pattern ads/sin pauta
5. Top Stories (solo Nov 25, intermitente) -> TopContentBlock(kind=POST) - gap potencial, ver abajo
6. Metricas Organicas Posts / Reels (solo Ene 26) -> MetricsTableBlock(network=INSTAGRAM) con source_type=ORGANIC
7. TikTok Metricas Clave -> KpiGridBlock o MetricsTableBlock(network=TIKTOK)
8. TikTok Top Contenidos -> TopContentBlock(kind=POST, limit=3) con network TT
9. Wrapped IG ("Dato MUY importante") -> TextImageBlock
10. Conclusion Tik Tok / Conclusion IG (2 narrativas separadas por network) -> 2x TextImageBlock

**Variations month-to-month:** FW varia mas que P10. Ene 26 separa Metricas Organicas Posts de Reels. Feb 26 no los tiene. Top Stories aparece solo Nov 25. La variacion es manejable con el operator decidiendo que blocks incluir por mes.

## Gaps encontrados

### Gap 1: ChartBlock solo soporta bar

- **Ejemplo:** P10 Abr 25, Aug 25, Jan 26 - followers growth chart es **line**, no bar. Visualmente distinto (curva temporal) vs bar (comparacion discreta).
- **Subtype actual:** ChartBlock(chart_type="bar") - spec DEV-116 ya declara el enum extensible.
- **Propuesta:** agregar "line" al enum chart_type. Cambio trivial (migration + frontend renderer).
- **Prioridad:** bloqueante DEV-118 si los templates generan followers-growth charts (son estandar en P10). Nice-to-have si DEV-118 arranca como operacion manual.

### Gap 2: TopContent.metrics agrupa ads_status en JSON

- **Ejemplo:** FW Feb 26, Mar 26 - Top Reels/Posts separan visualmente ads vs sin pauta. Metadata semantica consistente cross-month.
- **Subtype actual:** TopContent.metrics JSONField. Funcional para display, pero sin filtrado ni query por ads_status, y el frontend tiene que parsear el JSON.
- **Propuesta:** agregar TopContent.source_type field tipado reusando SourceType choices (ORGANIC/INFLUENCER/PAID). Ya existe en MetricsTableRow - consistencia cross-model.
- **Prioridad:** nice-to-have. El JSON cubre el viewer actual; no bloquea DEV-118.

### Gap 3: Stories como seccion propia

- **Ejemplo:** FW Nov 25 tenia Top Stories.
- **Subtype actual:** TopContentBlock(kind=POST) sin distincion.
- **Propuesta:** skip. Aparece 1 de 9 reportes; resoluble con instructions + title="Top Stories".
- **Prioridad:** skip.

## Patterns -> Templates candidatos

Tres templates claros, uno por brand. Basados en el layout mas completo (Mar 26 para cada):

- **P10 monthly (Balanz)** (~11-13 blocks):
  1. TextImageBlock (cover/title)
  2. TextImageBlock (introduction)
  3. MetricsTableBlock(IG) (reach/views comparison)
  4. MetricsTableBlock(IG) (engagement detail)
  5. ChartBlock(IG, line) (followers growth)
  6. MetricsTableBlock(IG) (last 3 months rolling)
  7. TopContentBlock(POST, limit=1) (best organic)
  8. TopContentBlock(POST or CREATOR, limit=1) (best influencer)
  9. AttributionTableBlock (UTM/OneLink)
  10. KpiGridBlock (TikTok monthly card)
  11. ChartBlock(TT) (TikTok followers growth, opcional)
  12. ChartBlock(X) (X followers growth, opcional)
  13. TextImageBlock (conclusions)

- **UC monthly (Ultracomb)** (~4-5 blocks):
  1. KpiGridBlock (big numbers)
  2. TopContentBlock(POST, limit=3) (top contenidos)
  3. TopContentBlock(CREATOR, limit=3) (top creadores)
  4. TextImageBlock (resumen del mes)

- **FW monthly (Mundo FW)** (~8-10 blocks):
  1. MetricsTableBlock(IG) (estadisticas IG)
  2. TopContentBlock(POST, limit=3) (top reels, metadata ads)
  3. TopContentBlock(POST, limit=3) (top posts, metadata ads)
  4. MetricsTableBlock(IG, source_type=ORGANIC) (metricas organicas posts) - opcional
  5. MetricsTableBlock(IG, source_type=ORGANIC) (metricas organicas reels) - opcional
  6. KpiGridBlock o MetricsTableBlock(TT) (TikTok metricas clave)
  7. TopContentBlock(POST, limit=3) (top tiktok)
  8. TextImageBlock (conclusion TikTok)
  9. TextImageBlock (conclusion IG)
  10. TextImageBlock (wrapped IG - opcional)

## Extensiones a subtypes existentes

1. **ChartBlock.chart_type** - agregar "line" al enum. **Recomendado.**
2. **TopContent.source_type** - agregar field tipado reusando SourceType choices. **Nice-to-have.**
3. **TopContent.metrics JSONField** - la decision DEV-116 de mantenerlo JSON sigue siendo correcta; los sets de metricas varian entre brands (P10: views/reach/likes/shared/comments/saved; UC: +tasa_retencion; FW: +repost/guardados). Confirmado: no typear.
4. **MetricsTableBlock** - no se observan gaps; acepta rows con cualquier metric_name libre, cubre todas las variantes (ER, delta %, followers, alcance, visualizaciones perfil, etc.).

## Follow-up tickets propuestos

1. **DEV-119 (sugerido): ChartBlock.chart_type=line** - agregar line al enum + renderer frontend. Scope: migration + componente frontend. Estimate: 2h. Potencial bloqueante DEV-118.

2. **DEV-120 (sugerido, opcional): TopContent.source_type** - agregar field tipado para ads/organic/influencer. Scope: migration + admin form + frontend badge. Estimate: 3h. No bloqueante.

3. **Update seed_demo (parte de DEV-118)** - reflejar los 3 templates distintos (P10/UC/FW) en seed_demo.py cuando DEV-118 defina el modelo ReportTemplate. No es ticket standalone.

## Reports skipped

Ninguno. Las 5 extracciones nuevas + 4 pre-extraidas corrieron todas en <30s. Los 7 reportes P10 restantes (May, Jul, Sep, Oct, Nov, Dec 25 + Feb 26) y los 3 FW restantes (Dic 25 + 2 marzo variants) no se extrajeron porque el shape ya es estable en los 4 meses P10 y 4 meses FW muestreados - extraer mas no agrega informacion.
