# External Dependencies Audit

Tracking audit metadata for new external deps added to the project. Add an entry when introducing a new runtime or dev dependency that isn't trivial (e.g., typing utilities, existing frameworks).

## Python (backend)

### django-polymorphic 4.11.2

- **License:** BSD-3-Clause (OSI-compatible).
- **Release:** 2026-03-07.
- **Last audited:** 2026-04-23 (DEV-116 PR).
- **Purpose:** Multi-table inheritance for typed ReportBlock subtypes. Powers the admin UX ("add block → pick subtype → typed fields") and the polymorphic serializer dispatcher. See `docs/superpowers/specs/2026-04-22-dev-116-typed-blocks-refactor-design.md`.
- **Compat:** Django 4.2 / 5.2 / 6.0. Python ≥3.10.
