from django import forms
from django.contrib import admin
from .models import Department, Designation, Member, BodMeeting, Agenda, MinutesOfMeeting, Notifications, SubAgenda, Sub_sub_Agenda,Notification_Membors,BODMember,ActionLog, CommitteeType, ActionItem, DocumentAccessLog, DocumentVersion, DocumentSignature


@admin.register(CommitteeType)
class CommitteeTypeAdmin(admin.ModelAdmin):
    """
    This is the single admin screen an administrator needs to add, edit,
    enable/disable, or (safely) delete a committee/category. Anything saved
    here immediately becomes available across the whole site - homepage,
    upload/create forms, and search - with no further code changes.
    """
    list_display = ('name', 'slug', 'is_active', 'order', 'meeting_count', 'created_at')
    list_editable = ('is_active', 'order')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('order', 'name')
    readonly_fields = ('created_at', 'updated_at')

    def meeting_count(self, obj):
        return obj.meetings.count()
    meeting_count.short_description = 'Documents / Meetings'

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('Department_name',)
    search_fields = ('Department_name',)

@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
    list_display = ('Designation_name',)
    search_fields = ('Designation_name',)

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'designation_name', 'department_name', 'email', 'address', 'phone', 'image')
    search_fields = ('name', 'designation_name__name', 'department_name__name', 'email', 'address', 'phone')
    list_filter = ('designation_name', 'department_name')





class SubAgendaForm(forms.ModelForm):
    bod_meeting = forms.ModelChoiceField(
        queryset=BodMeeting.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="BOD Meeting"
    )

    class Meta:
        model = SubAgenda
        fields = ['bod_meeting', 'agenda', 'subagenda_title', 'subagenda_description', 'subagenda_descision', 'pdf']
        widgets = {
            'subagenda_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sub Agenda Title'}),
            'subagenda_description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Sub Agenda Description'}),
            'subagenda_descision': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Sub Agenda Decision'}),
            'pdf': forms.FileInput(attrs={'class': 'form-control', 'placeholder': 'PDF'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'bod_meeting' in self.data:
            try:
                meeting_id = int(self.data.get('bod_meeting'))
                self.fields['agenda'].queryset = Agenda.objects.filter(add_meeting_id=meeting_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['agenda'].queryset = self.instance.agenda.add_meeting.agendas.all()
        else:
            self.fields['agenda'].queryset = Agenda.objects.none()

class SubAgendaInline(admin.StackedInline):  # Use StackedInline for better clarity
    model = SubAgenda
    form = SubAgendaForm
    extra = 1

class AgendaInlineForm(forms.ModelForm):
    class Meta:
        model = Agenda
        fields = ['title', 'pdf']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control agenda-title', 'placeholder': 'Agenda Title'}),
            'pdf': forms.FileInput(attrs={'class': 'form-control', 'placeholder': 'Agenda PDF'}),
        }






class AgendaInline(admin.StackedInline):  # Use StackedInline for better clarity
    model = Agenda
    form = AgendaInlineForm
    extra = 1
    inlines = [SubAgendaInline]  # Nest SubAgendaInline inside AgendaInline


class ActionItemInline(admin.TabularInline):
    """Add/edit action items directly from the meeting's admin page."""
    model = ActionItem
    extra = 1
    fields = ('description', 'assigned_to', 'due_date', 'status')





@admin.register(BodMeeting)
class BodMeetingAdmin(admin.ModelAdmin):
    # This is the "upload/create" screen for meetings/documents. The
    # `category` field below is a plain dropdown populated from the
    # CommitteeType table - any category an admin adds there (e.g.
    # "IT Support") is automatically selectable here immediately.
    list_display = ('title', 'date', 'category', 'approval_status',)
    list_editable = ('approval_status',)
    search_fields = ('title', 'category__name',)
    list_filter = ('date', 'category', 'approval_status',)
    inlines = [AgendaInline, ActionItemInline]

    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'pdf', 'image', 'category', 'date',)
        }),
        ('Approval', {
            'fields': ('approval_status', 'approved_by', 'approved_at'),
            'description': 'Draft -> Reviewed -> Approved. Members can also change this from the meeting details page if they are staff/superuser.',
        }),
    )
    readonly_fields = ('approved_by', 'approved_at')

    class Media:
        js = ('//cdn.ckeditor.com/4.14.1/standard/ckeditor.js',)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['description'].widget.attrs['class'] = 'ckeditor form-control'
        return form

    def save_model(self, request, obj, form, change):
        obj._request = request  # Attach request to the object
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        obj._request = request  # Attach request to the object
        super().delete_model(request, obj)

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user  # Set the user making changes
        super().save_model(request, obj, form, change)

@admin.register(ActionItem)
class ActionItemAdmin(admin.ModelAdmin):
    """
    Cross-meeting view of every action item - a simple report an admin can
    filter by status/assignee/due date without opening each meeting.
    """
    list_display = ('description_short', 'meeting', 'assigned_to', 'due_date', 'status', 'overdue_flag')
    list_filter = ('status', 'meeting__category', 'assigned_to')
    search_fields = ('description', 'meeting__title', 'assigned_to__username')
    list_editable = ('status',)
    date_hierarchy = 'due_date'

    def description_short(self, obj):
        return (obj.description[:75] + '...') if len(obj.description) > 75 else obj.description
    description_short.short_description = 'Description'

    def overdue_flag(self, obj):
        return obj.is_overdue
    overdue_flag.short_description = 'Overdue?'
    overdue_flag.boolean = True


@admin.register(DocumentAccessLog)
class DocumentAccessLogAdmin(admin.ModelAdmin):
    """
    Read-only audit trail report: who viewed or downloaded which
    meeting/document, and when. Filter by action, category, user, or date.
    """
    list_display = ('timestamp', 'user', 'action', 'meeting', 'meeting_category', 'ip_address')
    list_filter = ('action', 'meeting__category', 'timestamp')
    search_fields = ('user__username', 'meeting__title', 'ip_address')
    date_hierarchy = 'timestamp'

    def meeting_category(self, obj):
        return obj.meeting.category.name if obj.meeting and obj.meeting.category_id else '-'
    meeting_category.short_description = 'Category'

    def has_add_permission(self, request):
        # This log is written automatically by the app; it shouldn't be
        # hand-edited or fabricated from Admin.
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    """Read-only: archived files are created automatically when a meeting's PDF is replaced."""
    list_display = ('meeting', 'version_number', 'uploaded_by', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('meeting__title',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(DocumentSignature)
class DocumentSignatureAdmin(admin.ModelAdmin):
    """Read-only: signatures are created by users signing from the meeting details page."""
    list_display = ('meeting', 'signed_name', 'user', 'signed_at', 'ip_address')
    list_filter = ('signed_at',)
    search_fields = ('meeting__title', 'signed_name', 'user__username')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class ActionLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'model_name', 'timestamp', 'instance_id')
    list_filter = ('action', 'model_name', 'user')
    search_fields = ('user__username', 'action', 'model_name', 'instance_id')
    ordering = ('-timestamp',)
    readonly_fields = ('timestamp',)  # Making timestamp read-only

admin.site.register(ActionLog, ActionLogAdmin)


class Sub_sub_AgendaInline(admin.StackedInline):
    model = Sub_sub_Agenda
    extra = 1




@admin.register(SubAgenda)
class SubAgendaAdmin(admin.ModelAdmin):
    list_display = ('short_subagenda_title', 'short_agenda', 'pdf','get_meeting_title', 'created_at')
    search_fields = ('subagenda_title', 'agenda__title','bod_meeting__title')
    list_filter = ('created_at', 'agenda__title','bod_meeting__title')

    fieldsets = (
        (None, {
            'fields': ('bod_meeting', 'agenda', 'pdf', 'subagenda_title', 'subagenda_description', 'subagenda_descision',)
        }),
    )

    inlines = [Sub_sub_AgendaInline]

    class Media:
        js = ('assets/js/admin_subagenda.js', 'https://cdn.ckeditor.com/4.14.1/standard/ckeditor.js')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['subagenda_description'].widget.attrs['class'] = 'ckeditor form-control'
        form.base_fields['subagenda_descision'].widget.attrs['class'] = 'ckeditor form-control'
        return form

    def short_subagenda_title(self, obj):
        return obj.subagenda_title[:30] + '...' if len(obj.subagenda_title) > 30 else obj.subagenda_title
    short_subagenda_title.short_description = 'SubAgenda Title'

    def short_agenda(self, obj):
        return obj.agenda.title[:30] + '...' if obj.agenda and len(obj.agenda.title) > 30 else obj.agenda.title
    short_agenda.short_description = 'Agenda'

    def get_meeting_title(self, obj):
        return obj.bod_meeting.title if obj.bod_meeting else 'No Meeting'
    get_meeting_title.short_description = 'Meeting Title'



class NotificationsForm(forms.ModelForm):
    class Meta:
        model = Notifications
        fields = ['member', 'title', 'from_date', 'to_date', 'description', 'image','pdf_file']
        widgets = {
            'from_date': forms.DateInput(attrs={'type': 'date'}),
            'to_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super(NotificationsForm, self).__init__(*args, **kwargs)
        chairman_designation = Designation.objects.get(Designation_name='Chairman')
        self.fields['member'].queryset = Member.objects.filter(designation_name=chairman_designation)


@admin.register(Notifications)
class NotificationsAdmin(admin.ModelAdmin):
    form = NotificationsForm
    list_display = ('title', 'member', 'from_date', 'to_date', 'created_at', 'updated_at')
    search_fields = ('title', 'member__name', 'description')
    list_filter = ('from_date', 'to_date', 'member')


@admin.register(Notification_Membors)
class NotificationMemborsAdmin(admin.ModelAdmin):
    list_display = ('user', 'member', 'created_at', 'updated_at')  # Show these fields in the admin list
    search_fields = ('user__name', 'member__title')  # Add search functionality
    list_filter = ('created_at', 'updated_at')  # Add filters for date fields


class MinutesOfMeetingInline(admin.TabularInline):
    model = MinutesOfMeeting
    extra = 1  # Number of inline forms initially displayed

@admin.register(MinutesOfMeeting)
class MinutesOfMeetingAdmin(admin.ModelAdmin):
    list_display = ('meeting', 'agenda', 'title', 'created_at')
    search_fields = ('title', 'meeting__title', 'agenda__title')
    list_filter = ('created_at', 'meeting__title', 'agenda__title')

    fieldsets = (
        (None, {
            'fields': ('bod_meeting', 'agenda', 'subagenda_title', 'subagenda_description', 'subagenda_descision', 'pdf')
        }),
    )

    class Media:
        js = (
            'https://cdn.ckeditor.com/4.16.0/standard/ckeditor.js',
            'admin/js/custom_admin.js',  # Add path to your custom JavaScript file
        )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['description'].widget.attrs['class'] = 'ckeditor form-control'
        form.base_fields['decision'].widget.attrs['class'] = 'ckeditor form-control'
        return form
class BODMemberAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'from_date', 'to_date']
    filter_horizontal = ('members',)  # Enable checkboxes for member selection

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "chairman":
            kwargs["queryset"] = Member.objects.filter(designation_name__Designation_name='Chairman')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(BODMember, BODMemberAdmin)



from .models import UserViewPermission

class UserViewPermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'view_name', 'can_view')  # Display these fields in the admin list view
    list_filter = ('user', 'view_name')  # Add filters for easier searching
    search_fields = ('user__username', 'view_name')  # Allow searching by username and view name
    ordering = ('user', 'view_name')  # Order by user and view name

admin.site.register(UserViewPermission, UserViewPermissionAdmin)
