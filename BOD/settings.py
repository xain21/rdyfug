import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Environment-driven configuration -------------------------------------
# Secrets and environment-specific settings now live in a `.env` file next
# to manage.py (see .env.example for the template) instead of being
# hardcoded in this file. python-dotenv loads that file into os.environ if
# it's present; on a server where you set real environment variables
# instead of using a .env file, this is a harmless no-op.
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    # dotenv not installed yet (e.g. before `pip install -r requirements.txt`
    # has been re-run) - fall back to whatever is already in the real
    # environment / the hardcoded defaults below.
    pass

# Falls back to the old hardcoded key ONLY if no .env/environment variable
# is set, so nothing breaks immediately - but you should set
# DJANGO_SECRET_KEY in your .env for any real deployment.
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-pnyz(n%gd8^9%r+_pi6=483v3@r9$n@gvr)ybgaoihtmzuuf7#',
)

# Defaults to True (matches the previous behavior) so nothing breaks if you
# haven't set up a .env file yet. Set DJANGO_DEBUG=False in .env (or your
# real environment) before exposing this to anyone besides yourself.
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# Comma-separated list, e.g. DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,example.com
_default_allowed_hosts = 'localhost,127.0.0.1,172.16.17.100,172.16.17.168:1111,165.99.50.65,bod.wsspeshawar.org.pk:4003,bod.wsspeshawar.org.pk'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', _default_allowed_hosts).split(',')



INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "rest_framework",

    'Dashboard.apps.DashboardConfig',
    "api",
]

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'login'


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'BOD.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'Templates'),
            os.path.join(BASE_DIR, 'Dashboard', 'Templates'),
        ],
        # NOTE: Django's automatic APP_DIRS template discovery only looks
        # inside a folder literally named "templates" (lowercase) in each
        # app. This project's app templates live in "Dashboard/Templates"
        # (capital T), which only resolves on case-insensitive filesystems
        # (Windows/macOS default). On a case-sensitive filesystem - which
        # is what almost all Linux servers use, including typical
        # Gunicorn/Nginx deployments - APP_DIRS silently fails to find any
        # of these templates and EVERY page raises TemplateDoesNotExist.
        # Adding the explicit path above (which is not case-sensitive-loader
        # dependent) fixes this regardless of the OS, without renaming any
        # files.
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'BOD.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
AUTHENTICATION_BACKENDS = [
    "BOD.readonly_auth.ReadOnlyModelBackend",
]
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Karachi'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'  # Always start with a slash to serve it correctly
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]  # If you have custom static files in 'static' directory
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # Use staticfiles directory for production collection

# Media files (for user-uploaded content)
MEDIA_URL = '/media/'  # For serving media files
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')  # Path where media files are stored


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Debugging Static Files in Development

X_FRAME_OPTIONS = "SAMEORIGIN"
SILENCED_SYSTEM_CHECKS = ["security.W019"]

# --- Email (for "new meeting/document uploaded" notifications) ------------
# Defaults to printing emails to the console/log instead of actually
# sending anything, so this is safe out of the box and won't fail or need
# any setup for local development or a demo. To send real emails, set
# these in your .env (see .env.example) with your organization's SMTP
# details - nothing else in the code needs to change.
EMAIL_BACKEND = os.environ.get(
    'DJANGO_EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST = os.environ.get('DJANGO_EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('DJANGO_EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('DJANGO_EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('DJANGO_EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('DJANGO_EMAIL_USE_TLS', 'True') == 'True'
DEFAULT_FROM_EMAIL = os.environ.get('DJANGO_DEFAULT_FROM_EMAIL', 'noreply@bod-portal.local')

# A few extra hardening settings that only kick in once DEBUG=False, so they
# never interfere with local development.
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    CSRF_COOKIE_SECURE = os.environ.get('DJANGO_CSRF_COOKIE_SECURE', 'True') == 'True'
    SESSION_COOKIE_SECURE = os.environ.get('DJANGO_SESSION_COOKIE_SECURE', 'True') == 'True'
