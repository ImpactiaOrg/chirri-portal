# Report Viewer `/reports/[id]` — Design

**Linear:** DEV-52
**Date:** 2026-04-20
**Author:** Daniel Zacharias (via Claude)
**Status:** Done — 2026-04-20

## Contexto

Pantalla core del piloto Chirri Portal. El cliente (Balanz como primer piloto) abre el portal y ve el reporte mensual listo — reemplaza al Google Slides que hoy Chirri le manda con su branding.

Desde `/home` ya hay un link al "último reporte" (404 hoy). `/campaigns` y `/campaigns/[id]` (DEV-86) también apuntan acá.

Usamos la estructura del reporte de **Plataforma Diez** como superset — es el más completo de los que Chirri produce. El de Yelmo/Ultracomb (First Rate Argentina) es un subconjunto con mucho menos detalle. Cualquier sección sin data no se renderiza — sin toggles manuales.

## Scope

Opción C del brainstorming: todas las secciones del reporte P10 real, 3 modelos nuevos + 2 agregaciones computadas, single mega ticket (el usuario trabaja solo).

**Explícitamente fuera del ticket:**
- Edición inline (se edita vía Django admin).
- Branding por cliente (DEV-53).
- Export PDF/Excel (DEV-54, DEV-60).
- Importer Excel (DEV-83) — el spec del importer va a consumir este schema.
- Integración AppsFlyer API (OneLink hoy = upload manual).
- Mobile responsive pixel-perfect (desktop-first, como el resto del portal).

## Arquitectura

```
GET /api/reports/<id>/
    → ReportDetailSerializer extendido (TopContent, OneLink, snapshots, Q1, YoY)
    → tenant-scoped en la view (request.user.client_id), 404 si ajeno o DRAFT

frontend/app/reports/[id]/page.tsx (server component)
    → apiFetch con JWT (patrón existente)
    → compone secciones, cada una decide render-or-null por data

frontend/app/reports/[id]/sections/*.tsx  (1 file por sección, ~80 líneas max)
frontend/app/reports/[id]/components/*.tsx (BarChartMini, KpiTile, etc)
```

**Principios clave:**
- Server components en todas las secciones (mismo patrón que `/home`, `/campaigns`).
- "Empty section = no section" — función helper `hasData(section)` decide si renderizar.
- Scoping en la view, nunca en middleware (gotcha CLAUDE.md).
- Un endpoint canónico por reporte. La computacion de rollups (Q1, YoY) vive en el serializer, no en el frontend.

## Modelo de datos

### Cambios a modelos existentes

**`Report`** — agregar `intro_text` (el P10 tiene una intro separada en page 2, diferente de las conclusiones al final):
```python
intro_text = models.TextField(blank=True, help_text="Intro textual al principio del reporte.")
```

### Modelos nuevos

**`TopContent`** — posts orgánicos e influencers destacados del mes.
```python
class TopContent(models.Model):
    class Kind(models.TextChoices):
        POST = "POST", "Post destacado"
        CREATOR = "CREATOR", "Creator destacado"

    report = models.ForeignKey(Report, on_delete=CASCADE, related_name="top_content")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    network = models.CharField(max_length=16, choices=ReportMetric.Network.choices)
    source_type = models.CharField(max_length=16, choices=ReportMetric.SourceType.choices)
    rank = models.PositiveIntegerField()  # 1, 2, 3... ordering dentro de (kind, network)
    handle = models.CharField(max_length=120, blank=True)  # @pasaje.en.mano, vacío si ORGANIC
    caption = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to="top_content/%Y/%m/", blank=True)
    post_url = models.URLField(blank=True)
    metrics = models.JSONField(default=dict)  # {likes, comments, shared, saved, views, reach, er, ...}

    class Meta:
        ordering = ["report", "kind", "network", "rank"]
        indexes = [models.Index(fields=["report", "kind"])]
```

Rationale JSON vs columnas: IG post, Reel, TikTok y X tienen métricas distintas y cambiantes. JSON es más flexible y evita migraciones a cada rato. El trade-off (queries no-indexables sobre metrics) no aplica porque nunca filtramos por métrica interna — solo leemos para render.

**`BrandFollowerSnapshot`** — serie temporal de followers por brand+network.
```python
class BrandFollowerSnapshot(models.Model):
    brand = models.ForeignKey("tenants.Brand", on_delete=CASCADE, related_name="follower_snapshots")
    network = models.CharField(max_length=16, choices=ReportMetric.Network.choices)
    as_of = models.DateField()
    followers_count = models.PositiveIntegerField()

    class Meta:
        unique_together = [("brand", "network", "as_of")]
        ordering = ["-as_of"]
```

Rationale: el mismo dato (Feb 2026 IG followers de Balanz) aparece en múltiples reportes (el reporte de Feb, el de Mar al comparar). Lo storeamos una vez, lo referenciamos en cada reporte agrupando snapshots del brand+network en el rango del reporte y el trimestre.

**`OneLinkAttribution`** — clicks y descargas por influencer para un reporte.
```python
class OneLinkAttribution(models.Model):
    report = models.ForeignKey(Report, on_delete=CASCADE, related_name="onelink")
    influencer_handle = models.CharField(max_length=120)
    clicks = models.PositiveIntegerField(default=0)
    app_downloads = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["report", "-app_downloads"]
```

### Agregaciones computadas (sin modelo)

**Q1 trimestral.** Computa en `ReportDetailSerializer.get_q1_rollup()`:
- Query: Reports del mismo `brand_id`, filter `period_start` dentro del trimestre del reporte actual (Jan-Mar / Apr-Jun / etc).
- Si hay menos de 2 reportes vecinos → devolver lo que hay (ej. solo [jan, feb]). El frontend renderiza si `length >= 2`.
- Shape:
  ```json
  {
    "months": ["enero", "febrero", "marzo"],
    "rows": [
      { "metric": "reach", "network": "INSTAGRAM", "values": [183340, 198109, 157514] },
      { "metric": "er",    "network": "INSTAGRAM", "values": [5.1, 4.9, 3.7] }
    ]
  }
  ```

**YoY (ER + reach vs año anterior).** Computa en `get_yoy()`:
- Busca el Report del mismo `brand_id` + network cuyo `period_start` sea 12 meses antes (tolerancia ±15 días).
- Si existe, devuelve `{network, metric, current, year_ago}` por combinación. Si no → `null`, la sección no renderiza.

**Follower snapshots agrupados.** Computa en `get_follower_snapshots()`:
- Query: `BrandFollowerSnapshot` para el brand del reporte, `as_of` entre `period_start - 90d` y `period_end`.
- Shape: `{ "INSTAGRAM": [{month:"feb", count:104568}, {month:"mar", count:107072}], "TIKTOK": [...], "X": [...] }`.
- Frontend renderiza la sección si algún network tiene `>= 2` puntos.

## API

**Nuevo endpoint:**
```
GET /api/reports/<int:id>/
    permissions.IsAuthenticated
    filter: status=PUBLISHED AND stage.campaign.brand.client_id == request.user.client_id
    not found (either condition) → 404 (no distinguimos para no filtrar existencia)
    response: ReportDetailSerializer
```

**`/api/reports/latest/` existente:** shape se extiende con los nuevos campos (son backwards-compatible al ser nullable/empty).

**Serializer extensión:**
```python
class TopContentSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()
    class Meta:
        model = TopContent
        fields = ("kind", "network", "source_type", "rank", "handle",
                  "caption", "thumbnail_url", "post_url", "metrics")
    def get_thumbnail_url(self, obj):
        return obj.thumbnail.url if obj.thumbnail else None

class OneLinkAttributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OneLinkAttribution
        fields = ("influencer_handle", "clicks", "app_downloads")

class ReportDetailSerializer(serializers.ModelSerializer):
    stage_name = serializers.CharField(source="stage.name", read_only=True)
    stage_id = serializers.IntegerField(source="stage.id", read_only=True)
    campaign_name = serializers.CharField(source="stage.campaign.name", read_only=True)
    campaign_id = serializers.IntegerField(source="stage.campaign.id", read_only=True)
    brand_name = serializers.CharField(source="stage.campaign.brand.name", read_only=True)
    display_title = serializers.CharField(read_only=True)
    metrics = ReportMetricSerializer(many=True, read_only=True)
    top_content = TopContentSerializer(many=True, read_only=True)
    onelink = OneLinkAttributionSerializer(many=True, read_only=True)
    follower_snapshots = serializers.SerializerMethodField()
    q1_rollup = serializers.SerializerMethodField()
    yoy = serializers.SerializerMethodField()
    ...
```

## Frontend: estructura de página

```
frontend/app/reports/[id]/
    page.tsx                    ← server component, orquesta
    sections/
        HeaderSection.tsx
        IntroText.tsx
        KpisSummary.tsx
        MonthlyCompare.tsx
        YoyComparison.tsx
        NetworkSection.tsx       ← parametrizada por network (IG/TikTok/X)
        BestContentChapter.tsx
        OneLinkTable.tsx
        FollowerGrowthSection.tsx
        Q1RollupTable.tsx
        ConclusionsSection.tsx
    components/
        BarChartMini.tsx         ← SVG/CSS, reusable para follower growth + Q1 bars
        KpiTile.tsx              ← métrica grande + delta
        MetricRow.tsx            ← comparativa lado-a-lado
        ContentCard.tsx          ← foto + handle + métricas (Top Content)
    lib/
        aggregations.ts          ← helpers para agrupar r.metrics por network/source_type
```

**Policy de tamaño:** cada sección y componente ≤ 100 líneas. Si excede, se partea. El `page.tsx` queda <50 líneas, puro orquestador. Principio P2 (SRP): una sección = un concepto visible. Principio P10 (simplicidad): composición sobre abstracción, sin HOCs ni render props especulativos.

**Design tokens & CSS:** usamos las CSS vars existentes (`--chirri-pink`, `--chirri-mint`, `--chirri-yellow`, etc) de `frontend/app/globals.css`. Cero hex hardcoded en los nuevos componentes. Cuando lande DEV-53 (branding por cliente), las mismas CSS vars se sobreescriben via layout wrapper — zero-cost migration.

**Accessibility (a11y):**
- HTML semántico: `<main>`, `<section>`, `<h1-h3>` en jerarquía correcta (`<h1>` = display_title, `<h2>` por sección, `<h3>` por subsección).
- Imágenes de TopContent: `alt` obligatorio derivado de `caption` o `handle`. Thumbnail sin caption → `alt="Post de @handle"`.
- Chart SVG (BarChartMini): `role="img"` + `aria-label` con la serie (ej. "Follower growth Instagram: febrero 104568, marzo 107072").
- Tablas (Q1 rollup, OneLink): `<table>` con `<thead>` + `<th scope="col|row">`.
- Colores no son el único signal para deltas (↑↓ + color, no solo color) — soporta daltonismo.
- Focus visible en cualquier `<a>` / `<button>` interactivo (ya viene del reset global).
- No hay interactividad custom (todo server-rendered) → no hay keyboard handlers extra por ahora.

**i18n:**
- El portal es español-only por decisión de producto (Chirri opera en AR/LATAM, todos los clientes en español). Todas las strings se escriben directamente en español en los componentes, sin wrapper i18n.
- Si aparece un cliente anglo en el futuro → ticket aparte para introducir `next-intl` y convertir strings.

**State management:** todo server-rendered, sin client state. Si aparece alguna interactividad (ej. toggle show-more) se resuelve con React local state (`useState`) dentro del componente, nunca global.

**Empty-state helper:**
```ts
// lib/has-data.ts
export function hasMetrics(report: ReportDto, network: Network): boolean {
  return report.metrics.some(m => m.network === network);
}
export function hasTopContent(report: ReportDto, kind: "POST"|"CREATOR"): boolean {
  return report.top_content.some(c => c.kind === kind);
}
// ... uno por sección
```

## Charts

**Decisión: SVG/CSS native.** Sin dependency nueva.

- **Follower growth:** barras verticales simples en SVG con labels encima. Input: `[{label:"feb", value:104568}, ...]`. Range 0→max * 1.1.
- **Q1 comparativa:** tabla (no chart) con 3 columnas Jan/Feb/Mar, filas por métrica, deltas con flechas ↑↓ y color.

Si más adelante pide insights dashboard complejo → agregamos Recharts.

## Storage & imágenes

**Setup django-storages + R2:**
```
pip install django-storages[s3]
```

**`backend/config/settings/base.py`:**
```python
USE_R2 = os.getenv("USE_R2", "0") == "1"

STORAGES = {
    "default": {"BACKEND": "storages.backends.s3.S3Storage"} if USE_R2 else {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

if USE_R2:
    AWS_S3_ACCESS_KEY_ID = os.environ["R2_ACCESS_KEY_ID"]
    AWS_S3_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
    AWS_S3_ENDPOINT_URL = os.environ["R2_ENDPOINT_URL"]
    AWS_STORAGE_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "chirri-media")
    AWS_S3_CUSTOM_DOMAIN = os.environ["R2_PUBLIC_URL"].replace("https://", "")
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False
```

**Dev:** `USE_R2` unset → local `backend/media/`, Docker bind-mount lo persiste, Django dev server sirve `/media/`.

**Prod:** `USE_R2=1` + 5 env vars → django-storages sube a R2, URLs públicas via `R2_PUBLIC_URL`.

**Bucket:** `chirri-media` nuevo (no mezclamos con `impactia-media` del sitio corporativo). `npx wrangler r2 bucket create chirri-media`.

**Tests:** `@override_settings(STORAGES={"default":{"BACKEND":"django.core.files.storage.InMemoryStorage"}})` para no tocar disco ni bucket.

**Seed_demo:** extender para crear TopContent con thumbnails de placeholder (comitteamos 3-4 JPGs chicos en `backend/apps/tenants/management/commands/fixtures/`).

## Seguridad y tenant scoping

**Principio aplicado:** P7 (Security by Default — validar todo input externo, permisos explícitos en cada endpoint).

- **Scoping en la view**, no en middleware (gotcha CLAUDE.md):
  ```python
  def get_object(self):
      return get_object_or_404(
          Report,
          pk=self.kwargs["pk"],
          status=Report.Status.PUBLISHED,
          stage__campaign__brand__client_id=self.request.user.client_id,
      )
  ```
- User de cliente A intenta ver reporte de cliente B → **404** (no 403 — no filtramos existencia).
- DRAFT invisible a cualquier user no-staff vía filter. Staff ve DRAFT desde admin.
- Thumbnails R2 públicas: OK porque el reporte al cual pertenecen ya está published y expuesto a un cliente específico. Si aparece sensibilidad → URLs firmadas en ticket futuro.

### Validación de boundaries

**Upload de imágenes (TopContent.thumbnail):**
- `TopContent` admin form valida: max 5 MB, mimetypes en `{image/jpeg, image/png, image/webp}`. Enforced via custom `validators=[FileSizeValidator(5*1024*1024), FileMimetypeValidator(...)]` en el field.
- Admin-only upload (usuarios no-staff no pueden subir nada — este ticket no expone upload a clientes).

**Input de API:**
- `GET /api/reports/<id>/` — solo path param `id:int`. DRF lo castea; `id` no-int → 404.
- No hay mutations en este ticket (todo write va por admin).

**Output de API:**
- DRF serializer define shape cerrado; campos nunca expuestos: `status` DRAFT (filtrado), credenciales, etc.
- JSONField `metrics` se serializa tal cual — se asume que admin valida formato al cargar (responsabilidad del admin form, no del serializer).

**Secretos & env vars:**
- Credenciales R2 solo vía env vars (`R2_*`). Nunca commiteadas. `.env.example` (ya existe en el repo) y `docs/ENV.md` (crear si no existe) listan las nuevas con owner = Daniel.
- Django `SECRET_KEY` sin cambios. `DEBUG=False` en prod (ya configurado).

**Dependency health:**
- `django-storages[s3]` es un paquete mantenido activamente (última release 2025, 5k+ stars, parte del ecosistema Django oficial). Auditoría: `pip-audit` o `safety check` en el setup del entorno.

## Observability

**Principio aplicado:** P9 (Fail Fast and Loud).

**Backend (Django):**
- Logger estructurado existente (`logging.getLogger(__name__)` por módulo) — reusar, no crear nuevo.
- Log al servir reporte: `logger.info("report_served", extra={"report_id", "client_id", "user_id"})` en el view después del 200.
- Log al rechazar por scoping: `logger.warning("report_access_denied", extra={"report_id", "user_id", "reason"})` antes del 404 — esto deja trazabilidad de intentos cross-tenant (potencial señal de bug o abuso).
- Errores no capturados → Django los loguea con traceback vía LOGGING config existente. Sin swallow, sin try/except silencioso.

**Frontend:**
- Patrón existente: `console.error("<event>", {context})` en server components ante fetch fail (ver `/campaigns/page.tsx` línea 22 como ejemplo). Reusar el mismo patrón en `/reports/[id]/page.tsx` si el fetch falla.
- No hay APM / Sentry configurado hoy — fuera de este ticket. Si lo hay, el log estructurado se consume automáticamente.

**Métricas de negocio:**
- No agregamos prometheus/custom metrics en este ticket. Si después aparece necesidad ("cuántos reportes vió el cliente X este mes") se agrega con un model log o via access logs Nginx.

**Health check:**
- `/api/health/` ya existe en el proyecto. No se modifica.

## Tests

### Unit (pytest)

- `test_reports_detail_view.py`:
  - 200 con reporte published del cliente del user, shape completo.
  - 404 con reporte de otro cliente.
  - 404 con reporte DRAFT (mismo cliente).
  - 404 con id inexistente.
  - Shape incluye top_content, onelink, follower_snapshots, q1_rollup, yoy.
- `test_report_detail_serializer.py`:
  - q1_rollup con 3 reportes vecinos → 3 valores.
  - q1_rollup con 1 reporte (el propio) → length 1 o null según criterio.
  - yoy con reporte 12 meses atrás (±15d) → dict populado.
  - yoy sin reporte 12m atrás → null.
  - follower_snapshots agrupados correctamente por network.
- `test_top_content_model.py`:
  - Upload de thumbnail vía admin form → archivo persistido en storage.
  - Unique ordering por (report, kind, network, rank).

### E2E (Playwright)

- Login como `belen.rizzo@balanz.com` → `/home` → click "Leer reporte" → `/reports/<id>`:
  - Ver display_title visible.
  - Ver al menos 1 KpiTile con número.
  - Ver al menos 1 ContentCard con handle.
  - No errores en consola.

### Seguridad

- Unit: request con JWT de user cliente A a `/api/reports/<id>/` de cliente B → 404.
- Unit: request sin auth → 401.

### Performance (smoke)

- `select_related` + `prefetch_related` en la view para evitar N+1 (metrics, top_content, onelink).
- Test con 20 top_content + 10 onelink → 1 query (+ select_related chain).

## Boundary / Edge cases

- **Reporte sin metrics** (vacío completo): render muestra título + conclusions, el resto colapsa.
- **ReportMetric con value=0**: se renderiza como "0", no como empty.
- **period_comparison=null**: no mostrar delta ↑/↓.
- **TopContent sin thumbnail**: render con placeholder gris, no crash.
- **OneLinkAttribution con app_downloads=0**: se muestra el row.
- **`follower_snapshots` con 1 punto**: sección no renderiza (un punto no es "growth").
- **Q1 rollup con 1 reporte**: sección no renderiza.
- **yoy partial (1 network tiene data, otro no)**: solo renderiza los que tienen.

## Dependencias

- `django-storages[s3]` nuevo en `backend/requirements.txt` (incluye `boto3`).
- Bucket R2 `chirri-media` creado + 5 env vars en prod (Hetzner docker-compose env).
- `seed_demo` extendido con fixtures de TopContent + OneLink + FollowerSnapshot.

## CI/CD & Deployment

El repo ya tiene el pipeline de 5 etapas (per CLAUDE.md: `test.yml` + `deploy.yml`). Este ticket requiere ajustes menores, no rearmado.

**Stage 1 — PR gate (test.yml):**
- Los nuevos tests pytest se auto-descubren (patrón `test_*.py`). Cero cambios en workflow.
- Los nuevos tests Playwright smoke (`reports.spec.ts`) corren como parte del job `e2e-smoke` existente.
- Lint (ruff + eslint) + typecheck (mypy si aplica + tsc) ya son required checks en branch protection.

**Stage 2 — Build:**
- Backend: imagen Docker se construye con `${{ github.sha }}` tag (ya es el patrón actual). Cero cambios.
- Frontend: Next build como parte del container image del frontend. Cero cambios.

**Stage 3 — Deploy (branch→env):**
- Push a `development` → deploy a Hetzner staging (`chirri.impactia.ai` si existe o equivalente — revisar DEV-77).
- Push a `main` → no deploy automático (solo `development` deploya). Merge a `development` cuando se quiere publicar.

**Stage 4 — Post-deploy smoke:**
- Revisar si `test.yml` corre Playwright smoke contra el deploy target. Si no, agregar step `playwright test --project smoke` con `PLAYWRIGHT_BASE_URL=${{ secrets.DEPLOY_URL }}` como required para merge a `development`.
- Mínimo: `/api/health/` responde 200 + `/login` renderiza.

**Stage 5 — Rollback:**
- Ya existe: `deploy.yml` despliega con `git pull` + `docker compose up -d --build`. Rollback = `git reset --hard <sha>` + redeploy. Documentado en README.
- Migrations: las migrations de este ticket son aditivas (nuevos modelos, nuevo field en Report). Rollback = `manage.py migrate reports <prev>`. No borra data existente.

**Secrets:**
- Nuevos: `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ENDPOINT_URL`, `R2_BUCKET_NAME`, `R2_PUBLIC_URL`, `USE_R2=1`.
- Agregar a GitHub `Secrets and variables → Actions` para el repo.
- Documentar en `docs/ENV.md` (crear si no existe) con owner = Daniel.
- También en `.env.example` sin valores reales.

**No `:latest` tags**, no smoke contra localhost, no secrets en logs.

## Git & Commit Strategy

**Branch model** (CLAUDE.md):
- Trabajo en feature branch desde `main` (ej. `feat/dev-52-report-viewer`).
- Commits atómicos, uno por concern. Convención: `feat:`, `test:`, `fix:`, `refactor:`, `docs:`, `chore:`.
- Merge a `main` cuando tests verdes. Fast-forward `development` cuando se quiere deploy.
- Nunca `--no-verify`, nunca skippear hooks.

**Commits esperados** (indicativo — el plan los desglosa):
1. `feat(reports): add TopContent, BrandFollowerSnapshot, OneLinkAttribution models`
2. `feat(reports): intro_text on Report + migration`
3. `chore(storage): wire django-storages with USE_R2 toggle`
4. `feat(api): GET /api/reports/<id>/ with tenant scoping`
5. `feat(api): extend ReportDetailSerializer with computed q1/yoy/snapshots`
6. `feat(seed): populate fixtures for TopContent, OneLink, FollowerSnapshot`
7. `feat(frontend): /reports/[id] page + section components`
8. `test(e2e): reports viewer smoke`
9. `docs: document R2 env vars and report viewer`

**Ownership:** Daniel solo por ahora. Single maintainer, no bus factor planning en este ticket.

## Impacto en otros tickets

- **DEV-51** (historial de reportes): queda cubierto parcialmente por `/home` + `/campaigns`; puede cerrarse o re-scopearse.
- **DEV-86** (Campaign detail): va a linkear acá — la ruta `/reports/<id>` queda lista para consumir.
- **DEV-83** (Importer fase 1): tiene que cargar TopContent + OneLink + BrandFollowerSnapshot desde el template Excel. Spec del importer referencia este schema.
- **DEV-54/60** (PDF/Excel export): renderiza esta página a PDF (Playwright headless) y dumpea el data model a Excel. Ningún cambio acá.
- **DEV-53** (Branding): cuando lande, los headers y acentos de esta página pasan a usar CSS vars del client en lugar de paleta Chirri.
- **DEV-78** (logo upload): reusa `django-storages` que configuramos acá.

## Policy de complejidad (resumen)

- Ningún nuevo archivo Python supera 200 líneas. Si se acerca → partear (ej. serializer en archivo propio si crece, `services/aggregations.py` si la lógica de Q1/YoY crece).
- Ningún componente React supera 100 líneas. Si crece → partear en subcomponentes.
- `page.tsx` < 50 líneas: puro orquestador, sin lógica.
- Principio P10 (simplicidad): la primera versión es la más simple que funcione, no la más extensible.

## Repo Hygiene

- Este spec y el plan que genere quedan en `docs/superpowers/specs/` y `docs/superpowers/plans/` respectivamente, marcados `Status: Done` cuando se merge a `main`.
- `README.md` actualizado con sección sobre env vars R2 y sobre `/reports/[id]` en el map de rutas.
- `docs/ENV.md` creado si no existe, con todas las env vars del proyecto (no solo R2) — de paso mejoramos onboarding.
- Sin archivos deprecados o TODOs escondidos en el código.

## DoD

**Data model:**
- [ ] 3 modelos nuevos (`TopContent`, `BrandFollowerSnapshot`, `OneLinkAttribution`) + migrations aplicadas.
- [ ] Campo `intro_text` en `Report` + migration.
- [ ] Admin Django registrado para los 3 modelos nuevos (con validators de imagen para `TopContent.thumbnail`).

**Backend API:**
- [ ] Endpoint `GET /api/reports/<id>/` con tenant scoping (view, no middleware).
- [ ] Extensión de `ReportDetailSerializer` con `top_content`, `onelink`, `follower_snapshots`, `q1_rollup`, `yoy`, `intro_text`.
- [ ] `select_related` + `prefetch_related` para evitar N+1.
- [ ] `/api/reports/latest/` sigue funcionando (backwards-compatible).

**Storage:**
- [ ] `django-storages[s3]` en `requirements.txt`.
- [ ] Config por env var (`USE_R2` toggle), local en dev, R2 en prod.
- [ ] Bucket R2 `chirri-media` creado.
- [ ] 6 env vars (`USE_R2`, `R2_*`) documentadas en `docs/ENV.md` y `.env.example`.
- [ ] Image upload valida size ≤ 5MB y mimetype.

**Frontend:**
- [ ] Página `app/reports/[id]/page.tsx` + secciones + componentes.
- [ ] Todas las secciones respetan "empty = no render".
- [ ] CSS vars existentes, cero hex hardcoded.
- [ ] Alt text en imágenes, ARIA en charts, HTML semántico.
- [ ] `page.tsx` < 50 líneas, secciones < 100, sin componente > 100.

**Seed:**
- [ ] `seed_demo` extendido con TopContent (3+ por red), OneLink (3+ rows), BrandFollowerSnapshot (3+ meses).
- [ ] 3-4 JPGs de placeholder commiteados en fixtures.

**Tests:**
- [ ] Unit: detail view (200/404 scoping, DRAFT invisible, scoping cross-tenant, 401 sin auth).
- [ ] Unit: serializer computed fields (q1 con 1/2/3 reportes, yoy con/sin reporte vecino, follower_snapshots agrupados).
- [ ] Unit: TopContent image upload validators.
- [ ] Unit: N+1 test (1 query para reporte con 20 top_content + 10 onelink).
- [ ] E2E smoke: login → /home → click → /reports/<id>, ver título + KPI + ContentCard, sin errores en consola.

**Observability:**
- [ ] Log estructurado en el view (servido + access denied).
- [ ] `console.error("reports_fetch_failed", ...)` en el server component ante fetch fail.

**CI/CD:**
- [ ] Tests nuevos corren en `test.yml` (auto-descubiertos).
- [ ] Secrets R2 agregados a GitHub Actions.
- [ ] `docs/ENV.md` + `.env.example` actualizados.
- [ ] Post-deploy smoke revisa que `/reports/<id>` responde 200 con un reporte demo (opcional en este ticket si `test.yml` no lo corre).

**Docs:**
- [ ] README con sección de env vars R2 y mapa de rutas del portal.
- [ ] Spec (`2026-04-20-report-viewer-design.md`) marcado `Status: Done` al mergear.
- [ ] Plan (`2026-04-20-report-viewer.md`) archivado al mergear.

## Referencias

- `docs/superpowers/specs/2026-04-18-chirri-portal-foundation-design.md` — modelo tenancy.
- `docs/superpowers/specs/2026-04-20-campaigns-list-design.md` — patrón server component.
- `Documents/Reporte P10 Mar 26 (2).pdf` — estructura objetivo completa.
- `Documents/UC MARZO.pdf` — estructura simplificada (Yelmo/Ultracomb).
- `CLAUDE.md` — gotchas (tenant scoping en view, Windows+Docker middleware hot-reload).
