from django.db import migrations, models

import Dashboard.models


class Migration(migrations.Migration):
    """
    Cosmetic-only migration. On Django 6, newly created models default their
    auto `id` field to BigAutoField; the 0033 migration explicitly used the
    older AutoField to match this project's other models. This migration
    just records that as the current, intended state - it does not change
    any data or the real column type on SQLite.

    It also re-records `UserViewPermission.view_name`'s dynamic choices
    function so `makemigrations --check` stays clean as new categories are
    added over time (the choices themselves are computed at runtime, not
    stored in the migration).
    """

    dependencies = [
        ('Dashboard', '0035_require_category_going_forward'),
    ]

    operations = [
        migrations.AlterField(
            model_name='committeetype',
            name='id',
            field=models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='userviewpermission',
            name='view_name',
            field=models.CharField(choices=Dashboard.models.committee_permission_choices, max_length=100),
        ),
    ]
