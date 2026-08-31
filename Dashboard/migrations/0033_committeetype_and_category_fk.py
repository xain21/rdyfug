import django.db.models.deletion
from django.db import migrations, models

import Dashboard.models


class Migration(migrations.Migration):

    dependencies = [
        ('Dashboard', '0032_alter_member_address_alter_member_email_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='CommitteeType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True)),
                ('slug', models.SlugField(blank=True, max_length=170, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('icon', models.CharField(
                    blank=True, default='assets/images/bodmeeting.svg', max_length=255, null=True,
                    help_text='Static path to an icon shown on the homepage, e.g. assets/images/agm.svg',
                )),
                ('is_active', models.BooleanField(
                    default=True,
                    help_text='Only active categories are shown on the site, in upload forms, and in search.',
                )),
                ('order', models.PositiveIntegerField(default=0, help_text='Lower numbers appear first on the homepage.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Committee Type',
                'verbose_name_plural': 'Committee Types',
                'ordering': ['order', 'name'],
            },
        ),
        # Step 1 of the safe data migration: rename the old raw `type` string
        # field out of the way (kept for audit/history) instead of deleting it.
        migrations.RenameField(
            model_name='bodmeeting',
            old_name='type',
            new_name='legacy_type',
        ),
        migrations.AlterField(
            model_name='bodmeeting',
            name='legacy_type',
            field=models.CharField(blank=True, editable=False, max_length=50, null=True),
        ),
        # Step 2: add the new dynamic FK, nullable for now so the data
        # migration in 0034 can populate it safely before we enforce it.
        migrations.AddField(
            model_name='bodmeeting',
            name='category',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='meetings',
                to='Dashboard.committeetype',
            ),
        ),
    ]
