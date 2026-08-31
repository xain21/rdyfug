# urls.py
from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView, LoginView

urlpatterns = [
    path('', views.view_home, name='home'),
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),

    # ---- Fully dynamic committee/category URLs -------------------------
    # Works for ANY CommitteeType record, including ones created after
    # deployment (e.g. 'IT Support', 'Legal Committee') - no new URL,
    # view, or template is ever needed for a new category.
    path('committee/<slug:category_slug>/', views.category_meetings, name='category_meetings'),
    path('committee/<slug:category_slug>/search/', views.category_search, name='category_search'),

    # ---- Legacy URL names, kept for backward compatibility -------------
    # Each simply pins the generic dynamic view to the historical slug, so
    # every old bookmark/link/template tag keeps working unchanged.
    path('allmeetings/', views.category_meetings, {'category_slug': 'bod'}, name='all_meetings'),
    path('meetingsearch/', views.category_search, {'category_slug': 'bod'}, name='meetingsearch'),

    path('agm-meetings/', views.category_meetings, {'category_slug': 'agm'}, name='agm_meeting'),
    path('agmsearch/', views.category_search, {'category_slug': 'agm'}, name='agmsearch'),

    path('hr_meetings/', views.category_meetings, {'category_slug': 'hr'}, name='hr_meetings'),
    path('hr-meetings/search/', views.category_search, {'category_slug': 'hr'}, name='hr_search'),

    path('fn_meeting/', views.category_meetings, {'category_slug': 'finance'}, name='fnmeetings'),
    path('finance-meetings/search/', views.category_search, {'category_slug': 'finance'}, name='fn_search'),

    path('au_meeting/', views.category_meetings, {'category_slug': 'audit'}, name='Aumeetings'),
    path('audit-meetings/search/', views.category_search, {'category_slug': 'audit'}, name='au_search'),

    path('pro_meeting/', views.category_meetings, {'category_slug': 'procurement'}, name='promeetings'),
    path('procurement-meetings/search/', views.category_search, {'category_slug': 'procurement'}, name='pn_search'),

    # ---- Meeting/agenda details & site-wide search ----------------------
    # A single generic details view already worked for any meeting id
    # regardless of category, so every legacy "*_details" name below points
    # at the same view/template.
    path('meeting/<int:meeting_id>/', views.meeting_details, name='meeting_details'),
    path('meeting/<int:meeting_id>/download/', views.download_meeting_pdf, name='download_meeting_pdf'),
    path('meeting-details/<int:meeting_id>/', views.meeting_details, name='meeting_details_alt'),
    path('hrmeeting_details/<int:meeting_id>/', views.meeting_details, name='hrmeeting_details'),
    path('fnmeeting_details/<int:meeting_id>/', views.meeting_details, name='fnmeeting_details'),
    path('aumeeting_details/<int:meeting_id>/', views.meeting_details, name='aumeeting_details'),
    path('promeeting_details/<int:meeting_id>/', views.meeting_details, name='promeeting_details'),

    path('minutes/<int:meeting_id>/', views.minutes_details, name='minutes_details'),
    path('meeting/<int:meeting_id>/approval/', views.update_meeting_approval, name='update_meeting_approval'),
    path('meeting/<int:meeting_id>/sign/', views.sign_meeting, name='sign_meeting'),
    path('meeting/<int:meeting_id>/ical/', views.meeting_ical, name='meeting_ical'),
    path('calendar/', views.meetings_calendar, name='meetings_calendar'),

    path('action-items/', views.action_items_list, name='action_items_list'),
    path('activity-log/', views.activity_log, name='activity_log'),

    path('search/', views.search, name='search'),

    path('members/', views.view_members, name='view_members'),
    path('member/<int:id>/', views.view_member_details, name='view_member_details'),
    path('committee-users/<int:department_id>/<int:member_id>/', views.get_committee_users, name='get_committee_users'),
    path('notification/<int:id>/', views.get_notification, name='get_notification'),

    path('get_agendas/', views.get_agendas, name='get_agendas'),

    path('auto-extract/', views.auto_extract_meeting, name='auto_extract_meeting'),
]
