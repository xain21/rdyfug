from django.shortcuts import redirect, render, get_object_or_404
from django.db.models import Q
from django.http import JsonResponse, Http404
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.utils import timezone
from .utils import process_page_ocr, extract_text_from_file, parse_meeting_document
import os
import tempfile
from django.core.files import File
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse

from Dashboard.models import (
    Agenda, BodMeeting, CommitteeType, Department, Member, MinutesOfMeeting,
    Notifications, SubAgenda, Sub_sub_Agenda, BODMember, UserViewPermission,
    DocumentAccessLog, ActionItem, DocumentVersion, DocumentSignature,
)
from django.shortcuts import render
from .decorators import view_permission_required, category_permission_required


# login
from django.contrib.auth.decorators import login_required

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'home')  # Redirect to original URL or home
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'login.html')  # Render your login template

@login_required
def view_home(request):
    results = BodMeeting.objects.all()

    # Add the class name to each result
    for result in results:
        result.class_name = result.__class__.__name__

    # Active categories, loaded dynamically from the database. Adding a new
    # CommitteeType in Admin makes it show up here automatically.
    categories = CommitteeType.objects.filter(is_active=True).order_by('order', 'name')

    # --- Homepage summary stats ------------------------------------------
    # Small "reason to check in" numbers for the homepage, per the roadmap's
    # "Everyday Usability" recommendation. Kept cheap (simple counts) so
    # this doesn't slow the homepage down.
    now = timezone.now()
    meetings_this_month = BodMeeting.objects.filter(
        date__year=now.year, date__month=now.month
    ).count()
    pending_approvals = BodMeeting.objects.exclude(
        approval_status=BodMeeting.APPROVAL_APPROVED
    ).count()
    open_action_items = ActionItem.objects.exclude(status='done').count()
    overdue_action_items = ActionItem.objects.exclude(status='done').filter(
        due_date__lt=now.date()
    ).count()

    context = {
        'results': results,
        'categories': categories,
        'meetings_this_month': meetings_this_month,
        'pending_approvals': pending_approvals,
        'open_action_items': open_action_items,
        'overdue_action_items': overdue_action_items,
    }
    return render(request, 'homepage.html', context)


@login_required
def members(request):
    return render(request, 'members.html')



# BOD Meeting Card

@login_required
def category_meetings(request, category_slug):
    """
    Generic, dynamic replacement for all_meetings/agm_meeting/hr_meetings/
    fn_meetings/Au_meetings/pro_meetings.

    The committee/category is resolved purely from the URL slug against the
    CommitteeType table, so this single view serves every existing category
    AND any brand-new category created later in Admin - with zero code
    changes required.
    """
    category = get_object_or_404(CommitteeType, slug=category_slug)
    if not category.is_active and not request.user.is_superuser:
        raise Http404("This category is not currently active.")

    if not request.user.is_superuser:
        view_name = f'list:{category.slug}'
        if not UserViewPermission.objects.filter(user=request.user, view_name=view_name, can_view=True).exists():
            message = f"Sorry {request.user.username}, you do not have permission to view this page."
            return render(request, 'forbidden.html', {'message': message})

    search_term = request.POST.get('search', '') if request.method == 'POST' else request.GET.get('search', '')

    meetings_qs = BodMeeting.objects.filter(category=category)
    if search_term:
        meetings_qs = meetings_qs.filter(title__icontains=search_term)

    # Pagination setup
    page_size = int(request.GET.get('pagesize', 10))
    page = int(request.GET.get('page', 1))
    offset = (page - 1) * page_size

    paginated_meetings = list(meetings_qs.order_by('date')[offset:offset + page_size])
    for meeting in paginated_meetings:
        meeting.date_display = meeting.date.strftime('%d/%m/%y') if meeting.date else "No date available"

        agendas = meeting.agendas.all()
        meeting.has_agenda = agendas.exists()
        meeting.is_empty_agenda = not any(agenda.attachment_1 or agenda.pdf for agenda in agendas)
        meeting.no_agenda = not meeting.has_agenda

    total_meetings = meetings_qs.count()
    total_pages = (total_meetings + page_size - 1) // page_size
    pagination_ranges = [(i * page_size + 1, min((i + 1) * page_size, total_meetings)) for i in range(total_pages)]

    agendas_search = Agenda.objects.none()
    if search_term:
        agendas_search = Agenda.objects.select_related('add_meeting').filter(
            add_meeting__category=category, title__icontains=search_term
        )

    context = {
        'category': category,
        'meetings': paginated_meetings,
        'total_meetings': total_meetings,
        'page_size': page_size,
        'page': page,
        'pagination_ranges': pagination_ranges,
        'search_term': search_term,
        'agendas': agendas_search,
    }
    return render(request, 'category_meetings.html', context)


@login_required
def category_search(request, category_slug):
    """
    Generic, dynamic replacement for meeting_search/agm_search/hr_search/
    fn_search/au_search/pn_search. Scoped to a single category, resolved
    from the URL slug - works automatically for any future category.
    """
    category = get_object_or_404(CommitteeType, slug=category_slug)

    search_term = request.POST.get('search', '').strip() if request.method == 'POST' else request.GET.get('search', '').strip()

    meetings = BodMeeting.objects.none()
    agendas = Agenda.objects.none()
    mom = MinutesOfMeeting.objects.none()

    if search_term:
        meetings = BodMeeting.objects.filter(category=category).filter(
            Q(title__icontains=search_term) |
            Q(description__icontains=search_term) |
            Q(date__icontains=search_term)
        )
        agendas = Agenda.objects.filter(add_meeting__category=category).filter(
            Q(title__icontains=search_term)
        )
        mom = MinutesOfMeeting.objects.filter(meeting__category=category).filter(
            Q(title__icontains=search_term)
        )

    return render(request, 'search_results.html', {
        'meetings': meetings,
        'agendas': agendas,
        'search_term': search_term,
        'mom': mom,
        'category': category,
    })


@login_required
def meeting_details(request, meeting_id):
    """
    Generic meeting/agenda details view shared by every category (this
    single view already worked for any BodMeeting id regardless of type;
    it now also enforces the dynamic per-category 'details:<slug>'
    permission when the meeting has a category assigned).
    """
    meeting = get_object_or_404(BodMeeting, id=meeting_id)

    if not request.user.is_superuser and meeting.category_id:
        view_name = f'details:{meeting.category.slug}'
        if not UserViewPermission.objects.filter(user=request.user, view_name=view_name, can_view=True).exists():
            message = f"Sorry {request.user.username}, you do not have permission to view this page."
            return render(request, 'forbidden.html', {'message': message})

    # Audit trail: record that this user opened this meeting's details.
    DocumentAccessLog.objects.create(
        user=request.user,
        meeting=meeting,
        action='view',
        ip_address=_get_client_ip(request),
    )

    # Fetch all agendas related to this meeting
    agendas = Agenda.objects.filter(add_meeting=meeting)

    # Fetch sub-agendas for each agenda in the meeting, ordered by title
    sub_agendas = SubAgenda.objects.filter(agenda__in=agendas).order_by('subagenda_title')

    # Create a list to store sub-agendas for each agenda
    agenda_list = []
    for agenda in agendas:
        agenda_sub_agendas = [
            {
                'subagenda_title': sub_agenda.subagenda_title,
                'subagenda_description': sub_agenda.subagenda_description or "No description available",
                'subagenda_descision': sub_agenda.subagenda_descision or "No decision available",
                'sub_sub_agendas': Sub_sub_Agenda.objects.filter(sub_sub_agenda=sub_agenda).order_by('subagenda_title')
            }
            for sub_agenda in sub_agendas if sub_agenda.agenda.id == agenda.id
        ]
        agenda_list.append({
            'agenda': agenda,
            'sub_agendas': agenda_sub_agendas
        })

    context = {
        'meeting': meeting,
        'agenda_list': agenda_list,
        'action_items': meeting.action_items.all(),
        'approval_choices': BodMeeting.APPROVAL_STATUS_CHOICES,
        'document_versions': meeting.document_versions.all(),
        'signatures': meeting.signatures.select_related('user').all(),
        'user_has_signed': meeting.signatures.filter(user=request.user).exists(),
    }

    return render(request, 'meeting_details.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def update_meeting_approval(request, meeting_id):
    """
    Move a meeting's minutes/documents through Draft -> Reviewed ->
    Approved. Restricted to staff/superuser accounts, since this is a
    governance signal (not just a display field) that regular viewers
    shouldn't be able to set themselves.
    """
    meeting = get_object_or_404(BodMeeting, id=meeting_id)
    if request.method == 'POST':
        new_status = request.POST.get('approval_status')
        valid_statuses = dict(BodMeeting.APPROVAL_STATUS_CHOICES)
        if new_status in valid_statuses:
            meeting.approval_status = new_status
            meeting.approved_by = request.user
            meeting.approved_at = timezone.now()
            meeting.save(update_fields=['approval_status', 'approved_by', 'approved_at'])
            messages.success(request, f'"{meeting.title}" marked as {valid_statuses[new_status]}.')
        else:
            messages.error(request, 'Invalid status.')
    return redirect('meeting_details', meeting_id=meeting.id)


@login_required
def sign_meeting(request, meeting_id):
    """
    Internal e-signature: the logged-in user types their name to confirm
    they've reviewed/signed off on this meeting's minutes. One signature
    per user per meeting (re-submitting just updates the name/timestamp).
    """
    meeting = get_object_or_404(BodMeeting, id=meeting_id)
    if request.method == 'POST':
        signed_name = request.POST.get('signed_name', '').strip()
        if not signed_name:
            messages.error(request, 'Please type your full name to sign.')
        else:
            DocumentSignature.objects.update_or_create(
                meeting=meeting, user=request.user,
                defaults={'signed_name': signed_name, 'ip_address': _get_client_ip(request)},
            )
            messages.success(request, 'You have signed this document.')
    return redirect('meeting_details', meeting_id=meeting.id)


def _ics_escape(text):
    """Escapes text for safe inclusion in an .ics (iCalendar) file field."""
    return (text or '').replace('\\', '\\\\').replace(',', '\\,').replace(';', '\\;').replace('\n', '\\n')


@login_required
def meeting_ical(request, meeting_id):
    """Downloads a single meeting as a .ics file the user can add to their own calendar app."""
    from django.http import HttpResponse

    meeting = get_object_or_404(BodMeeting, id=meeting_id)
    if not meeting.date:
        raise Http404("This meeting has no date set, so it can't be exported to a calendar.")

    dt = meeting.date.strftime('%Y%m%d')
    category_name = meeting.category.name if meeting.category_id else ''
    ics = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//BOD Portal//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:meeting-{meeting.id}@bod-portal\r\n"
        f"DTSTAMP:{timezone.now().strftime('%Y%m%dT%H%M%SZ')}\r\n"
        f"DTSTART;VALUE=DATE:{dt}\r\n"
        f"SUMMARY:{_ics_escape(meeting.title)}\r\n"
        f"DESCRIPTION:{_ics_escape(category_name)}\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
    response = HttpResponse(ics, content_type='text/calendar')
    response['Content-Disposition'] = f'attachment; filename="meeting-{meeting.id}.ics"'
    return response


@login_required
def meetings_calendar(request):
    """
    Month-view calendar of all meetings, with previous/next month
    navigation. Meetings are shown on whichever day their `date` falls on;
    clicking one goes straight to its details page.
    """
    import calendar as cal_module

    today = timezone.now().date()
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except ValueError:
        year, month = today.year, today.month
    if month < 1 or month > 12:
        month = today.month

    month_weeks = cal_module.Calendar(firstweekday=6).monthdayscalendar(year, month)  # Sunday-first

    meetings = BodMeeting.objects.filter(date__year=year, date__month=month).select_related('category')
    meetings_by_day = {}
    for m in meetings:
        meetings_by_day.setdefault(m.date.day, []).append(m)

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

    context = {
        'year': year,
        'month': month,
        'month_name': cal_module.month_name[month],
        'month_weeks': month_weeks,
        'meetings_by_day': meetings_by_day,
        'prev_year': prev_year, 'prev_month': prev_month,
        'next_year': next_year, 'next_month': next_month,
        'today': today,
    }
    return render(request, 'meetings_calendar.html', context)


@login_required
def action_items_list(request):
    """
    Front-end list of action items across every meeting (previously only
    visible in Django Admin). Anyone logged in can see the list; only
    staff/superuser or the person the item is assigned to can change its
    status, so a member can't mark someone else's task done.
    """
    items = ActionItem.objects.select_related('meeting', 'assigned_to', 'meeting__category').all()

    status_filter = request.GET.get('status', '')
    if status_filter in ('open', 'in_progress', 'done'):
        items = items.filter(status=status_filter)

    mine_only = request.GET.get('mine') == '1'
    if mine_only:
        items = items.filter(assigned_to=request.user)

    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        new_status = request.POST.get('status')
        item = get_object_or_404(ActionItem, id=item_id)
        can_edit = request.user.is_staff or request.user.is_superuser or item.assigned_to_id == request.user.id
        if can_edit and new_status in dict(ActionItem.STATUS_CHOICES):
            item.status = new_status
            item.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'Action item updated.')
        else:
            messages.error(request, "You don't have permission to update that item.")
        return redirect(request.get_full_path())

    context = {
        'items': items,
        'status_filter': status_filter,
        'mine_only': mine_only,
        'status_choices': ActionItem.STATUS_CHOICES,
    }
    return render(request, 'action_items.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def activity_log(request):
    """
    Readable, filterable front-end report for DocumentAccessLog (who viewed
    or downloaded which document, and when) - the "next step" the roadmap
    called for on top of the raw Admin table. Staff/superuser only, since
    this is an audit trail of other users' activity.
    """
    logs = DocumentAccessLog.objects.select_related('user', 'meeting', 'meeting__category').all()

    action_filter = request.GET.get('action', '')
    if action_filter in ('view', 'download'):
        logs = logs.filter(action=action_filter)

    search_term = request.GET.get('search', '').strip()
    if search_term:
        logs = logs.filter(
            Q(user__username__icontains=search_term) | Q(meeting__title__icontains=search_term)
        )

    page_size = 50
    page = int(request.GET.get('page', 1))
    offset = (page - 1) * page_size
    total = logs.count()
    total_pages = (total + page_size - 1) // page_size
    paginated_logs = logs[offset:offset + page_size]

    context = {
        'logs': paginated_logs,
        'action_filter': action_filter,
        'search_term': search_term,
        'page': page,
        'total_pages': total_pages,
        'total': total,
    }
    return render(request, 'activity_log.html', context)


@login_required
def download_meeting_pdf(request, meeting_id):
    """
    Proxy for downloading a meeting's PDF. Exists purely so the download can
    be logged to DocumentAccessLog (a direct link to the media file would
    bypass Django entirely and couldn't be tracked) - then redirects the
    browser straight to the actual file, so behavior otherwise looks
    identical to a normal download link.
    """
    meeting = get_object_or_404(BodMeeting, id=meeting_id)
    if not meeting.pdf:
        raise Http404("No PDF attached to this meeting.")

    DocumentAccessLog.objects.create(
        user=request.user,
        meeting=meeting,
        action='download',
        ip_address=_get_client_ip(request),
    )
    return redirect(meeting.pdf.url)


def _get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@login_required
def minutes_details(request, meeting_id):
    meeting = get_object_or_404(BodMeeting, id=meeting_id)
    return render(request, 'minutes_details.html', {'meeting': meeting})


# View function for searching PDFs

import fitz  # PyMuPDF

@login_required
def search(request):
    search_term = request.POST.get('search', '').strip()
    # 'text'  -> only search normal, selectable PDF text (fast, skips OCR entirely)
    # 'ocr'   -> search normal PDF text AND OCR'd image text (slower, thorough)
    search_mode = request.POST.get('search_mode', 'ocr')
    if search_mode not in ('text', 'ocr'):
        search_mode = 'ocr'
    use_ocr = (search_mode == 'ocr')

    if request.method == 'POST' and search_term:
        # Only search meetings that belong to an active category (or are not
        # yet categorized). This is fully dynamic: it queries whichever
        # CommitteeType rows are currently active, so a brand-new category
        # is automatically included and a disabled one is automatically
        # excluded - no code changes needed.
        active_or_uncategorized = Q(category__isnull=True) | Q(category__is_active=True)

        # Regular search in database fields
        meetings = BodMeeting.objects.filter(active_or_uncategorized).filter(
            Q(title__icontains=search_term) |
            Q(description__icontains=search_term)
        )
        agendas = Agenda.objects.select_related('add_meeting').filter(
            Q(add_meeting__category__isnull=True) | Q(add_meeting__category__is_active=True)
        ).filter(title__icontains=search_term)
        sub_agendas = SubAgenda.objects.select_related('agenda', 'bod_meeting').filter(
            Q(bod_meeting__category__isnull=True) | Q(bod_meeting__category__is_active=True)
        ).filter(
            Q(subagenda_title__icontains=search_term) |
            Q(subagenda_description__icontains=search_term)
        )
        sub_sub_agendas = Sub_sub_Agenda.objects.filter(
            Q(sub_sub_agenda__bod_meeting__category__isnull=True) | Q(sub_sub_agenda__bod_meeting__category__is_active=True)
        ).filter(subagenda_title__icontains=search_term)

        # PDF content search - only runs in "Text + OCR" mode. When the user
        # picks "Text only", we skip PDFs entirely and only search the
        # database fields (title/description) above.
        pdf_results = []
        if search_mode == 'ocr':
            all_meetings_with_pdfs = BodMeeting.objects.filter(active_or_uncategorized).filter(pdf__isnull=False)

            for meeting in all_meetings_with_pdfs:
                try:
                    # Check if the meeting has a valid file
                    if not meeting.pdf or not meeting.pdf.name.strip():
                        continue

                    pdf_path = meeting.pdf.path  # Get the file path
                    text = ""  # Initialize empty text
                    context_text = ""  # Initialize context for snippet display
                    page_number = 0  # Initialize page number for the snippet

                    # Search through the text content of the PDF
                    with fitz.open(pdf_path) as pdf:
                        for page in pdf:
                            page_number += 1  # Track the current page number
                            page_text = process_page_ocr(page, pdf_path, "", use_ocr=use_ocr)  # Extract text from the page (OCR only if requested)

                            # Check if the search term is found in the page's text
                            if search_term.lower() in page_text.lower():
                                # Create a snippet of the surrounding text to show where the term appears
                                snippet = page_text.lower().find(search_term.lower())
                                context_text = page_text[snippet - 50:snippet + 50] if snippet != -1 else "Not found"

                                pdf_results.append({
                                    'meeting': meeting,
                                    'category': meeting.category.name if meeting.category_id else 'Uncategorized',
                                    'pdf_url': meeting.pdf.url,
                                    'page_number': page_number,  # Page number is now tracked
                                    'snippet': context_text,  # Add the snippet of text with the term highlighted
                                })
                                break  # Found the term, no need to scan further

                except Exception as e:
                    print(f"Error processing PDF for meeting {meeting.id}: {e}")

        # Add results to context
        context = {
            'search_term': search_term,
            'search_mode': search_mode,
            'meetings': meetings,
            'agendas': agendas,
            'sub_agendas': sub_agendas,
            'sub_sub_agendas': sub_sub_agendas,
            'pdf_results': pdf_results,
        }

        return render(request, 'search_results.html', context)
    else:
        return render(request, 'search_results.html', {'error': 'No search term provided or invalid request.'})


        
@login_required
def view_members(request):
    bod_members = BODMember.objects.all().order_by('-from_date')
    departments_with_members = []  # This will store departments with their members

    for bod_member in bod_members:
        departments = set()  # To avoid duplicates
        for member in bod_member.members.all():
            department = member.department_name  # Assuming department_name exists in the Member model
            departments.add(department)  # Add department to the set
        departments_with_members.append({
            'bod_member': bod_member,
            'departments': list(departments),  # Convert set back to list
        })

    return render(request, 'bodmembers.html', {'bod_members': bod_members, 'departments_with_members': departments_with_members})
    

@login_required
def get_committee_users(request, department_id, member_id):
    if request.method == 'GET':
        members = Member.objects.filter(department_name_id=department_id).values('id', 'name', 'email', 'department_name__Department_name', 'image')
        return JsonResponse(list(members), safe=False)


@login_required
def get_notification(request, id):
    notification = get_object_or_404(Notifications, id=id)

    pdf_url = notification.pdf_file.url if notification.pdf_file else None
    if pdf_url:
        pdf_url = request.build_absolute_uri(pdf_url)

    image_url = notification.image.url if notification.image else None
    if image_url:
        image_url = request.build_absolute_uri(image_url)

    return JsonResponse({
        'title': notification.title,
        'description': notification.description,
        'file_url': pdf_url,
        'image_url': image_url,
    })
    print(notification.pdf_file.url)



from django.db.models import Case, When, IntegerField

@login_required
def view_member_details(request, id):
    bod_member = get_object_or_404(BODMember, id=id)
    members = bod_member.members.all().order_by(
     Case(
         When(designation_name__Designation_name='Chairman', then=0),
         default=1,
         output_field=IntegerField()
     ),
     'designation_name__Designation_name'
 )

    DEFAULT_IMAGE_URL = "/media/member_image/default.jpg"  # Adjust this path if needed
    return render(request, 'bodmembers_details.html', {'bod_member': bod_member, 'members': members, 'DEFAULT_IMAGE_URL': DEFAULT_IMAGE_URL})




def get_agendas(request):
    meeting_id = request.GET.get('meeting_id')
    if meeting_id:
        agendas = Agenda.objects.filter(add_meeting_id=meeting_id).values('id', 'title')
        return JsonResponse({'agendas': list(agendas)})
    else:
        return JsonResponse({'error': 'No meeting_id provided'}, status=400)


@staff_member_required
def auto_extract_meeting(request):
    """
    "Upload & Auto-Fill" workflow:
      Step 1 (POST 'document'): read the uploaded PDF/Word file, extract
        text, run the title/date/agenda parser, and show an editable
        preview form - nothing is saved yet.
      Step 2 (POST 'confirm'): create the BodMeeting + Agenda records from
        the (possibly hand-edited) preview form, and attach the original
        file to the meeting.
    """
    extracted = None

    if request.method == 'POST' and 'confirm' in request.POST:
        title = request.POST.get('title', '').strip() or 'Untitled Meeting'
        date_str = request.POST.get('date', '').strip() or None
        category_id = request.POST.get('category') or None
        agenda_titles = [t.strip() for t in request.POST.getlist('agenda_title') if t.strip()]

        meeting = BodMeeting(
            title=title,
            date=date_str,
            category_id=category_id,
            updated_by=request.user,
        )

        temp_path = request.session.get('auto_extract_temp_path')
        original_name = request.session.get('auto_extract_original_name', 'document.pdf')
        if temp_path and os.path.exists(temp_path):
            with open(temp_path, 'rb') as f:
                meeting.pdf.save(original_name, File(f), save=False)

        meeting.save()

        for agenda_title in agenda_titles:
            Agenda.objects.create(title=agenda_title, add_meeting=meeting)

        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        request.session.pop('auto_extract_temp_path', None)
        request.session.pop('auto_extract_original_name', None)

        messages.success(
            request,
            f'"{meeting.title}" created with {len(agenda_titles)} agenda item(s). '
            f'Open it in the admin to add discussion/decision details for each item.'
        )
        return redirect(f'/admin/Dashboard/bodmeeting/{meeting.id}/change/')

    elif request.method == 'POST':
        uploaded_file = request.FILES.get('document')
        if not uploaded_file:
            messages.error(request, 'Please choose a PDF or Word (.docx) file.')
        else:
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            if ext not in ('.pdf', '.docx'):
                messages.error(request, 'Only .pdf and .docx files are supported.')
            else:
                fd, temp_path = tempfile.mkstemp(suffix=ext)
                with os.fdopen(fd, 'wb') as f:
                    for chunk in uploaded_file.chunks():
                        f.write(chunk)
                try:
                    text = extract_text_from_file(temp_path)
                    if not text.strip():
                        messages.warning(
                            request,
                            "Couldn't read any text from that file (it may be a blank or "
                            "unreadable scan). You can still fill the form in manually below."
                        )
                        extracted = {"title": "", "date": "", "agenda_items": [], "discussion": "", "decision": "", "source": "none"}
                    else:
                        extracted = parse_meeting_document(text)
                    extracted['original_filename'] = uploaded_file.name
                    request.session['auto_extract_temp_path'] = temp_path
                    request.session['auto_extract_original_name'] = uploaded_file.name
                except Exception as e:
                    messages.error(request, f'Could not read that file: {e}')
                    os.remove(temp_path)

    categories = CommitteeType.objects.filter(is_active=True).order_by('order', 'name')
    return render(request, 'auto_extract_meeting.html', {
        'extracted': extracted,
        'categories': categories,
    })
