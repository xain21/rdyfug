import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Dashboard', '0034_migrate_legacy_types_to_committeetype'),
    ]

    operations = [
        # `null=True` is intentionally kept at the database level (data
        # safety net), but `blank=False` means Django Admin and any ModelForm
        # will require a category to be selected for new/edited meetings.
        migrations.AlterField(
            model_name='bodmeeting',
            name='category',
            field=models.ForeignKey(
                null=True,
                blank=False,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='meetings',
                to='Dashboard.committeetype',
            ),
        ),
    ]
