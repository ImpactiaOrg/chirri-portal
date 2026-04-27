"""Reports domain models — package post-DEV-116 (split por concern)."""
from .report import Report  # noqa: F401
from .follower_snapshot import BrandFollowerSnapshot  # noqa: F401

# Typed blocks (DEV-116):
from .blocks.base_block import ReportBlock  # noqa: F401
from .blocks.text_image import TextImageBlock  # noqa: F401
from .blocks.image import ImageBlock  # noqa: F401
from .blocks.kpi_grid import KpiGridBlock, KpiTile as _LegacyKpiTile  # noqa: F401
from .blocks.table import TableBlock, TableRow as _LegacyTableRow  # noqa: F401
from .blocks.top_contents import TopContentsBlock, TopContentItem as _LegacyTopContentItem  # noqa: F401
from .blocks.top_creators import TopCreatorsBlock, TopCreatorItem as _LegacyTopCreatorItem  # noqa: F401
from .blocks.chart import ChartBlock, ChartDataPoint as _LegacyChartDataPoint  # noqa: F401

# Legacy-compat aliases kept so existing code that does
# `from apps.reports.models import KpiTile` continues to work.
# These will be removed in Task 8.
KpiTile = _LegacyKpiTile  # noqa: F401
TableRow = _LegacyTableRow  # noqa: F401
ChartDataPoint = _LegacyChartDataPoint  # noqa: F401
TopContentItem = _LegacyTopContentItem  # noqa: F401
TopCreatorItem = _LegacyTopCreatorItem  # noqa: F401

from .section import Section  # noqa: F401
from .widgets.base_widget import Widget  # noqa: F401

# Widget subtypes (Task 2):
from .widgets.text import TextWidget  # noqa: F401
from .widgets.image import ImageWidget  # noqa: F401
from .widgets.text_image import TextImageWidget  # noqa: F401
from .widgets.kpi_grid import KpiGridWidget, KpiTileWidget  # noqa: F401
from .widgets.table import TableWidget, TableRowWidget  # noqa: F401
from .widgets.chart import ChartWidget, ChartDataPointWidget  # noqa: F401
from .widgets.top_contents import TopContentsWidget, TopContentItemWidget  # noqa: F401
from .widgets.top_creators import TopCreatorsWidget, TopCreatorItemWidget  # noqa: F401

# Attachments (DEV-108):
from .attachments import ReportAttachment  # noqa: F401
