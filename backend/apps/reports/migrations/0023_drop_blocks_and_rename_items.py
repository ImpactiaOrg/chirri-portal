# Hand-written migration — Task 8 of sections-widgets-redesign.
#
# Two operations:
#   1. Delete legacy block models (blocks/ directory removed from codebase).
#      Order: block item children first, then block containers, then ReportBlock.
#   2. Rename widget item models to canonical short names (drop "Widget" suffix).
#      Only after the legacy names are freed up.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0022_sections_widgets'),
    ]

    operations = [
        # ----------------------------------------------------------------
        # Part 1a: Delete legacy block item models (children of block containers).
        # ----------------------------------------------------------------
        migrations.DeleteModel(
            name='KpiTile',       # reports_kpitile — legacy block item
        ),
        migrations.DeleteModel(
            name='ChartDataPoint',  # reports_chartdatapoint — legacy block item
        ),
        migrations.DeleteModel(
            name='TableRow',        # reports_tablerow — legacy block item
        ),
        migrations.DeleteModel(
            name='TopContentItem',  # reports_topcontentitem — legacy block item
        ),
        migrations.DeleteModel(
            name='TopCreatorItem',  # reports_topcreatoritem — legacy block item
        ),

        # ----------------------------------------------------------------
        # Part 1b: Delete legacy block container models (leaf → base).
        # ----------------------------------------------------------------
        migrations.DeleteModel(
            name='KpiGridBlock',
        ),
        migrations.DeleteModel(
            name='TableBlock',
        ),
        migrations.DeleteModel(
            name='ChartBlock',
        ),
        migrations.DeleteModel(
            name='TopContentsBlock',
        ),
        migrations.DeleteModel(
            name='TopCreatorsBlock',
        ),
        migrations.DeleteModel(
            name='TextImageBlock',
        ),
        migrations.DeleteModel(
            name='ImageBlock',
        ),
        migrations.DeleteModel(
            name='ReportBlock',     # base polymorphic model — deleted last
        ),

        # ----------------------------------------------------------------
        # Part 2: Rename widget item models.
        # The legacy names are now freed, so renaming is conflict-free.
        # ----------------------------------------------------------------
        migrations.RenameModel(
            old_name='KpiTileWidget',
            new_name='KpiTile',
        ),
        migrations.RenameModel(
            old_name='TableRowWidget',
            new_name='TableRow',
        ),
        migrations.RenameModel(
            old_name='ChartDataPointWidget',
            new_name='ChartDataPoint',
        ),
        migrations.RenameModel(
            old_name='TopContentItemWidget',
            new_name='TopContentItem',
        ),
        migrations.RenameModel(
            old_name='TopCreatorItemWidget',
            new_name='TopCreatorItem',
        ),
    ]
