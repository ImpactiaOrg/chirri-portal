from django.db import migrations, models


def populate_topcontent_block(apps, schema_editor):
    """Attach each TopContent to a TOP_CONTENT ReportBlock in the same report,
    matched by kind. When no matching block exists, create one so the FK can be
    made NOT NULL in the follow-up migration without losing orphaned data.
    """
    TopContent = apps.get_model("reports", "TopContent")
    ReportBlock = apps.get_model("reports", "ReportBlock")

    for tc in TopContent.objects.select_related("report").all():
        match = (
            ReportBlock.objects
            .filter(report=tc.report, type="TOP_CONTENT")
            .filter(config__kind=tc.kind)
            .order_by("order")
            .first()
        )
        if match is None:
            next_order = (
                ReportBlock.objects.filter(report=tc.report)
                .aggregate(m=models.Max("order"))["m"] or 0
            ) + 1
            title = "Posts del mes" if tc.kind == "POST" else "Creators del mes"
            match = ReportBlock.objects.create(
                report=tc.report,
                type="TOP_CONTENT",
                order=next_order,
                config={"kind": tc.kind, "title": title, "limit": 6},
            )
        tc.block = match
        tc.save(update_fields=["block"])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0006_report_blocks_and_pdf"),
    ]

    operations = [
        migrations.AddField(
            model_name="topcontent",
            name="block",
            field=models.ForeignKey(
                to="reports.reportblock",
                on_delete=models.CASCADE,
                related_name="items",
                null=True,
                help_text="Bloque TOP_CONTENT que renderiza este ítem en el viewer.",
            ),
        ),
        migrations.RunPython(populate_topcontent_block, reverse_noop),
    ]
