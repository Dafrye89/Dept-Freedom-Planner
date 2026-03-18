import os
from pathlib import Path

import environ


AZURE_DEFAULT_HOSTNAME = "debt-freedom-planner-fgfxd3daanaud0fc.centralus-01.azurewebsites.net"
AZURE_DEFAULT_HTTPS_URL = f"https://{AZURE_DEFAULT_HOSTNAME}"


def env_bool(name: str, default: bool) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _clean_list(values):
    cleaned = []
    for value in values:
        if not value:
            continue
        normalized = str(value).strip()
        if normalized:
            cleaned.append(normalized)
    return cleaned


def _unique(values):
    seen = set()
    ordered = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


BASE_DIR = Path(__file__).resolve().parent.parent
WEBSITE_HOSTNAME = os.environ.get("WEBSITE_HOSTNAME", "").strip()
RUNNING_ON_AZURE = bool(WEBSITE_HOSTNAME)
env = environ.Env(
    ALLOWED_HOSTS=(list, ["127.0.0.1", "localhost", "testserver"]),
    CSRF_TRUSTED_ORIGINS=(list, []),
    APP_BASE_URL=(str, AZURE_DEFAULT_HTTPS_URL),
    AZURE_SQLITE_DIR=(str, "/home/data/debt_freedom_planner"),
    GOOGLE_CLIENT_ID=(str, ""),
    GOOGLE_CLIENT_SECRET=(str, ""),
    DEFAULT_FROM_EMAIL=(str, "noreply@debtfreedomplanner.local"),
    EMAIL_BACKEND=(str, "django.core.mail.backends.console.EmailBackend"),
    BOOTSTRAP_SUPERUSER_USERNAME=(str, "dafrye89"),
    BOOTSTRAP_SUPERUSER_PASSWORD=(str, "DafHef_04!"),
    BOOTSTRAP_SUPERUSER_EMAIL=(str, "dafrye89@local.test"),
)
environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env_bool("DEBUG", not RUNNING_ON_AZURE)
SECRET_KEY = env(
    "SECRET_KEY",
    default="django-insecure-debt-freedom-planner-local-only-secret-key",
)
APP_BASE_URL = env("APP_BASE_URL").rstrip("/")
APP_BASE_HOST = APP_BASE_URL.split("://", 1)[-1].split("/", 1)[0]
AZURE_SQLITE_DIR = Path(env("AZURE_SQLITE_DIR"))
if RUNNING_ON_AZURE:
    AZURE_SQLITE_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_DATABASE_URL = (
    f"sqlite:///{AZURE_SQLITE_DIR / 'db.sqlite3'}"
    if RUNNING_ON_AZURE
    else f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
)

configured_allowed_hosts = _clean_list(env("ALLOWED_HOSTS"))
runtime_allowed_hosts = _clean_list(
    [
        AZURE_DEFAULT_HOSTNAME,
        APP_BASE_HOST,
        WEBSITE_HOSTNAME,
    ]
)
ALLOWED_HOSTS = _unique(configured_allowed_hosts + runtime_allowed_hosts)

configured_csrf_trusted_origins = _clean_list(env("CSRF_TRUSTED_ORIGINS"))
runtime_csrf_trusted_origins = _clean_list(
    [
        APP_BASE_URL,
        AZURE_DEFAULT_HTTPS_URL,
        f"https://{WEBSITE_HOSTNAME}" if WEBSITE_HOSTNAME else "",
    ]
)
CSRF_TRUSTED_ORIGINS = _unique(configured_csrf_trusted_origins + runtime_csrf_trusted_origins)

GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET")
GOOGLE_LOGIN_ENABLED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")
EMAIL_BACKEND = env("EMAIL_BACKEND")
BOOTSTRAP_SUPERUSER_USERNAME = env("BOOTSTRAP_SUPERUSER_USERNAME")
BOOTSTRAP_SUPERUSER_PASSWORD = env("BOOTSTRAP_SUPERUSER_PASSWORD")
BOOTSTRAP_SUPERUSER_EMAIL = env("BOOTSTRAP_SUPERUSER_EMAIL")
DATABASE_URL = env("DATABASE_URL", default=DEFAULT_DATABASE_URL)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "core",
    "accounts",
    "plans",
    "calculator",
    "exports",
    "legal",
    "billing",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": False,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.app_access",
            ],
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


DATABASES = {"default": env.db("DATABASE_URL", default=DATABASE_URL)}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Chicago"

USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}
WHITENOISE_USE_FINDERS = DEBUG
WHITENOISE_AUTOREFRESH = DEBUG

AUTH_USER_MODEL = "accounts.CustomUser"
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

LOGIN_REDIRECT_URL = "plans:dashboard"
LOGOUT_REDIRECT_URL = "core:home"
LOGIN_URL = "account_login"

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_USER_MODEL_USERNAME_FIELD = "username"
ACCOUNT_USER_MODEL_EMAIL_FIELD = "email"
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https" if APP_BASE_URL.startswith("https://") or not DEBUG else "http"
ACCOUNT_ADAPTER = "accounts.adapter.PlannerAccountAdapter"

SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_STORE_TOKENS = False
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "APP": {
            "client_id": GOOGLE_CLIENT_ID,
            "secret": GOOGLE_CLIENT_SECRET,
            "key": "",
        },
    }
}

EMAIL_SUBJECT_PREFIX = "[Debt Freedom Planner] "

MESSAGE_TAGS = {
    10: "info",
    20: "success",
    25: "warning",
    30: "danger",
    40: "danger",
}

WEASYPRINT_BASEURL = BASE_DIR

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": LOGS_DIR / "app.log",
            "formatter": "standard",
        },
        "error_file": {
            "class": "logging.FileHandler",
            "filename": LOGS_DIR / "error.log",
            "formatter": "standard",
            "level": "ERROR",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": True,
        },
        "debt_freedom_planner": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
X_FRAME_OPTIONS = "SAMEORIGIN"
