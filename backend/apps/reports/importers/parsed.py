"""Dataclasses intermedias del parser (DEV-83 · Etapa 2).

`ParsedReport` es el contrato entre el `excel_parser` (input) y el
`builder` (que crea las filas en DB). Fuera de los módulos del importer,
no debería filtrarse — el admin recibe un `Report` ya creado.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class ParsedBlock:
    """Bloque parseado listo para instanciar. `type_name` identifica el subtipo
    (ej. 'TextImageBlock'). `fields` mapea a los fields escalares del parent.
    `items` contiene dicts con los child rows (vacío para blocks sin items)."""
    type_name: str
    nombre: str
    fields: dict
    items: list[dict] = field(default_factory=list)


@dataclass
class ParsedReport:
    """Report + blocks listos para `builder.build_report(...)`."""
    stage_id: int | None  # lo setea el caller del admin form; None en validate_import
    kind: str              # ej. "MENSUAL"
    period_start: date
    period_end: date
    title: str
    intro_text: str
    conclusions_text: str
    layout: list[tuple[int, str]]  # (orden, nombre) ordenado por orden
    blocks: dict[str, ParsedBlock] = field(default_factory=dict)
    image_refs: set[str] = field(default_factory=set)

    def block_count(self) -> int:
        return len(self.blocks)
