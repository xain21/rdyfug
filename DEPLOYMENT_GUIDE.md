# DEPLOYMENT GUIDE — Update 2: E-Signatures, Calendar, Document Versioning

Added on top of Update 1 below (approval workflow, action items page,
activity log page, homepage stats, email notifications, role groups).
PostgreSQL migration was intentionally skipped per request.

| Feature | What it does | Where |
|---|---|---|
| **Document versioning** | If a meeting's PDF is replaced with a new upload, the old file is automatically kept (not deleted) and listed as a downloadable prior version on the meeting page. Fully automatic — nothing to configure. | `models.py` (`DocumentVersion`, hooked into `BodMeeting.save()`), meeting details page |
| **E-signatures** | Logged-in users can type their name to formally sign off on a meeting's minutes; recorded with timestamp and IP. This is an internal audit-trail sign-off, not a certified/legally-binding e-signature service (no cryptographic signing or ID verification) — appropriate for internal board sign-off, not for anything requiring legal e-signature compliance. | `models.py` (`DocumentSignature`), `/meeting/<id>/sign/`, meeting details page |
| **Calendar** | Month-view calendar of all meetings with previous/next navigation, plus a "Add to Calendar (.ics)" button on each meeting to add it to Outlook/Google/phone calendars. | `/calendar/`, `meetings_calendar.html`, `/meeting/<id>/ical/` |

### How to run this update
1. Back up `db.sqlite3` again.
2. Copy over the changed files: `models.py`, `views.py`, `urls.py`,
   `admin.py`, `Dashboard/templatetags/custom_filters.py`, the new
   `meetings_calendar.html`, and the edited `meeting_details.html`/`header.html`.
3. Run: `python manage.py migrate` (applies migration `0042`).
4. Restart the server.

Nothing here changes existing URLs or removes any data — all additive, and
tested against a copy of your database before being handed back.

---

# DEPLOYMENT GUIDE — Update: Governance Features + Critical Template Fix

## ⚠️ Critical fix in this update — read this first
Your app templates live in `Dashboard/Templates/` (capital T). Django's
automatic template discovery only looks inside a folder literally named
`templates` (lowercase). This happens to still work on Windows/macOS
because their filesystems ignore letter case, but **on a case-sensitive
Linux server — which is what almost every real Django hosting setup
(Gunicorn/Nginx, PythonAnywhere, etc.) uses — every single page in this
app would fail with `TemplateDoesNotExist`.** If you've only ever run this
with `python manage.py runserver` on your own Windows PC, you would never
have seen this. This update adds an explicit path in `BOD/settings.py` so
it now works regardless of OS, without renaming any of your existing files.
**Make sure this fix is included before you deploy to any Linux server.**

## What's new in this update
Added on top of the previous dynamic-category refactor, based on the
roadmap in `docs/BOD_Portal_Improvement_Roadmap.pdf`:

| Feature | What it does | Where |
|---|---|---|
| **Approval workflow** | Every meeting now has a Draft → Reviewed → Approved status, changeable by staff/superuser from the meeting details page or Admin. | `models.py` (`BodMeeting.approval_status`), `meeting_details.html` |
| **Action Items page** | Front-end list of all action items (previously admin-only), filterable by status/"assigned to me", with inline status updates. | `/action-items/`, `action_items.html` |
| **Activity Log page** | Front-end, filterable version of the document access audit trail (previously admin-only). Staff/superuser only. | `/activity-log/`, `activity_log.html` |
| **Homepage stats** | Meetings this month, open action items (with overdue count), and pending approvals now show on the homepage. | `views.py: view_home`, `homepage.html` |
| **Email notifications** | Emails everyone with view access to a category when a new meeting/document is added to it. Prints to console until you set real SMTP details in `.env` — see `.env.example`. | `signals.py`, `settings.py` |
| **Role groups** | Three reusable Django Groups (`Committee Member`, `Committee Chair`, `Admin`) created automatically via migration, ready to assign permissions to from Admin → Groups instead of configuring every user by hand. | migration `0041_committee_role_groups.py` |

### How to run this update
1. Back up `db.sqlite3` first (as always).
2. Copy over the changed files (`models.py`, `views.py`, `urls.py`,
   `admin.py`, `signals.py`, `settings.py`, the two new templates, and the
   edited `homepage.html`/`meeting_details.html`/`header.html`).
3. Run: `python manage.py migrate` (applies migrations `0040` and `0041`).
4. Restart the server.

Nothing here changes existing URLs, templates, or data — every addition is
additive, and this was tested against a copy of your `db.sqlite3` before
being handed back to you.

### Still open from the roadmap (not done in this pass)
Role-based permissions currently only creates the three Groups — it
doesn't yet wire specific page-level permissions to them (that's a bigger
change to `decorators.py` and would need you to confirm exactly what each
role should and shouldn't see). PostgreSQL migration, e-signatures,
calendar integration, and document versioning are still not started —
flag if you want any of those prioritized next.

---

# DEPLOYMENT GUIDE — Dynamic Committee/Category Refactor

This zip is your **complete Django project** (`manage.py`, `BOD/` project
settings, `Dashboard/` app, `api/` app, `media/`, `static/`, `db.sqlite3`,
`requirements.txt`, etc.) with the dynamic-category refactor already
applied to the source code. It is NOT a fresh rebuild — every file below
that isn't listed as changed is byte-for-byte identical to what you
uploaded.

`db.sqlite3` is your **original, untouched database** — the new migrations
are included as files but have not been run yet. You (or I, in a follow-up
if you re-upload after running it) still need to run `migrate`.

---

## Option 1: Just use this zip
1. Stop your current running server.
2. Back up your current project folder (especially `db.sqlite3` and
   `media/`) somewhere safe.
3. Unzip this package and replace your project folder with it entirely
   (or copy `manage.py`, `BOD/`, `Dashboard/`, `api/` from this zip over
   your existing project — `media/`, `static/`, `db.sqlite3` are included
   here too but are unchanged from what you uploaded, so it's safe to keep
   your own copies of those instead if you've added files since uploading).
4. Recreate your virtualenv (this zip does not include `venv/` — see
   "Installation steps" below).
5. Run the migration commands in "How to run the migration" below.

## Option 2: Patch your existing project by hand
If you'd rather edit your existing project in place instead of swapping
the whole folder, here is the exact, complete list of changes.

### Files to REPLACE (full file contents changed)
| File | What changed |
|---|---|
| `Dashboard/models.py` | Added `CommitteeType` model; changed `BodMeeting.type` → `BodMeeting.category` (FK), old field kept as `legacy_type`; `UserViewPermission.view_name` choices are now generated dynamically |
| `Dashboard/views.py` | Replaced ~10 duplicated per-committee view functions with 3 generic ones (`category_meetings`, `category_search`, `meeting_details`); `view_home` now passes `categories` to the template; `search` now scopes to active categories and includes category name in PDF results |
| `Dashboard/urls.py` | All old URL *names* kept (still resolve, now point at the generic views); new `committee/<slug:category_slug>/` and `committee/<slug:category_slug>/search/` routes added |
| `Dashboard/admin.py` | Added `CommitteeTypeAdmin`; `BodMeetingAdmin` now uses a `category` dropdown instead of the hardcoded `type` field |
| `Dashboard/decorators.py` | Added `category_permission_required` (dynamic, slug-based); old `view_permission_required` kept as-is for anything still using it |

### Files to ADD (new files)
| File |
|---|
| `Dashboard/migrations/0033_committeetype_and_category_fk.py` |
| `Dashboard/migrations/0034_migrate_legacy_types_to_committeetype.py` |
| `Dashboard/migrations/0035_require_category_going_forward.py` |
| `Dashboard/Templates/category_meetings.html` |

### Files to REPLACE (templates, content changed but same filename)
| File | What changed |
|---|---|
| `Dashboard/Templates/meeting_details.html` | `{{ meeting.type }}` → `{{ meeting.category.name }}`; now used generically for every category |
| `Dashboard/Templates/search_results.html` | `{{ ....type }}` references → `{{ ....category.name }}`; PDF results now show category name |
| `Dashboard/Templates/homepage.html` | The 6 hardcoded category cards replaced with a `{% for category in categories %}` loop (same CSS/markup) |

### Files to DELETE (now redundant — content was merged above)
```
Dashboard/Templates/agm_meeting.html
Dashboard/Templates/hr_meeting.html
Dashboard/Templates/fn_meeting.html
Dashboard/Templates/audit_meeting.html
Dashboard/Templates/pro_meeting.html
Dashboard/Templates/all_meetings.html
Dashboard/Templates/hrmeeting_details.html
Dashboard/Templates/fnmeeting_details.html
Dashboard/Templates/auditmeeting_details.html
Dashboard/Templates/promeeting_details.html
```

### Files NOT changed
Everything else in your project is untouched, including (non-exhaustive):
`BOD/settings.py`, `BOD/urls.py`, `BOD/wsgi.py`, `BOD/asgi.py`, `manage.py`,
`Dashboard/utils.py` (OCR logic — already generic, no change needed),
`Dashboard/signals.py`, `Dashboard/custom_filters.py`,
`Dashboard/templatetags/`, `Dashboard/management/commands/seed.py`,
`Dashboard/Templates/header.html`, `index.html`, `login.html`,
`bodmembers.html`, `bodmembers_details.html`, `forbidden.html`, `api/*`,
all of `static/` and `media/`.

---

## Installation steps
This zip does not include a `venv/` folder (it's environment-specific and
was too large to ship). On the target machine:

```bash
cd BOD
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

Your `requirements.txt` already lists everything needed
(`Django==5.1.2`, `PyMuPDF`, `pytesseract`, `pillow`, etc.) — nothing new
was added by this refactor.

You also still need Tesseract OCR installed on the machine itself (not a
pip package) — `Dashboard/utils.py` currently points at a hardcoded path:
```python
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```
This is unrelated to this refactor (it was already there) — just confirm
that path is correct on whichever machine you deploy to.

## How to run the migration
**Back up `db.sqlite3` first.**

```bash
python manage.py makemigrations --check --dry-run   # should print "No changes detected"
python manage.py migrate
```

Then start the server as usual (`python manage.py runserver`) and log in.

## What the migration does to your existing data
- Creates `CommitteeType` rows for your existing committees: AGM, HR
  Committee, Finance Committee, Audit Committee, Procurement Committee,
  BOD Meetings.
- Every existing `BodMeeting` row is linked to the matching new
  `CommitteeType` via the new `category` field (based on its old `type`
  value, which is preserved, untouched, in a renamed `legacy_type` column
  — nothing is deleted).
- Every existing `UserViewPermission` grant is remapped to the new
  permission-name scheme (e.g. `'hr_meetings'` → `'list:hr'`) so no one
  loses access they had before.
- No PDFs, images, dates, titles, descriptions, users, or record IDs are
  touched or deleted.
- The migration is reversible (`python manage.py migrate Dashboard 0032`
  would undo it) if you need to roll back.

## Verifying the "success test" from your original request
1. Django Admin → **Committee Types** → Add → Name: `IT Support` → Save.
2. Open the homepage — "IT Support" appears automatically, no code change.
3. Django Admin → **BOD Meetings** → Add → pick `IT Support` from the
   `category` dropdown, attach a PDF, Save.
4. Click the new "IT Support" homepage card (or visit
   `/committee/it-support/`) — the meeting/document appears.
5. Use the homepage search box for text from that PDF — found via normal
   PDF text extraction, or via Tesseract OCR if the text only exists
   inside a scanned image (both already run on every page, for every
   category, automatically).
6. Repeat step 1–4 with a `Legal Committee` category — again with zero
   code changes.

## New: Search mode toggle (Text-only vs Text + OCR)
The site-wide PDF search box on the homepage now has two radio options:
- **Text only** — searches only the normal, selectable text inside each PDF.
  Skips Tesseract OCR entirely, so it's noticeably faster.
- **Text + OCR (scanned pages)** — the original behavior: searches normal
  PDF text *and* runs OCR on every page to also catch text that only exists
  inside a scanned image. Slower, but thorough. This is still the default.

No schema/migration changes were needed for this — it's a `views.search` +
`Dashboard/utils.py` change (`process_page_ocr` now takes a `use_ocr` flag)
plus a small addition to the homepage search form. Per-category search
boxes (inside a committee page) only ever searched database fields, not
PDFs, so they're unaffected.

## Also included: migration 0036
A small extra migration (`0036_alter_committeetype_id_and_more.py`) is
included to clear a harmless `makemigrations --check` warning some of you
saw on Django 6 (an `id` field default difference + re-recording the
dynamic `view_name` choices function). It changes no real data.

## New: three roadmap items implemented

### 1. Debug mode + secret key moved to environment variables
- `BOD/settings.py` now reads `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, and
  two cookie-security flags from environment variables (via a `.env` file),
  with the exact same values as before as fallback defaults - **nothing
  changes in how the app behaves until you edit `.env`.**
- A ready-to-use `.env` file is included at the project root (same folder
  as `manage.py`) with a freshly generated secret key and `DJANGO_DEBUG=True`
  (matching current behavior). **Before letting anyone besides yourself use
  this, edit `.env` and set `DJANGO_DEBUG=False`.**
- `.env.example` documents every variable. Treat `.env` as a secret - don't
  commit it to git or share it; generate a new key for each real environment
  with:
  ```
  python -c "import secrets; print(secrets.token_urlsafe(50))"
  ```
- New dependency: `python-dotenv==1.0.1` (added to `requirements.txt`) -
  run `pip install -r requirements.txt` again after pulling this update.

### 2. Document access audit trail
- New `DocumentAccessLog` model records every time someone opens a
  meeting's details page (`action='view'`) or downloads its PDF
  (`action='download'`), who did it, and when (plus their IP address).
- PDF download links now go through a small proxy view
  (`download_meeting_pdf`) so the download can be logged before redirecting
  to the actual file - visually identical to before, just trackable now.
- View the report in Django Admin → **Document Access Logs**. It's
  filterable by action, category, and date, and searchable by user/meeting/
  IP. It's intentionally read-only there (the log should only ever be
  written by the app itself, not hand-edited).

### 3. Action item tracking
- New `ActionItem` model: description, assigned-to user, due date, status
  (Open / In Progress / Done), linked to a specific meeting.
- Add them directly while editing a meeting in Django Admin → **BOD
  Meetings** (a new inline section, right under the Agendas section) - no
  separate screen needed for the common case.
- Django Admin → **Action Items** gives a flat, filterable report across
  every meeting (filter by status/category/assignee, sorted by due date),
  with an "Overdue?" column.
- A meeting's action items are now also shown directly on its details page
  in the app itself, with a status badge and an "Overdue" flag for anyone
  viewing that meeting - not just in Admin.

### Migration for this update
One new migration: `0037_documentaccesslog_actionitem.py` (creates the two
new tables only - doesn't touch any existing data). Run the usual:
```
python manage.py migrate
```

## Known limitation of this session
I don't have network/package-install access in the sandbox I worked in, so
I was not able to actually run `makemigrations`/`migrate`/`runserver`
against a live Django install here — everything was hand-verified against
your original code and syntax-checked with `python -m py_compile`, but
**you must run `makemigrations --check --dry-run` and `migrate` yourself**
before trusting this in production. If `--check` reports any unexpected
differences, send me the output and I'll fix it.
