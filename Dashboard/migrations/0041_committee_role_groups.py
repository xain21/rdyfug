from django.db import migrations


GROUP_NAMES = ['Committee Member', 'Committee Chair', 'Admin']


def create_role_groups(apps, schema_editor):
    """
    Creates three reusable Django auth Groups so users can be assigned a
    role (Committee Member / Committee Chair / Admin) in one place instead
    of ticking every permission by hand for every user.

    This is intentionally additive: the existing per-user UserViewPermission
    system (per-category list/details access) keeps working exactly as
    before and is unaffected. These groups are a starting point for
    reusable roles - assign a user to 'Committee Chair' or 'Admin' from
    Django Admin -> Users, and use Admin -> Groups to attach whichever
    Django permissions that role should have (e.g. Admin -> can add/change
    CommitteeType, BodMeeting, etc.).
    """
    Group = apps.get_model('auth', 'Group')
    for name in GROUP_NAMES:
        Group.objects.get_or_create(name=name)


def remove_role_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=GROUP_NAMES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('Dashboard', '0040_bodmeeting_approval_status_bodmeeting_approved_at_and_more'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(create_role_groups, remove_role_groups),
    ]
