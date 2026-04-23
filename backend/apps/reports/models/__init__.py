"""Reports domain models — package post-DEV-116 (split por concern).

Durante la transición a bloques tipados, re-exportamos los modelos viejos
desde models_legacy y agregamos los nuevos a medida que existen.
"""
# Legacy (se van a eliminar al cerrar DEV-116):
from apps.reports.models_legacy import (  # noqa: F401
    Report,
    ReportMetric,
    TopContent,
    BrandFollowerSnapshot,
    OneLinkAttribution,
)

# Nuevos tipados (DEV-116):
from .blocks.base_block import ReportBlock  # noqa: F401
from .blocks.text_image import TextImageBlock  # noqa: F401
