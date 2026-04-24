"""Error estructurado para el parser/bundle_reader (DEV-83 · Etapa 2).

Todos los errores que ve el usuario pasan por `ImporterError`. El admin
serializa `List[ImporterError]` a una tabla (hoja, fila, columna, razón).
No hay `raise ValueError(...)` dispersos — cualquier inconsistencia se
acumula y se muestra junta.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImporterError:
    sheet: str
    row: int | None
    column: str | None
    reason: str

    def to_dict(self) -> dict:
        return {
            "sheet": self.sheet,
            "row": self.row,
            "column": self.column,
            "reason": self.reason,
        }
