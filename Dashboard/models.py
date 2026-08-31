from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify


DEFAULT_CATEGORY_ICON = 'assets/images/bodmeeting.svg'


class CommitteeType(models.Model):
    """
    Dynamic, admin-managed replacement for the old hardcoded committee/category
    list (AGM, HR, Finance, Audit, Procurement, ...).

    Creating a new row here (via Django Admin) is the ONLY thing required to add
    a brand-new committee/department/category to the whole application: the
    homepage, the upload/creation forms, and the search system all read from
    this table automatically. No Python/HTML/JS/URL changes are needed.
    """
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default=DEFAULT_CATEGORY_ICON,
        help_text="Static path to an icon shown on the homepage, e.g. assets/images/agm.svg",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only active categories are shown on the site, in upload forms, and in search.",
    )
    order = models.PositiveIntegerField(
        default=0, help_text="Lower numbers appear first on the homepage."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Committee Type'
        verbose_name_plural = 'Committee Types'
        ordering = ['order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or 'category'
            slug = base_slug
            counter = 1
            while CommitteeType.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
            self.slug = slug
        if not self.icon:
            self.icon = DEFAULT_CATEGORY_ICON
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


def committee_permission_choices():
    """
    Builds the list of selectable permission "views" dynamically from the
    active CommitteeType records, so UserViewPermission never needs code
    changes when a new category is added.
    """
    choices = [
        ('all_meetings', 'All Meetings (legacy)'),
    ]
    try:
        for committee in CommitteeType.objects.filter(is_active=True).order_by('order', 'name'):
            choices.append((f'list:{committee.slug}', f'{committee.name} - Meetings List'))
            choices.append((f'details:{committee.slug}', f'{committee.name} - Meeting Details'))
    except Exception:
        # Table may not exist yet during initial migrations.
        pass
    return choices


class Department(models.Model):
    Department_name = models.CharField(max_length=150)

    class Meta:
        verbose_name_plural = 'Departments'

    def __str__(self):
        return self.Department_name

class Designation(models.Model):
    Designation_name = models.CharField(max_length=150)

    class Meta:
        verbose_name_plural = 'Designations'

    def __str__(self):
        return self.Designation_name

class Member(models.Model):
    name = models.CharField(max_length=500, null=True, blank=True)
    designation_name = models.ForeignKey(Designation, on_delete=models.CASCADE)
    department_name = models.ForeignKey(Department, on_delete=models.CASCADE)
    short_intro = models.TextField(null=True, blank=True)
    email = models.EmailField(max_length=50, null=True, blank=True)
    address = models.CharField(max_length=150, null=True, blank=True)
    phone = models.CharField(max_length=150, null=True, blank=True)
    image = models.ImageField(upload_to='member_image/', null=True, blank=True)
    resume = models.FileField(upload_to='member_resumes/', null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Members'

    def __str__(self):
        return self.name
   
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name
    
    



class BodMeeting(models.Model):
    title = models.CharField(max_length=2000)
    description = models.TextField(blank=True, null=True)
    pdf = models.FileField(upload_to='meeting_pdfs/', blank=True, null=True)
    image = models.ImageField(upload_to='meeting_images/', blank=True, null=True)
    # Dynamic replacement for the old hardcoded `type` choices field.
    # Every existing document/meeting is linked to a CommitteeType record via
    # this FK. New categories created in Admin automatically become valid
    # choices here - no code changes required.
    category = models.ForeignKey(
        CommitteeType,
        on_delete=models.PROTECT,  # a category can't be deleted while meetings reference it
        related_name='meetings',
        null=True,
        blank=False,
    )
    # Kept (not deleted) for data-safety/audit purposes only. Old code used to
    # store the committee as a raw string here (e.g. "agm", "hr", "finance").
    # Existing values were migrated into `category` above; this column is no
    # longer read by the application.
    legacy_type = models.CharField(max_length=50, blank=True, null=True, editable=False)
    date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)  # Track the user making changes

    # --- Approval workflow -------------------------------------------------
    # Simple Draft -> Reviewed -> Approved status so minutes/documents don't
    # just "appear" once uploaded. Anyone with view access can still see the
    # document at any status; the status is a visible governance signal and
    # is changed from the meeting details page (staff/superuser only).
    APPROVAL_DRAFT = 'draft'
    APPROVAL_REVIEWED = 'reviewed'
    APPROVAL_APPROVED = 'approved'
    APPROVAL_STATUS_CHOICES = [
        (APPROVAL_DRAFT, 'Draft'),
        (APPROVAL_REVIEWED, 'Reviewed'),
        (APPROVAL_APPROVED, 'Approved'),
    ]
    approval_status = models.CharField(
        max_length=20, choices=APPROVAL_STATUS_CHOICES, default=APPROVAL_DRAFT,
        help_text="Visible review status for this meeting's minutes/documents.",
    )
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_meetings',
        help_text="Who last moved this to 'Reviewed' or 'Approved'.",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    @property
    def type(self):
        """
        Backward-compatible accessor for any code/templates still reading
        `meeting.type`. Prefer `meeting.category` going forward.
        """
        return self.category.slug if self.category_id else self.legacy_type

    def save(self, *args, **kwargs):
        # --- Document versioning ------------------------------------------
        # If this is an update to an existing meeting AND the attached PDF
        # is being replaced, archive the outgoing file as a DocumentVersion
        # before it's overwritten, instead of just losing it. The old file
        # is already sitting in storage under its old path, so this simply
        # "adopts" that path into a version record - no extra file copy.
        if self.pk:
            try:
                old = BodMeeting.objects.get(pk=self.pk)
            except BodMeeting.DoesNotExist:
                old = None
            old_name = old.pdf.name if (old and old.pdf) else None
            new_name = self.pdf.name if self.pdf else None
            if old_name and old_name != new_name:
                last_version = self.document_versions.order_by('-version_number').first()
                next_version_number = (last_version.version_number + 1) if last_version else 1
                DocumentVersion.objects.create(
                    meeting=self,
                    file=old_name,
                    version_number=next_version_number,
                    uploaded_by=old.updated_by,
                )

        if self.updated_by:  # Check if the user is set
            if not self.pk:  # If the instance is being created
                ActionLog.objects.create(
                    user=self.updated_by,
                    action='create',
                    instance_id=str(self.id),  # Use the instance ID
                    model_name=self.__class__.__name__,  # Correctly reference the model name
                )
            else:  # Log update
                ActionLog.objects.create(
                    user=self.updated_by,
                    action='update',
                    instance_id=str(self.id),  # Use the instance ID
                    model_name=self.__class__.__name__,  # Correctly reference the model name
                )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.updated_by:  # Check if the user is set
            ActionLog.objects.create(
                user=self.updated_by,
                action='delete',
                instance_id=str(self.id),  # Use the instance ID
                model_name=self.__class__.__name__,  # Correctly reference the model name
            )
        super().delete(*args, **kwargs)

    def __str__(self):  # Corrected from _str_ to __str__
        return f"{self.title}"

class ActionLog(models.Model):
    # Was previously required (no null allowed), which caused deletes/updates
    # to crash with "NOT NULL constraint failed" whenever a BodMeeting had no
    # `updated_by` user saved on it (e.g. old/demo records). Now allows a
    # blank user instead of blocking the action entirely.
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50)  # e.g., 'create', 'update', 'delete'
    timestamp = models.DateTimeField(auto_now_add=True)
    instance_id = models.CharField(max_length=100)  # ID of the updated/deleted instance
    model_name = models.CharField(max_length=100)  # Name of the model

    def __str__(self):  # Corrected from _str_ to __str__
        return f"{self.user} {self.action} {self.model_name} at {self.timestamp}"


class Agenda(models.Model):
    title = models.TextField(max_length=2000)
    attachment_1 = models.FileField(upload_to='attachments/', blank=True, null=True)
    pdf = models.FileField(upload_to='pdfs/', blank=True, null=True, default=None)  # Add default here
    add_meeting = models.ForeignKey(BodMeeting, on_delete=models.CASCADE, related_name='agendas')

    class Meta:
        verbose_name_plural = 'AddAgendas'

    def __str__(self):
        return self.title
    



class SubAgenda(models.Model):
    bod_meeting = models.ForeignKey(BodMeeting, on_delete=models.CASCADE, related_name='sub_agendas', null=True, blank=True)
    agenda = models.ForeignKey(Agenda, on_delete=models.CASCADE, related_name='sub_agendas')
    subagenda_title = models.TextField(blank=True, null=True)
    subagenda_description = models.TextField(blank=True, null=True)
    subagenda_descision = models.TextField(blank=True, null=True)
    pdf = models.FileField(upload_to='subagenda_pdfs/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.subagenda_title if self.subagenda_title else 'SubAgenda'
    



class Sub_sub_Agenda(models.Model):
    subagenda_title = models.TextField(blank=True, null=True) 
    subagenda_description = models.TextField(blank=True, null=True)
    subagenda_descision = models.TextField(blank=True, null=True)
     # Add default here
    sub_sub_agenda = models.ForeignKey(SubAgenda, on_delete=models.CASCADE, related_name='agendas')

    class Meta:
        verbose_name_plural = 'Sub_sub_Agenda'



class Notifications(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    title = models.CharField(max_length=255)
    from_date = models.DateField()
    to_date = models.DateField()
    description = models.TextField(null=True, blank=True)
    image = models.ImageField(upload_to='notifications/', null=True, blank=True)
    pdf_file = models.FileField(upload_to='notifications/pdfs/', null=True, blank=True)  # New PDF field
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class BODMember(models.Model):
    chairman = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='bod_members')
    notification = models.ForeignKey(Notifications, on_delete=models.CASCADE, related_name='bod_member_notifications', null=True, blank=True)
    title = models.CharField(max_length=255)
    from_date = models.DateField()
    to_date = models.DateField()
    members = models.ManyToManyField(Member, related_name='selected_members')  # Add this for multiple members
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    

class Notification_Membors(models.Model):
    user = models.ForeignKey(Member, on_delete=models.CASCADE)
    member = models.ForeignKey(Notifications, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class MinutesOfMeeting(models.Model):
    meeting = models.ForeignKey(BodMeeting, on_delete=models.CASCADE, related_name='minutes_of_meetings')
    agenda = models.ForeignKey(Agenda, on_delete=models.CASCADE, related_name='minutes_of_meetings')
    title = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    decision = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title if self.title else 'Minutes of Meeting'


from django.db import models
from django.contrib.auth.models import User


class UserViewPermission(models.Model):
    # The dropdown of selectable "views" is generated dynamically from the
    # active CommitteeType records (see committee_permission_choices above),
    # so a brand-new category automatically gets its own list/details
    # permission entries here without any code change.
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    view_name = models.CharField(max_length=100, choices=committee_permission_choices)
    can_view = models.BooleanField(default=False)  # Permission flag (True if the user can view this view)

    def __str__(self):
        # Display the user, the readable view name, and the permission status
        return f"{self.user.username} - {self.get_view_name_display()} - {'Can View' if self.can_view else 'Cannot View'}"


class DocumentAccessLog(models.Model):
    """
    Audit trail: records who viewed a meeting's details page or downloaded
    its attached PDF, and when. Read this from Django Admin -> Document
    Access Logs (filterable by user, meeting, category, and date).
    """
    ACTION_CHOICES = [
        ('view', 'Viewed details'),
        ('download', 'Downloaded PDF'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='document_access_logs')
    meeting = models.ForeignKey(BodMeeting, on_delete=models.CASCADE, null=True, blank=True, related_name='access_logs')
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, default='view')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Document Access Log'
        verbose_name_plural = 'Document Access Logs'

    def __str__(self):
        who = self.user.username if self.user else 'Unknown user'
        what = self.meeting.title if self.meeting else 'Unknown document'
        return f"{who} {self.get_action_display()} '{what}' at {self.timestamp:%Y-%m-%d %H:%M}"


class ActionItem(models.Model):
    """
    A decision/action item captured from a meeting: what needs to happen,
    who owns it, by when, and its current status. Managed from Admin ->
    Action Items, or inline while editing a BOD Meeting.
    """
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ]

    meeting = models.ForeignKey(BodMeeting, on_delete=models.CASCADE, related_name='action_items')
    description = models.TextField()
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_action_items')
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['status', 'due_date']

    def __str__(self):
        owner = f" - {self.assigned_to.username}" if self.assigned_to else ""
        return f"{self.description[:60]}{owner} [{self.get_status_display()}]"

    @property
    def is_overdue(self):
        if not self.due_date or self.status == 'done':
            return False
        return self.due_date < timezone.now().date()


class DocumentVersion(models.Model):
    """
    Archived, previously-attached PDF for a meeting, kept when a newer file
    is uploaded over it instead of silently overwriting/losing the old one.
    Created automatically from BodMeeting.save() - never created by hand.
    """
    meeting = models.ForeignKey(BodMeeting, on_delete=models.CASCADE, related_name='document_versions')
    file = models.FileField(upload_to='meeting_pdfs/', max_length=500)
    version_number = models.PositiveIntegerField()
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=255, blank=True, default='Superseded by a newer upload')

    class Meta:
        ordering = ['-version_number']
        verbose_name = 'Document Version'
        verbose_name_plural = 'Document Versions'
        unique_together = ('meeting', 'version_number')

    def __str__(self):
        return f"{self.meeting.title} — v{self.version_number}"


class DocumentSignature(models.Model):
    """
    Lightweight internal e-signature: a logged-in user typing their name to
    formally confirm they've reviewed/signed off on a meeting's minutes,
    recorded with a timestamp and IP address for the audit trail.

    This is an internal sign-off record, not a certified/legally-binding
    digital signature service (no cryptographic signing or third-party
    identity verification) - appropriate for internal board governance,
    not for documents needing legal e-signature compliance (e.g. eIDAS/ESIGN).
    """
    meeting = models.ForeignKey(BodMeeting, on_delete=models.CASCADE, related_name='signatures')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='document_signatures')
    signed_name = models.CharField(max_length=255, help_text="Typed full name at the time of signing.")
    signed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        unique_together = ('meeting', 'user')
        ordering = ['signed_at']
        verbose_name = 'Document Signature'
        verbose_name_plural = 'Document Signatures'

    def __str__(self):
        return f"{self.signed_name} signed '{self.meeting.title}' on {self.signed_at:%Y-%m-%d}"
