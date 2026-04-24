# DEV-130 — ImageBlock (solo imagen + overlay opcional)

**Goal:** Agregar un nuevo block `ImageBlock` para renderear imágenes full-width con título/caption en overlay opcional.

**Ticket:** [DEV-130](https://linear.app/impactia/issue/DEV-130)

**Branch:** directo a `main` (working branch único; ver `CLAUDE.md`).

**Approach:** refactor chico, same-session. Migración aditiva (no toca data existente).

---

## Modelo

```python
class ImageBlock(ReportBlock):
    image         = ImageField(upload_to="image_blocks/%Y/%m/",
                               validators=[validate_image_size, validate_image_mimetype])
    image_alt     = CharField(max_length=200, blank=True)
    title         = CharField(max_length=200, blank=True)
    caption       = TextField(blank=True)
    overlay_position = CharField(choices=[
        ("top", "Arriba"),
        ("bottom", "Abajo"),
        ("center", "Centrado"),
        ("none", "Sin overlay"),
    ], default="bottom")
```

No hay tabla hija — es un block "hoja".

---

## Checklist

### Backend — modelo + migración
- [ ] Crear `backend/apps/reports/models/blocks/image.py` con `ImageBlock`.
- [ ] Exportar en `backend/apps/reports/models/__init__.py`.
- [ ] `makemigrations` → `0015_imageblock.py` (aditiva, no destructiva).

### Backend — admin
- [ ] En `backend/apps/reports/admin.py`:
  - Agregar `ImageBlockAdmin(_BlockChildAdminBase)` sin inlines.
  - Agregar `ImageBlockInline(StackedPolymorphicInline.Child)` en `ReportBlockInline.child_inlines`.
  - Agregar `ImageBlock` en `ReportBlockAdmin.child_models`.

### Backend — serializer
- [ ] `ImageBlockSerializer` con fields `(type, image_url, image_alt, title, caption, overlay_position)` y `get_image_url` + `get_type="ImageBlock"`.
- [ ] Agregar al dict `_BLOCK_SERIALIZERS`.

### Frontend — DTO + renderer
- [ ] `frontend/lib/api.ts`: `ImageBlockDto` en la union `ReportBlockDto`.
- [ ] Crear `frontend/app/reports/[id]/blocks/ImageBlock.tsx` que renderea la imagen y, según `overlay_position`, un `<div>` absoluto con título+caption (top / bottom / center) o nada.
- [ ] `BlockRenderer.tsx`: case "ImageBlock".

### Seed
- [ ] Agregar `ImageBlock` al `_seed_full_layout_abril` (e.g. como block de cierre visual): usar `_pick_image("post")` para la imagen, con `title="Mes en fotos"` y `caption` corto.

### Tests
- [ ] `backend/tests/unit/blocks/test_image_block.py` — create con image, serializer shape, overlay choices.
- [ ] `frontend/tests/report-blocks.spec.ts`: pill o screenshot verifying el nuevo block en el report demo.

---

## Verificación final

```bash
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_demo --wipe
docker compose exec backend pytest tests/unit -q
cd frontend && npm run typecheck
```

**Criterio:** seed corre, admin permite crear ImageBlock, viewer lo renderea con overlay en las 4 posiciones.
