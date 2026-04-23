# Deploy Notes

Notas sobre deploys significativos o migraciones destructivas. Se actualiza al momento del merge, no al del push.

## 2026-04-23 — DEV-116 typed blocks refactor

### Migraciones incluidas

| # | Archivo | Destructiva | Notas |
|---|---|---|---|
| 0009 | `typed_blocks` | Parcial | Agrega columnas `polymorphic_ctype`, `instructions`, `created_at`, `updated_at`. State-remueve `ReportBlock.type/config/image` + DROP NOT NULL a nivel DB. Crea tabla `TextImageBlock`. |
| 0010 | `add_remaining_block_subtypes` | No | Crea las 5 subtype tables restantes (`KpiGridBlock`, `MetricsTableBlock`, `TopContentBlock`, `AttributionTableBlock`, `ChartBlock`) + child tables (`KpiTile`, `MetricsTableRow`, `ChartDataPoint`). |
| 0011 | `drop_legacy_and_migrate_fks` | **Sí** | DROP tabla `ReportMetric`. DROP columns `type/config/image` de `ReportBlock`. Rewire `TopContent.block` FK → `TopContentBlock`, drop `TopContent.report`. Rewire `OneLinkAttribution.attribution_block` FK, drop `OneLinkAttribution.report`. |

### Pre-deploy checklist

- [x] No production data at time of merge (confirmado 2026-04-23 — piloto Balanz todavía no lanzado).
- [x] Staging deploy (`development` branch → Hetzner vía `deploy.yml`) verificable.
- [ ] Post-deploy: verificar en logs de Hetzner:
  - `reports.migrations: typed_blocks_scaffold_applied` (0009 OK)
  - `reports.migrations: typed_blocks_destructive_migration_applied` (0011 OK)
- [ ] Post-deploy smoke manual:
  - Login con Balanz demo (`belen.rizzo@balanz.com` / `balanz2026`).
  - Abrir Educación Marzo General report → 11 bloques rendereando (KPI grid + 4 metrics tables + 2 top content + 1 attribution + 3 charts).
  - Ejecutar `python manage.py seed_demo` en el container de prod una vez — debe correr sin errores.

### Rollback procedure

Migraciones 0009 y 0010 son reversibles (`manage.py migrate reports 0008`). Migración **0011 NO es reversible** — su reverse `_warn_rollback_unsafe` levanta `RuntimeError` explícitamente porque la data dropped (ReportMetric, config JSON de blocks) no se puede restaurar sin backup.

#### Si falla post-deploy antes de 0011

Si la migración falla entre 0008 y 0010, revertir:

```bash
# En el container de Hetzner:
python manage.py migrate reports 0008
git reset --hard <sha_previo>
docker compose restart backend
```

#### Si falla post-deploy después de 0011

Data loss ya ocurrió. Opciones:

1. **Restore desde backup de Postgres**. Requiere acceso al backup del momento pre-deploy. Coordinar con infra.
2. **Re-run `seed_demo`**. Si el ambiente es staging/dev, esto regenera data demo. En prod real habría que recuperar los reportes a mano.
3. **Fix forward**. La migración sumó columnas/tablas nuevas; si el fail es en código post-migración, probablemente es más rápido arreglar el código que revertir.

### Secretos y env vars

Sin secretos nuevos. DEV-116 no introduce integraciones externas (Metricool llega en DEV-111).

### Dependencias nuevas

Agregadas en `backend/requirements.txt`:

- `django-polymorphic==4.11.2` (BSD-3-Clause). Ver `docs/DEPENDENCIES.md` para audit metadata.

Sin dependencias frontend nuevas.

### Observación: CompressedManifestStaticFilesStorage

El ambiente dev container usa `whitenoise.storage.CompressedManifestStaticFilesStorage`. Esto requiere `collectstatic` pre-render antes de que el admin sirva. Los smoke tests de admin polimórfico (agregados en Task 3.1) usan un fixture `_plain_staticfiles` que override a `StaticFilesStorage` plano durante el test — NO afecta producción, solo evita el `ValueError: Missing staticfiles manifest entry` en pytest cuando renderizan admin change pages.
