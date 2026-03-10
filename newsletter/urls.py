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
    /api/trigger-newsletter/             – TriggerNewsletterView (POST)
    /api/todays-celebrants/              – TodaysCelebrantsView (GET)
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

# Crea il router DRF che genera automaticamente le URL per i ViewSet.
router = DefaultRouter()

# Registrazione dei ViewSet con i relativi prefissi URL.
router.register(r"offices", OfficeViewSet, basename="office")
router.register(r"teams", TeamViewSet, basename="team")
router.register(r"employees", EmployeeViewSet, basename="employee")
router.register(r"templates", EmailTemplateViewSet, basename="emailtemplate")
router.register(r"send-logs", SendLogViewSet, basename="sendlog")

urlpatterns = [
    # URL generate automaticamente dal router per tutti i ViewSet registrati.
    path("", include(router.urls)),

    # Endpoint custom per il trigger manuale dell'invio newsletter.
    # Accoda un task asincrono tramite il Django Task Framework.
    path("trigger-newsletter/", TriggerNewsletterView.as_view(), name="trigger-newsletter"),

    # Endpoint custom in sola lettura per consultare i festeggiati di oggi.
    # Supporta il parametro opzionale ?date=YYYY-MM-DD nella query string.
    path("todays-celebrants/", TodaysCelebrantsView.as_view(), name="todays-celebrants"),
]
