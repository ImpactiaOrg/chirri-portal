# Chirri Portal — Foundation Design

**Fecha:** 2026-04-18
**Estado:** En brainstorming — decisiones iniciales cerradas, spec pendiente de review
**Tickets Linear relacionados:** DEV-47, DEV-48, DEV-49, DEV-50, DEV-51, DEV-52, DEV-53, DEV-56, DEV-65

Este documento captura las decisiones de stack, arquitectura y modelo de datos del portal Chirri tomadas antes de escribir código. Lo complementa `Documents/design-prompt.md` (brief visual) y `Documents/design-prompt-addendum-data-model.md` (implicancias de UI del modelo de datos).

## Decisión 1 — Tech stack

**Elegido:** Django 5 + DRF (backend) + Next.js App Router (frontend).

**Alternativa descartada:** Django + HTMX + Alpine.js (estilo Siga).

**Por qué:**
- El portal va a incluir un editor de templates de reportes vía prompting — preview en vivo, state cliente rica, streaming de LLM. Es caso arquetípico donde React/Next.js gana.
- Posibilidad futura de app mobile nativa (RN puede compartir lógica pura y tipos con Next.js).
- El contexto de Impactia (`Git/CLAUDE.md`) explícitamente permite ambos stacks ("Next.js o HTMX+Alpine depending on the product").

**Costo aceptado:** dos apps en vez de una (más deploy, más piezas vs. el patrón de Siga).

## Decisión 2 — Repositorio

**Elegido:** monorepo con `/backend` (Django) y `/frontend` (Next.js). Un solo dev, un solo PR por feature cruza todo el stack. Cambiar a dos repos si escala el equipo.

## Decisión 3 — Infraestructura

Idéntico a Siga:

- Postgres 15 + Redis + Celery (jobs pesados, integraciones con APIs externas)
- Docker Compose (dev y prod separados)
- Nginx al frente
- Deploy a Hetzner vía GitHub Actions sobre push a `development`
- `entrypoint.sh` corre migraciones y seeds automáticamente en cada boot
- `.env` (dev) / `.env.prod` (prod)
- Auth: JWT para DRF, session/httpOnly cookie en Next.js

Integraciones LLM vía `arc-sdk` (plataforma interna Impactia), no llamadas directas a providers.

## Decisión 4 — Modelo de datos multi-tenant

Jerarquía:

```
Client (tenant, el que logea)
 └─ Brand (1..N, si hay 1 la UI la auto-selecciona)
     └─ Campaign (1..N, status: ACTIVE / FINISHED / PAUSED)
         ├─ Stage (1..N, si hay 1 la UI colapsa el concepto)
         │   └─ Report (1..N, period: MONTH / QUARTER / CUSTOM / FINAL)
         └─ NarrativeLine (0..N, transversal a las etapas)
```

Entidades satélite:

- `Influencer` (global) ↔ `CampaignInfluencer` (through: narrative_line, stage, status MUST/ALT, fee, flags de contenido/pauta).
- `ScheduledPost` (cronograma IG/TikTok) → FK a `Brand` + FKs opcionales a `Campaign`, `Stage`, `CampaignInfluencer`.
- `ReportMetric` → por `(report, network, source_type)` con `source_type ∈ {organic, influencer, paid}`.

**Convención "Operación continua":** toda Brand tiene al menos una Campaign. Si la marca no tiene campaña estructurada (caso Plataforma Diez), el seed crea una Campaign "Operación continua" con una única Stage "Ongoing". Los reportes mensuales cuelgan ahí. En la UI, esta jerarquía se colapsa: el cliente ve solo su historial de reportes, sin las palabras "campaña" ni "etapa".

**Tenant scoping:** middleware/mixin filtra automáticamente todas las queries por `brand__client=request.user.client`. Patrón copiado de Siga.

**Separación orgánico vs pauta vs influencer** es un campo de primera clase en `ReportMetric` (no derivado, no opcional). Es el principal valor agregado del portal vs exportar Metricool raw.

## Decisión 5 — Django Admin como panel interno

El equipo Chirri (Vicky, Julián, Tati) no tiene UI custom para cargar datos — usan Django Admin, con inlines y acciones custom para:

- Alta de clientes, marcas, usuarios
- Carga de influencers y asignación a campañas
- Creación y publicación de reportes (draft → published)
- Carga de posts programados (cronograma IG)

DEV-56 cubre esto. La UI del portal es para el cliente, no para el equipo.

## Entidades — detalle de campos

### `Client`
- name, logo (URL en Cloudflare R2), primary_color, secondary_color

### `ClientUser`
- client (FK), email, password, role (ej: VIEWER, ADMIN_CLIENT)
- scoped: solo ve data de su Client

### `Brand`
- client (FK), name, logo, description

### `Campaign`
- brand (FK), name, mother_concept, tagline, objective
- brief (TextField): descripción narrativa corta para el header del portal (ej: "Acompañar al ahorrista argentino en su viaje a inversor. 4 actos: Awareness, Educación, Validación, Conversión.")
- start_date, end_date, status
- `is_single_stage` derivado de `stages.count() == 1` (no se persiste)

### `Stage`
- campaign (FK), order, kind (AWARENESS/EDUCATION/VALIDATION/CONVERSION/ONGOING/OTHER)
- name (editable), description, start_date, end_date

### `NarrativeLine`
- campaign (FK), name, description, tone

### `Report`
- stage (FK)
- kind: Choices(INFLUENCER, GENERAL, QUINCENAL, MENSUAL, CIERRE_ETAPA) — tipo del reporte. Se muestra como tag en el header del reporte.
- period_start, period_end — rango de fechas que cubre el reporte (obligatorio, para cualquier kind)
- title (opcional, se auto-genera a partir de kind + period si no se provee)
- status (DRAFT/PUBLISHED), published_at
- conclusions_text (texto libre del equipo Chirri)

### `ReportMetric`
- report (FK), network (IG/TIKTOK/X), source_type (ORGANIC/INFLUENCER/PAID)
- metric_name (reach, impressions, er, followers_gained, etc.), value (decimal)
- period_comparison (delta vs mes/Q anterior, opcional)

### `Influencer`
- handle_ig, handle_tiktok, handle_x, link_ig, link_tiktok
- followers_ig, followers_tiktok, size_tier (NANO/MICRO/MACRO/MEGA)
- er_ig, er_tiktok, engagement_level
- niche, main_audience, age_range, gender, top_format, comm_style, ideal_campaign_type

### `CampaignInfluencer`
- campaign (FK), influencer (FK)
- narrative_line (FK nullable), stage (FK nullable)
- status (MUST/ALTERNATIVE/NEGOTIATE_FEE/DISCARDED)
- fee_ars, cost_per_engagement, includes_content, includes_paid_boost
- previous_collabs, notes

### `ScheduledPost`
- brand (FK), campaign (FK nullable), stage (FK nullable), campaign_influencer (FK nullable)
- scheduled_for (datetime), caption, image (URL en R2)
- status (DRAFT/APPROVED/PUBLISHED)
- network (IG para el prototipo; TikTok/X en fases siguientes)

## Decisión 6 — Qué absorber del diseño (v2, 2026-04-18)

El usuario revisó el handoff de Claude Design (`design/handoff/chirri-portal/`) y decidió:

- **Absorber al modelo ahora:**
  - `Campaign.brief` (descripción narrativa)
  - `Report.kind` con enum `{INFLUENCER, GENERAL, QUINCENAL, MENSUAL, CIERRE_ETAPA}` + `period_start`/`period_end` obligatorios
- **No absorber al modelo** (quedan en el front como datos derivados o mock; se reevalúan más adelante):
  - `Report.author` / `ChirriUser` — se posterga
  - `Stage.lead`, `Stage.color` derivado
  - `Campaign.hero_color`, `totalReach`/`pieces`/`influencers` agregados
  - `CampaignInfluencer.caption`/`notes`/`posts_count`/`cpm`
  - `Pipeline` (influencers en propuesta/próximo mes)
  - Fee en USD vs ARS — se deja en ARS por ahora

La seed con datos simulados (DEV-49) queda postergada: el usuario cargará datos directamente vía Django Admin sobre la base real.

## Scope del prototipo (label "Prototype" en Linear)

Tickets que entran en la primera iteración ("cimientos del MVP real"):

- **DEV-47** — Scaffolding monorepo Django + Next.js + Docker Compose + CI/CD a Hetzner
- **DEV-48** — Migraciones con todas las entidades del spec
- **DEV-50** — Auth JWT + session cookie, multi-tenant scoping
- **DEV-53** — Branding por cliente (logo + colores desde `Client`, aplicados en el frontend)
- **DEV-56** — Django Admin configurado para el equipo Chirri

Luego, con cimientos listos, se empiezan las pantallas contra backend real:

- **DEV-51** — Home del cliente
- **DEV-52** — Detalle de reporte
- **DEV-54** — Descarga PDF
- **DEV-65** — Cronograma IG (ya marcado "soon" en el diseño)

**Fuera del scope de cimientos:**

- **DEV-49** (seed con datos simulados) queda postergado — el usuario cargará data real vía Django Admin.

## Fuera de scope del prototipo (se difieren a MVP o "Someday")

- Integración real con Metricool (DEV-55)
- Ingesta IG/TikTok/X (DEV-59)
- Email al publicar (DEV-57)
- Export Excel (DEV-60)
- Admin custom más allá de Django Admin (DEV-56 queda cubierto por admin, sin UI propia)
- OKRs (DEV-61), Dashboard interno (DEV-62), Insights con IA (DEV-63), Asistente de calendario (DEV-64)

## Decisiones abiertas (para cerrar antes de tocar código)

1. **Nombre del repo GitHub** → Sugerido: `ImpactiaOrg/chirri-portal` (consistente con DEV-47).
3. **Dominio de prod** → A definir. Sugerido: `chirri.impactia.ai` o similar.
4. **Editor de templates de reportes vía prompting** → decisión tomada en brainstorming pero sin ticket Linear. Falta crear ticket y spec separado. Es el driver principal de la decisión de stack pero no entra en el prototipo.
5. **Dónde guardar logos/miniaturas** → Cloudflare R2 (`impactia-media` bucket), convención heredada de Impactia.

## Next step

El plan de implementación queda en pausa por pedido del usuario. Cuando se retome, invocar `superpowers:writing-plans` para producir el plan paso a paso del prototipo (scaffolding → data model → auth → admin → home → detalle → cronograma → deploy).
