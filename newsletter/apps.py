"""
Configurazione dell'app Django "newsletter".

Questo file definisce la classe di configurazione dell'app, che viene
referenziata da Django durante l'avvio del progetto.
"""

from django.apps import AppConfig


class NewsletterConfig(AppConfig):
    # Tipo di campo predefinito per le chiavi primarie auto-generate
    default_auto_field = "django.db.models.BigAutoField"

    # Nome dell'app usato da Django per identificarla nel progetto
    name = "newsletter"

    # Nome leggibile dell'app (usato nell'interfaccia di amministrazione)
    verbose_name = "Newsletter Compleanni"
