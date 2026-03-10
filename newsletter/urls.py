"""
Configurazione delle URL dell'app "newsletter".

Registra tutti i ViewSet tramite il DefaultRouter di DRF che genera
automaticamente gli endpoint standard (list, create, retrieve, update,
partial_update, destroy) per ogni ViewSet. Le APIView custom vengono
aggiunte manualmente alla lista urlpatterns.

Endpoint generati dal router:
    /api/offices/                        – OfficeViewSet (CRUD)
    /api/teams/                          – TeamViewSet (CRUD)
    /api/employees/                      – EmployeeViewSet (CRUD)
    /api/employees/birthdays-today/      – action custom (festeggiati oggi)
    /api/templates/                      – EmailTemplateViewSet (CRUD)
    /api/templates/{id}/set-default/     – action custom (imposta predefinito)
    /api/send-logs/                      – SendLogViewSet (sola lettura)

Endpoint aggiuntivi (APIView custom):
    /api/newsletter/trigger/             – TriggerNewsletterView (POST)
    /api/newsletter/celebrants-today/    – TodaysCelebrantsView (GET)
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    EmailTemplateViewSet,
    EmployeeViewSet,
    OfficeViewSet,
    SendLogViewSet,
    TeamViewSet,
    TodaysCelebrantsView,
    TriggerNewsletterView,
)

# Namespace dell'app: consente di referenziare le URL con il prefisso "newsletter:".
app_name = "newsletter"

# Crea il router DRF che genera automaticamente le URL per i ViewSet.
router = DefaultRouter()

# Registra le sedi aziendali: genera gli endpoint CRUD per il modello Office.
router.register(r"offices", OfficeViewSet, basename="office")

# Registra i team: genera gli endpoint CRUD per il modello Team.
router.register(r"teams", TeamViewSet, basename="team")

# Registra i dipendenti: genera gli endpoint CRUD per il modello Employee.
router.register(r"employees", EmployeeViewSet, basename="employee")

# Registra i template email: genera gli endpoint CRUD per il modello EmailTemplate.
router.register(r"templates", EmailTemplateViewSet, basename="emailtemplate")

# Registra i log di invio: genera gli endpoint in sola lettura per il modello SendLog.
router.register(r"send-logs", SendLogViewSet, basename="sendlog")

urlpatterns = [
    # URL generate automaticamente dal router per tutti i ViewSet registrati.
    path("", include(router.urls)),

    # Endpoint per il trigger manuale dell'invio newsletter (POST).
    # Accoda un task asincrono tramite il Django Task Framework.
    path("newsletter/trigger/", TriggerNewsletterView.as_view(), name="trigger"),

    # Endpoint in sola lettura per consultare i festeggiati di oggi (GET).
    # Supporta il parametro opzionale ?date=YYYY-MM-DD nella query string.
    path("newsletter/celebrants-today/", TodaysCelebrantsView.as_view(), name="celebrants-today"),
]
