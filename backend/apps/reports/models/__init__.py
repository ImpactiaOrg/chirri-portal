"""Reports domain models — package post-DEV-116 (split por concern).

Durante la transición a bloques tipados, re-exportamos los modelos viejos
desde models_legacy y agregamos los nuevos a medida que existen.
"""
# Legacy (se van a eliminar al cerrar DEV-116):
from apps.reports.models_legacy import (  # noqa: F401
    Report,
    BrandFollowerSnapshot,
    OneLinkAttribution,
)

# Nuevos tipados (DEV-116):
from .blocks.base_block import ReportBlock  # noqa: F401
from .blocks.text_image import TextImageBlock  # noqa: F401
from .blocks.kpi_grid import KpiGridBlock, KpiTile  # noqa: F401
from .blocks.metrics_table import MetricsTableBlock, MetricsTableRow  # noqa: F401
from .blocks.top_contents import TopContentsBlock, TopContentItem  # noqa: F401
from .blocks.top_creators import TopCreatorsBlock, TopCreatorItem  # noqa: F401
from .blocks.attribution import AttributionTableBlock  # noqa: F401
from .blocks.chart import ChartBlock, ChartDataPoint  # noqa: F401

# Attachments (DEV-108):
from .attachments import ReportAttachment  # noqa: F401
