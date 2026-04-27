"""Datos parseados del xlsx — input al builder (post sections-widgets-redesign)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class ParsedWidget:
    type_name: str
    section_nombre: str
    widget_orden: int
    widget_title: str
    fields: dict
    items: list[dict] = field(default_factory=list)


@dataclass
class ParsedSection:
    nombre: str
    title: str
    layout: str
    order: int
    instructions: str


@dataclass
class ParsedReport:
    stage_id: int | None
    kind: str
    period_start: date
    period_end: date
    title: str
    intro_text: str
    conclusions_text: str
    sections: list[ParsedSection]
    widgets_by_section: dict[str, list[ParsedWidget]]
    image_refs: set[str]
