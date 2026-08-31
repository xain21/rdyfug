from django.db import migrations


# Old raw `type` values -> (display name, slug, icon)
LEGACY_TYPE_MAP = {
    'bod': ('BOD Meetings', 'bod', 'assets/images/bodmeeting.svg'),
    'agm': ('AGM', 'agm', 'assets/images/agm.svg'),
    'hr': ('HR Committee', 'hr', 'assets/images/hr.svg'),
    'finance': ('Finance Committee', 'finance', 'assets/images/fn.svg'),
    'audit': ('Audit Committee', 'audit', 'assets/images/Au.svg'),
    'procurement': ('Procurement Committee', 'procurement', 'assets/images/Au.svg'),
}

# Old UserViewPermission.view_name values -> new dynamic scheme
PERMISSION_NAME_MAP = {
    'all_meetings': 'list:bod',
    'agm_meeting': 'list:agm',
    'hr_meetings': 'list:hr',
    'fn_meetings': 'list:finance',
    'Au_meetings': 'list:audit',
    'pro_meetings': 'list:procurement',
    'meeting_details': 'details:bod',
    'hrmeeting_details': 'details:hr',
    'fn_details': 'details:finance',
    'Au_details': 'details:audit',
    'pro_details': 'details:procurement',
}


def forwards(apps, schema_editor):
    CommitteeType = apps.get_model('Dashboard', 'CommitteeType')
    BodMeeting = apps.get_model('Dashboard', 'BodMeeting')
    UserViewPermission = apps.get_model('Dashboard', 'UserViewPermission')

    order = 0
    slug_to_committee = {}
    for order, (legacy_key, (name, slug, icon)) in enumerate(LEGACY_TYPE_MAP.items()):
        committee, _ = CommitteeType.objects.get_or_create(
            slug=slug,
            defaults={'name': name, 'icon': icon, 'is_active': True, 'order': order},
        )
        slug_to_committee[legacy_key] = committee

    # Any existing meeting whose legacy_type doesn't match a known key
    # (defensive: blank/None/unexpected values) is mapped to a fallback
    # "Uncategorized" bucket rather than being silently dropped.
    fallback_committee = None

    for meeting in BodMeeting.objects.all():
        legacy_key = (meeting.legacy_type or '').strip().lower()
        committee = slug_to_committee.get(legacy_key)
        if committee is None:
            if fallback_committee is None:
                fallback_committee, _ = CommitteeType.objects.get_or_create(
                    slug='uncategorized',
                    defaults={
                        'name': 'Uncategorized',
                        'icon': 'assets/images/bodmeeting.svg',
                        'is_active': True,
                        'order': order + 1,
                    },
                )
            committee = fallback_committee
        meeting.category_id = committee.id
        meeting.save(update_fields=['category'])

    # Remap any previously-granted per-view permissions to the new
    # dynamic list:/details: scheme so existing access isn't lost.
    for perm in UserViewPermission.objects.all():
        new_name = PERMISSION_NAME_MAP.get(perm.view_name)
        if new_name and new_name != perm.view_name:
            perm.view_name = new_name
            perm.save(update_fields=['view_name'])


def backwards(apps, schema_editor):
    BodMeeting = apps.get_model('Dashboard', 'BodMeeting')
    UserViewPermission = apps.get_model('Dashboard', 'UserViewPermission')

    reverse_permission_map = {v: k for k, v in PERMISSION_NAME_MAP.items()}

    for meeting in BodMeeting.objects.select_related('category').all():
        if meeting.category_id:
            meeting.legacy_type = meeting.category.slug
            meeting.save(update_fields=['legacy_type'])

    for perm in UserViewPermission.objects.all():
        old_name = reverse_permission_map.get(perm.view_name)
        if old_name:
            perm.view_name = old_name
            perm.save(update_fields=['view_name'])


class Migration(migrations.Migration):

    dependencies = [
        ('Dashboard', '0033_committeetype_and_category_fk'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
