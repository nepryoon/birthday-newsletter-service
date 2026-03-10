"""
Registrazione dei modelli dell'app "newsletter" nel pannello di amministrazione Django.
"""

from django.contrib import admin

from .models import EmailTemplate, Employee, Office, SendLog, SendLogEntry, Team

admin.site.register(Office)
admin.site.register(Team)
admin.site.register(Employee)
admin.site.register(EmailTemplate)
admin.site.register(SendLog)
admin.site.register(SendLogEntry)
