"""Idempotent loader of seed prompts into the DB.

Reads .md files from apps/llm/seed/ and creates a Prompt + a v1 PromptVersion
for each. If the prompt already exists, does nothing (does NOT bump the version
or overwrite the body — explicit prompt edits go via admin).
"""
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.llm.models import Prompt, PromptVersion

SEED_DIR = Path(__file__).resolve().parent.parent.parent / "seed"

# Per-prompt metadata not present in the .md file body.
PROMPT_META = {
    "parse_pdf_report": {
        "name": "Parse PDF Report",
        "description": (
            "Parser de PDFs legacy a ParsedReport (use case A, DEV-84). "
            "Recibe páginas como imágenes, devuelve JSON estructurado."
        ),
        "consumer": "reports.pdf_parser",
        "model_hint": "accounts/fireworks/models/kimi-k2-instruct-0905",
        "response_format": "json_object",
        "json_schema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string"},
                "period_start": {"type": "string"},
                "period_end": {"type": "string"},
                "title": {"type": "string"},
                "intro_text": {"type": "string"},
                "conclusions_text": {"type": "string"},
                "layout": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": [
                            {"type": "integer"}, {"type": "string"},
                        ],
                        "minItems": 2, "maxItems": 2,
                    },
                },
                "blocks": {"type": "object"},
            },
            "required": ["kind", "period_start", "period_end", "title",
                         "layout", "blocks"],
        },
    },
}


class Command(BaseCommand):
    help = "Seed prompts from apps/llm/seed/*.md (idempotent)."

    def handle(self, *args, **options):
        created = skipped = 0
        for md in sorted(SEED_DIR.glob("*.md")):
            key = md.stem
            meta = PROMPT_META.get(key)
            if meta is None:
                self.stdout.write(self.style.WARNING(
                    f"skip {key}: no PROMPT_META entry"
                ))
                continue
            if Prompt.objects.filter(key=key).exists():
                skipped += 1
                continue
            p = Prompt.objects.create(
                key=key, name=meta["name"], description=meta["description"],
                consumer=meta["consumer"],
            )
            v1 = PromptVersion.objects.create(
                prompt=p, body=md.read_text(encoding="utf-8"),
                model_hint=meta["model_hint"],
                response_format=meta["response_format"],
                json_schema=meta["json_schema"],
                notes="seed v1",
            )
            p.active_version = v1
            p.save()
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"seed_prompts: created={created} skipped={skipped}"
        ))
