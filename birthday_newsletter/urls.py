"""
Configurazione delle URL principali (root) per il progetto Django "birthday_newsletter".

Ogni path associa un prefisso URL a un insieme di URL definite in un'app o libreria specifica.
Documentazione: https://docs.djangoproject.com/en/5.1/topics/http/urls/
"""

from django.contrib import admin
from django.urls import include, path

# Importa il modulo API di django_tasks per la gestione dei task asincroni via database
from django_tasks.backends.database import api as tasks_api

urlpatterns = [
    # Pannello di amministrazione Django: interfaccia web per gestire i dati del progetto
    path("admin/", admin.site.urls),

    # API dell'app "newsletter": endpoint REST per iscritti, compleanni e invio email
    path("api/", include("newsletter.urls")),

    # API di django_tasks: endpoint per monitorare e gestire i task asincroni nel database
    path("tasks/", include(tasks_api)),
]
