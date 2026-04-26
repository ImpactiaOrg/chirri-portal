"""Informational registry of consumer handler paths.

Keys are consumer names; values are dotted paths to the handler callable.
The Celery task uses django.utils.module_loading.import_string to resolve
LLMJob.handler_path directly, so this registry is for documentation / debug
only. New consumers register here for discoverability."""

REGISTRY: dict[str, str] = {
    "reports.pdf_parser": "apps.reports.importers.pdf_parser._run_pdf_parse",
}
