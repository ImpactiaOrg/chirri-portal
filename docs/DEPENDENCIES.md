# External Dependencies Audit

Tracking audit metadata for new external deps added to the project. Add an entry when introducing a new runtime or dev dependency that isn't trivial (e.g., typing utilities, existing frameworks).

## Python (backend)

### django-polymorphic 4.11.2

- **License:** BSD-3-Clause (OSI-compatible).
- **Release:** 2026-03-07.
- **Last audited:** 2026-04-23 (DEV-116 PR).
- **Purpose:** Multi-table inheritance for typed ReportBlock subtypes. Powers the admin UX ("add block → pick subtype → typed fields") and the polymorphic serializer dispatcher. See `docs/superpowers/specs/2026-04-22-dev-116-typed-blocks-refactor-design.md`.
- **Compat:** Django 4.2 / 5.2 / 6.0. Python ≥3.10.
- **Tested against:** Django 5.0.9 (current repo version). Package
  classifiers advertise 4.2/5.2/6.0 — 5.0 is NOT in the declared matrix but
  works in practice. Re-evaluate when bumping Django (5.2+ is the next
  supported LTS).

### django-admin-sortable2 2.2.8

- **License:** MIT (OSI-compatible).
- **Release:** 2025-05-15.
- **Last audited:** 2026-04-23 (DEV-116 post-review cleanup).
- **Purpose:** Drag-reorder for the child row inlines (KpiTile /
  MetricsTableRow / ChartDataPoint / TopContent) inside the block subtype
  admins. Eliminates manual integer `order` entry.
- **Compat:** Django 4.2 / 5.0 / 5.1 / 5.2. Python ≥3.10.
- **Version note:** bumped from 2.1.10 during DEV-116 cleanup because
  2.1.10 only shipped admin templates up to `tabular-django-4.2.html` and
  raised `TemplateDoesNotExist: tabular-django-5.0.html` on our Django
  5.0.9. 2.2.x adds the Django 5.0+ templates.
