"""Reports domain models — Sections + Widgets architecture."""
from .report import Report  # noqa: F401
from .follower_snapshot import BrandFollowerSnapshot  # noqa: F401

# Sections + Widgets:
from .section import Section  # noqa: F401
from .widgets.base_widget import Widget  # noqa: F401
from .widgets.text import TextWidget  # noqa: F401
from .widgets.image import ImageWidget  # noqa: F401
from .widgets.text_image import TextImageWidget  # noqa: F401
from .widgets.kpi_grid import KpiGridWidget, KpiTile  # noqa: F401
from .widgets.table import TableWidget, TableRow  # noqa: F401
from .widgets.chart import ChartWidget, ChartDataPoint  # noqa: F401
from .widgets.top_contents import TopContentsWidget, TopContentItem  # noqa: F401
from .widgets.top_creators import TopCreatorsWidget, TopCreatorItem  # noqa: F401

# Attachments:
from .attachments import ReportAttachment  # noqa: F401
