"""Reports domain models — package post-DEV-116 (split por concern)."""
from .report import Report  # noqa: F401
from .follower_snapshot import BrandFollowerSnapshot  # noqa: F401
from .onelink_attribution import OneLinkAttribution  # noqa: F401

# Typed blocks (DEV-116):
from .blocks.base_block import ReportBlock  # noqa: F401
from .blocks.text_image import TextImageBlock  # noqa: F401
from .blocks.image import ImageBlock  # noqa: F401
from .blocks.kpi_grid import KpiGridBlock, KpiTile  # noqa: F401
from .blocks.metrics_table import MetricsTableBlock, MetricsTableRow  # noqa: F401
from .blocks.table import TableBlock, TableRow  # noqa: F401
from .blocks.top_contents import TopContentsBlock, TopContentItem  # noqa: F401
from .blocks.top_creators import TopCreatorsBlock, TopCreatorItem  # noqa: F401
from .blocks.attribution import AttributionTableBlock  # noqa: F401
from .blocks.chart import ChartBlock, ChartDataPoint  # noqa: F401

# Attachments (DEV-108):
from .attachments import ReportAttachment  # noqa: F401
