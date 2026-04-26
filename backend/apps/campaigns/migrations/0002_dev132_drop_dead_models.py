"""DEV-132: cleanup post-DEV-115/116 — drop NarrativeLine + apps influencers/scheduling.

Migración destructiva (no preservar data; nada en prod). Hace tres cosas:

1. DROP TABLE de las orphan tables que dejaron las apps `influencers` y
   `scheduling` (ya removidas de INSTALLED_APPS y borradas del repo).
   En postgres usamos CASCADE para limpiar el FK cruzado entre ellas y
   hacia `campaigns_narrativeline`. En sqlite (test DB recién creada)
   las tablas no existen, así que el DROP IF EXISTS es no-op.
2. DELETE FROM django_migrations para esas dos apps, así una migrate
   posterior no las trata como "applied" zombies.
3. DeleteModel(NarrativeLine) — Django ahora puede dropar la tabla
   limpio porque su único FK reverso (influencers_campaigninfluencer)
   ya no existe.
"""
from django.db import migrations


def drop_dead_tables(apps, schema_editor):
    cursor = schema_editor.connection.cursor()
    cascade = " CASCADE" if schema_editor.connection.vendor == "postgresql" else ""
    for tbl in (
        "scheduling_scheduledpost",
        "influencers_campaigninfluencer",
        "influencers_influencer",
    ):
        cursor.execute(f"DROP TABLE IF EXISTS {tbl}{cascade};")
    cursor.execute(
        "DELETE FROM django_migrations WHERE app IN ('influencers', 'scheduling');"
    )


class Migration(migrations.Migration):

    dependencies = [
        ('campaigns', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(drop_dead_tables, reverse_code=migrations.RunPython.noop),
        migrations.DeleteModel(name='NarrativeLine'),
    ]
