from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0007_topcontent_block_fk"),
    ]

    operations = [
        migrations.AlterField(
            model_name="topcontent",
            name="block",
            field=models.ForeignKey(
                to="reports.reportblock",
                on_delete=models.CASCADE,
                related_name="items",
                help_text="Bloque TOP_CONTENT que renderiza este ítem en el viewer.",
            ),
        ),
    ]
