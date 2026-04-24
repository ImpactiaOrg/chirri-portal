---
name: import-report-from-pdf
description: Convert a legacy Chirri report (PDF/PPTX) into a ZIP bundle (xlsx + images/) ready to upload via the Django admin importer (DEV-83). Use when the user points at a PDF in `Documents/Reportes Ejemplo/...` and asks to import it, build an xlsx from it, or generate the bundle.
---

# Importar un reporte legacy desde PDF

Este skill convierte un PDF (típicamente de Google Slides exportado) al formato de import del portal: `reporte.xlsx` + carpeta `images/` + `reporte.zip`. El output va a `Documents/Old Reports Import/<Brand> - <Mes Año>/`.

## Contrato de salida

```
Documents/Old Reports Import/<Brand> - <Mes Año>/
├── reporte.xlsx          # 10 hojas, mismo formato que dump_report_template
├── images/               # solo las imágenes referenciadas por el xlsx
│   └── *.jpg|.png|.webp
└── reporte.zip           # los dos de arriba, listos para el admin
```

El ZIP tiene que validar con `python manage.py validate_import /tmp/<zip>` antes de entregárselo al usuario.

## Flujo obligatorio

### 1. Extraer texto e imágenes del PDF

Usar `pypdf` dentro del container backend. Copiar el PDF primero:

```bash
docker compose cp "<pdf-path>" backend:/tmp/src.pdf
MSYS_NO_PATHCONV=1 docker compose exec -T backend python -c "
from pypdf import PdfReader
from pathlib import Path
r = PdfReader('/tmp/src.pdf')
for i, p in enumerate(r.pages, 1):
    print(f'--- Page {i} ---')
    print((p.extract_text() or '')[:3000])
out = Path('/tmp/src_images'); out.mkdir(exist_ok=True)
count = 0
for pno, page in enumerate(r.pages, 1):
    for img in page.images:
        count += 1
        data = img.data
        ext = '.png' if data[:8].startswith(b'\x89PNG') else '.jpg'
        (out / f'page{pno:02d}_img{count:02d}{ext}').write_bytes(data)
print(f'{count} images extracted')
"
```

Si `pypdf` no está instalado en el container, correr `docker compose exec backend pip install pypdf` primero.

### 2. Decidir qué imágenes conservar

**NO copiar todo a ciegas.** Un PDF suele tener decoraciones de fondo, logos, separadores. Miralas (tamaño, página de origen) y elegí solo las que sean contenido real:

- Thumbnails de posts destacados → referenciados desde `TopContents` / `TopCreators`.
- Renders de tablas/gráficos que NO podemos reconstruir con `ChartBlock` o `MetricsTableBlock` → van a un `TextImageBlock` con la imagen + texto descriptivo al costado.
- Imágenes ilustrativas del mes → opcionalmente un `ImageBlock` full-width.

Renombralas descriptivamente en el destino (`best_organic_post.png`, `utm_performance_table.png`, etc.), no dejes `page13_img11.png`.

### 3. Decidir: ¿reconstruir como block tipado o `TextImage` con screenshot?

Esta es la decisión clave del skill. Regla:

| Sección del PDF | Decisión |
|---|---|
| Lista de métricas simples (likes, comments, shares, reach) | `MetricsTableBlock` o `KpiGridBlock` — reconstruí con valores |
| Chart simple (bar/line) de pocos puntos, con labels claros | `ChartBlock` — extraé los datos |
| Tabla compleja renderizada como imagen (ej. UTM performance de GA4 con muchas columnas raras) | **`TextImageBlock` con la imagen como screenshot** + texto descriptivo al costado |
| Collage / layout visual custom que no podemos reproducir | `TextImageBlock` o `ImageBlock` con la imagen renderizada |
| Post destacado / creator destacado | `TopContentsBlock` + `TopCreatorItem` con la thumbnail real |

**Anti-patrón a evitar**: narrativizar una tabla compleja como texto plano cuando el original tiene valor visual. Si la tabla del PDF ya es una imagen, extraéla y usála como imagen. No pierdas señal convirtiendo a prosa.

### 4. Armar el xlsx

Generá el xlsx programáticamente usando el skeleton del writer. Dejá el script one-off en `tmp/build_<slug>.py`, copialo a `/app/` del container y corrélo. Ver `tmp/build_p10_april.py` como template:

```python
from apps.reports.importers import schema as s
from apps.reports.importers.excel_writer import build_skeleton, to_bytes

wb = build_skeleton()
# ... llenar cada hoja con ws.cell(row=R, column=C, value=X)
Path(out).write_bytes(to_bytes(wb).getvalue())
```

**Reglas del template** (más detalle en la hoja `Instrucciones` del template vacío):

- Hoja `Reporte`: KV en columna B filas 2-7 (tipo, fecha_inicio, fecha_fin, titulo, intro, conclusiones) + Layout (orden, nombre) debajo del header `# Layout`.
- `nombre` único cross-sheet, regex `[a-z0-9_-]{1,60}`.
- Hojas denormalizadas (Kpis, MetricsTables, TopContents, TopCreators, Attribution, Charts): parent fields (`block_title`, `block_network`, etc.) se repiten en cada row del item. Agrupación por `nombre`.
- Enums en español: `tipo` ∈ {Influencer, General, Quincenal, Mensual, Cierre de etapa}; `block_network` ∈ {Instagram, TikTok, X, ""}; `source_type` ∈ {Orgánico, Influencer, Pauta, ""}.
- `image_position` ∈ {left, right, top}; `chart_type` ∈ {bar, line}; `block_show_total` ∈ {TRUE, FALSE}.
- Fechas `DD/MM/YYYY`. Decimales con `.`.

Conclusions del PDF van al **field `conclusiones` del Report** (hoja `Reporte`), no a un block.

### 5. Copiar el xlsx al destino y armar el ZIP

```bash
docker compose cp backend:/tmp/out.xlsx "Documents/Old Reports Import/<Brand> - <Mes>/reporte.xlsx"
cd "Documents/Old Reports Import/<Brand> - <Mes>"
rm -f reporte.zip
python -c "
import zipfile, os
with zipfile.ZipFile('reporte.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.write('reporte.xlsx', 'reporte.xlsx')
    for name in sorted(os.listdir('images')):
        zf.write(os.path.join('images', name), f'images/{name}')
"
```

### 6. Validar

**Obligatorio antes de entregar**:

```bash
cp "Documents/Old Reports Import/<Brand> - <Mes>/reporte.zip" tmp/out.zip
MSYS_NO_PATHCONV=1 docker compose cp tmp/out.zip backend:/tmp/out.zip
MSYS_NO_PATHCONV=1 docker compose exec -T backend bash -c "cd /app && python manage.py validate_import /tmp/out.zip"
```

Tiene que imprimir `✓ ... es válido`. Si falla, corregí hasta que valide — no entregues un bundle roto.

## Entregable final (mensaje al usuario)

1. Path del folder: `Documents/Old Reports Import/<Brand> - <Mes Año>/`
2. Lista de blocks generados (nombre, tipo, descripción breve).
3. **Caveats explícitos**: datos que inferiste, interpolaste, o que no pudiste mapear 1:1. El usuario tiene que saber qué retocar si quiere 100% fidelidad.
4. Instrucción final: "eliminá el Report si ya importaste uno anterior, subí el `reporte.zip` desde el admin (Cliente → Brand → Campaña → Etapa → file)".

## Anti-patrones a evitar

- ❌ Narrativizar tablas complejas como prosa cuando el original es visual → extraer la imagen y usar `TextImageBlock`.
- ❌ Copiar todas las imágenes extraídas del PDF al bundle → elegir solo las que son contenido real, renombrarlas con nombres descriptivos.
- ❌ Entregar sin validar con `validate_import` → siempre correrlo antes de decirle al usuario que está listo.
- ❌ Inventar datos que no están en el PDF → si el PDF muestra "Marzo 79821" y "Abril 79821" (datos ambiguos), marcar como caveat y dejar valores razonables interpolados, NO inventar picos/caídas artificiales.
- ❌ Scripts one-off en el repo sin prefijo `tmp/` → `tmp/` está gitignored.
- ❌ Usar `ChartBlock` forzado para charts de layout custom (polaroid, collage) que el viewer no puede reproducir → preferir `TextImageBlock` con la imagen renderizada.
