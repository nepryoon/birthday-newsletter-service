"""
Configurazione principale per il progetto Django "birthday_newsletter".

Questo file contiene tutte le impostazioni necessarie per il funzionamento
del servizio di newsletter per compleanni, incluse le configurazioni per:
- Database SQLite locale
- Backend email (console, per sviluppo/test)
- Gestione task asincroni con django-tasks
- API REST con Django REST Framework
- Filtri, paginazione e permessi per le API
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Percorso base del progetto
# ---------------------------------------------------------------------------
# Costruisce i percorsi all'interno del progetto in questo modo:
# BASE_DIR / 'sotto-cartella'
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Sicurezza
# ---------------------------------------------------------------------------
# ATTENZIONE: mantieni la chiave segreta usata in produzione al sicuro e
# non condividerla mai. Usa variabili d'ambiente in produzione.
SECRET_KEY = "django-insecure-birthday-newsletter-secret-key-change-in-production"

# Non abilitare il debug in produzione!
DEBUG = True

ALLOWED_HOSTS: list[str] = []

# ---------------------------------------------------------------------------
# Applicazioni installate
# ---------------------------------------------------------------------------
# Elenco di tutte le applicazioni Django attive in questo progetto.
# - django.contrib.*: app predefinite di Django (admin, autenticazione, ecc.)
# - rest_framework: Django REST Framework per la gestione delle API REST
# - django_filters: filtri avanzati per le query delle API
# - django_tasks: gestione di task asincroni con salvataggio su database
# - newsletter: l'app principale del progetto per la gestione delle newsletter
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Librerie di terze parti
    "rest_framework",
    "django_filters",
    "django_tasks",
    "django_tasks.backends.database",
    # App del progetto
    "newsletter",
]

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
# Strati di elaborazione applicati ad ogni richiesta/risposta HTTP.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "birthday_newsletter.urls"

# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------
# Configurazione del sistema di template Django.
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "birthday_newsletter.wsgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# Configurazione del database SQLite locale.
# SQLite è ideale per lo sviluppo e i prototipi; in produzione si consiglia
# di passare a PostgreSQL o MySQL tramite variabili d'ambiente.
# Documentazione: https://docs.djangoproject.com/en/5.1/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ---------------------------------------------------------------------------
# Validazione delle password
# ---------------------------------------------------------------------------
# Regole per la validazione delle password degli utenti.
# Documentazione: https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators
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

# ---------------------------------------------------------------------------
# Internazionalizzazione
# ---------------------------------------------------------------------------
# Impostazioni per la lingua e il fuso orario del progetto.
# Documentazione: https://docs.djangoproject.com/en/5.1/topics/i18n/
LANGUAGE_CODE = "it-it"

# Fuso orario italiano (CET/CEST)
TIME_ZONE = "Europe/Rome"

USE_I18N = True

# Attiva il supporto ai fusi orari (datetime "aware") nel database e nel codice.
# Tutte le date/ore vengono salvate in UTC e convertite al fuso orario locale
# solo al momento della visualizzazione.
USE_TZ = True

# ---------------------------------------------------------------------------
# File statici (CSS, JavaScript, immagini)
# ---------------------------------------------------------------------------
# Documentazione: https://docs.djangoproject.com/en/5.1/howto/static-files/
STATIC_URL = "static/"

# ---------------------------------------------------------------------------
# Chiave primaria predefinita per i modelli
# ---------------------------------------------------------------------------
# Tipo di campo usato automaticamente come chiave primaria per i modelli
# che non la specificano esplicitamente.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Email Backend
# ---------------------------------------------------------------------------
# Backend email per lo sviluppo: stampa le email sulla console invece di
# inviarle realmente. Utile per test e sviluppo locale.
# In produzione, sostituire con un backend SMTP reale (es. SendGrid, AWS SES).
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Indirizzo email mittente predefinito usato per tutte le email in uscita.
DEFAULT_FROM_EMAIL = "newsletter@azienda.com"

# ---------------------------------------------------------------------------
# Django Tasks
# ---------------------------------------------------------------------------
# Configurazione per la gestione dei task asincroni tramite django-tasks.
# Il backend DatabaseBackend salva i task nel database SQLite, permettendo
# di monitorarne lo stato e rieseguirli in caso di errore.
# Documentazione: https://django-tasks.readthedocs.io/
TASKS = {
    "default": {
        "BACKEND": "django_tasks.backends.database.DatabaseBackend",
        "QUEUES": {
            "default": {},
        },
    }
}

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
# Configurazione per le API REST del progetto.
# Documentazione: https://www.django-rest-framework.org/api-guide/settings/
REST_FRAMEWORK = {
    # --- Backend di filtraggio ---
    # Permette di filtrare, cercare e ordinare i risultati delle API.
    # - DjangoFilterBackend: filtri per campo (es. ?nome=Mario)
    # - SearchFilter: ricerca testuale (es. ?search=Mario)
    # - OrderingFilter: ordinamento dei risultati (es. ?ordering=nome)
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    # --- Paginazione ---
    # LimitOffsetPagination permette al client di controllare quanti risultati
    # ricevere (limit) e da dove iniziare (offset).
    # Esempio: GET /api/iscritti/?limit=10&offset=20
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 20,
    # --- Permessi ---
    # AllowAny: accesso libero senza autenticazione richiesta.
    # Appropriato per un prototipo interno; in produzione usare permessi
    # più restrittivi (es. IsAuthenticated, IsAdminUser).
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}
