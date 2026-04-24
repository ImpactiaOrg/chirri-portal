# DEV-129 — Split TopContentBlock → TopContentsBlock + TopCreatorsBlock

**Goal:** Reemplazar el block único `TopContentBlock` (con `kind` discriminator y `TopContent.metrics: JSONField`) por dos blocks tipados separados con métricas como columnas reales.

**Ticket:** [DEV-129](https://linear.app/impactia/issue/DEV-129)

**Branch:** directo a `main` (working branch único mientras no haya Hetzner; ver `CLAUDE.md`).

**Approach:** refactor chico, same-session. Nada en prod → migración destructiva + re-seed (mismo approach que DEV-116).

**Decisión de diseño (2026-04-24):** considerado alternativa de `TopBlock` único + items polimórficos — descartado porque el layout del container es del block (no del item) y el modelo polimórfico permitiría blocks con items mixtos como estado inválido. Si mañana aparece un caso real de "block que mezcla tipos", se refactorea entonces.

---

## Modelos

**`TopContentsBlock(ReportBlock)`** — posts/contenidos destacados:
- `title: CharField` (default "Top contenidos")
- `network: Network`
- `period_label: CharField(blank)` — ej. "febrero"
- `limit: PositiveSmallIntegerField` (default 6)

**`TopContentItem`** (FK reverso `related_name="items"`):
- `block FK`, `order: PositiveIntegerField`
- `thumbnail: ImageField`
- `caption: TextField(blank)`
- `post_url: URLField(blank)`
- `source_type: SourceType` (ORGANIC|INFLUENCER|ADS)
- Métricas: `views`, `likes`, `comments`, `shares`, `saves` (todos `PositiveIntegerField(null=True, blank=True)`)

**`TopCreatorsBlock(ReportBlock)`** — creators destacados:
- `title: CharField` (default "Top creadores")
- `network`, `period_label`, `limit`

**`TopCreatorItem`** (FK reverso):
- `block FK`, `order`
- `thumbnail: ImageField`
- `handle: CharField(max_length=120)` — **required**
- `post_url: URLField(blank)`
- Métricas: `views`, `likes`, `comments`, `shares` (sin saves)

---

## Layout del viewer

Cada block renderea sus items como grid responsive (`grid-template-columns: repeat(auto-fill, minmax(N, 1fr))`). Funciona para 1 item (cajita sola), 2, 3, 5 items — el grid adapta. No hay asunción de "5 fijos" ni "1 fijo centered".

---

## Checklist

### Backend — modelos + migración
- [ ] Crear `backend/apps/reports/models/blocks/top_contents.py` con `TopContentsBlock` + `TopContentItem`.
- [ ] Crear `backend/apps/reports/models/blocks/top_creators.py` con `TopCreatorsBlock` + `TopCreatorItem`.
- [ ] Borrar `backend/apps/reports/models/blocks/top_content.py`.
- [ ] Actualizar `backend/apps/reports/models/__init__.py` (remover `TopContentBlock`, `TopContent`; agregar los 4 nuevos).
- [ ] Remover `TopContent` de `models_legacy.py` si ya no se usa.
- [ ] Migración `0014_split_top_content_blocks.py`: drop `TopContentBlock` y `TopContent`; create las 4 tablas nuevas. Destructiva.

### Backend — admin
- [ ] En `backend/apps/reports/admin.py`:
  - Remover `TopContentBlockAdmin`, `TopContentAdmin`, `TopContentInline`.
  - Agregar `TopContentItemInline` (SortableTabularInline por `order`) + `TopContentsBlockAdmin`.
  - Agregar `TopCreatorItemInline` + `TopCreatorsBlockAdmin`.
  - En `ReportBlockInline.child_inlines`: reemplazar `TopContentBlockInline` por los dos nuevos.
  - En `ReportBlockAdmin.child_models`: mismo swap.

### Backend — serializers
- [ ] En `backend/apps/reports/serializers.py`:
  - Remover `TopContentItemSerializer` (viejo), `TopContentBlockSerializer`.
  - Agregar `TopContentItemSerializer` (nuevo: 5 métricas + caption + thumbnail_url) y `TopContentsBlockSerializer` (type="TopContentsBlock").
  - Agregar `TopCreatorItemSerializer` (4 métricas + handle + thumbnail_url) y `TopCreatorsBlockSerializer` (type="TopCreatorsBlock").
  - Actualizar `_BLOCK_SERIALIZERS` dict.

### Frontend — DTOs + renderers
- [ ] `frontend/lib/api.ts`:
  - Remover `TopContentItemDto`, `TopContentDto` (alias), `TopContentBlockDto`.
  - Agregar `TopContentItemDto` (con caption/source_type/views/likes/comments/shares/saves).
  - Agregar `TopCreatorItemDto` (con handle/views/likes/comments/shares).
  - Agregar `TopContentsBlockDto` (type="TopContentsBlock") y `TopCreatorsBlockDto` (type="TopCreatorsBlock").
  - Union `ReportBlockDto`: swap.
- [ ] `frontend/lib/has-data.ts`: guards nuevos por tipo.
- [ ] Crear `frontend/app/reports/[id]/blocks/TopContentsBlock.tsx` — grid responsive, cajitas con 5 métricas (incluye guardados).
- [ ] Crear `frontend/app/reports/[id]/blocks/TopCreatorsBlock.tsx` — grid responsive, cajitas con @handle + 4 métricas.
- [ ] Borrar `frontend/app/reports/[id]/blocks/TopContentBlock.tsx`.
- [ ] `BlockRenderer.tsx`: swap case "TopContentBlock" por los dos nuevos.
- [ ] Partir `frontend/app/reports/[id]/components/ContentCard.tsx` en `ContentItemCard.tsx` + `CreatorItemCard.tsx` (sin iterar `Object.entries(metrics)`).

### Seed — ⚠️ no olvidar
- [ ] `backend/apps/tenants/management/commands/seed_demo.py` — `_seed_report_viewer_fixtures`:
  - Reemplazar el loop de `top_content_specs` por **dos creaciones separadas**: un `TopContentsBlock` con N items (3-5, variable por reporte) con `_pick_image("post")` + métricas realistas incluyendo `saves` + captions; y un `TopCreatorsBlock` con M items (1-3) con `_pick_image("creator")` + `handle` + métricas sin `saves`.
- [ ] Revisar `_seed_full_layout` y `_seed_full_layout_abril` — referencias a `TopContentBlock` → swap a los dos nuevos.

### Tests
- [ ] Borrar `backend/tests/unit/blocks/test_top_content_block.py`, `test_topcontent_block_fk.py`.
- [ ] Crear `backend/tests/unit/blocks/test_top_contents_block.py` — create, serializer output, métricas tipadas con `saves`.
- [ ] Crear `backend/tests/unit/blocks/test_top_creators_block.py` — create, serializer output, `handle` required, sin `saves`.
- [ ] Actualizar `frontend/tests/e2e/report-blocks.spec.ts` si hay assertions específicas del block type viejo.

---

## Verificación final

```bash
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_demo
docker compose exec backend pytest backend/tests/unit -q
cd frontend && npm run typecheck && npm run test:e2e:smoke
```

**Criterio de éxito:** seed corre limpio; el reporte demo muestra ambos bloques con layout correcto independiente del count de items (1, 2, 3, 5…); E2E smoke verde.
