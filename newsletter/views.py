"""
View dell'app "newsletter" per il servizio di birthday newsletter aziendale.

Questo modulo definisce tutti i ViewSet e le APIView DRF che espongono le
risorse REST del sistema. Le view si dividono in due categorie:

1. ViewSet CRUD (ModelViewSet / ReadOnlyModelViewSet):
   - OfficeViewSet       – gestione sedi aziendali
   - TeamViewSet         – gestione team
   - EmployeeViewSet     – gestione dipendenti (con action birthdays-today)
   - EmailTemplateViewSet – gestione template email (con action set-default)
   - SendLogViewSet      – log degli invii (sola lettura)

2. APIView custom:
   - TriggerNewsletterView  – avvia manualmente un run di invio newsletter
   - TodaysCelebrantsView   – elenca i festeggiati di oggi (o di una data)
"""

from __future__ import annotations

import logging
from datetime import date as date_type

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

# Importazione dei modelli del dominio
from .models import (
    EmailTemplate,
    Employee,
    Office,
    SendLog,
    Team,
)

# Importazione dei serializer per la serializzazione/deserializzazione
from .serializers import (
    EmailTemplateSerializer,
    EmployeeBriefSerializer,
    EmployeeSerializer,
    OfficeSerializer,
    SendLogSerializer,
    TeamSerializer,
    TriggerSendSerializer,
)

# Importazione del task asincrono per l'invio della newsletter
from .tasks import run_birthday_newsletter

# Importazione del servizio che calcola i festeggiati odierni
from .services import get_todays_celebrants

# Logger del modulo: facilita il filtraggio e la configurazione del logging.
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OfficeViewSet
# ---------------------------------------------------------------------------


class OfficeViewSet(ModelViewSet):
    """
    ViewSet CRUD per il modello Office (sede aziendale).

    Espone le operazioni standard: list, create, retrieve, update,
    partial_update, destroy. Supporta la ricerca testuale per nome sede.

    Endpoint:
        GET    /api/offices/         – lista di tutte le sedi
        POST   /api/offices/         – crea una nuova sede
        GET    /api/offices/{id}/    – dettaglio di una sede
        PUT    /api/offices/{id}/    – aggiorna completamente una sede
        PATCH  /api/offices/{id}/    – aggiornamento parziale di una sede
        DELETE /api/offices/{id}/    – elimina una sede
    """

    # Queryset ordinato per nome per garantire un ordinamento stabile e leggibile.
    queryset = Office.objects.all().order_by("name")

    # Serializer che espone tutti i campi del modello Office.
    serializer_class = OfficeSerializer

    # SearchFilter permette ?search=<testo> per filtrare per nome sede.
    filter_backends = [SearchFilter]

    # Campo su cui viene applicata la ricerca testuale.
    search_fields = ["name"]


# ---------------------------------------------------------------------------
# TeamViewSet
# ---------------------------------------------------------------------------


class TeamViewSet(ModelViewSet):
    """
    ViewSet CRUD per il modello Team.

    Usa select_related('office') per ottimizzare le query evitando il
    problema N+1 quando si accede alla relazione con Office. Supporta
    il filtraggio per sede (office) e la ricerca testuale per nome team.

    Endpoint:
        GET    /api/teams/           – lista di tutti i team
        POST   /api/teams/           – crea un nuovo team
        GET    /api/teams/{id}/      – dettaglio di un team
        PUT    /api/teams/{id}/      – aggiorna completamente un team
        PATCH  /api/teams/{id}/      – aggiornamento parziale di un team
        DELETE /api/teams/{id}/      – elimina un team
    """

    # select_related('office') precarica la sede in JOIN SQL evitando query aggiuntive.
    queryset = Team.objects.select_related("office").all()

    # Serializer che include anche il campo office_name calcolato.
    serializer_class = TeamSerializer

    # DjangoFilterBackend permette ?office=<id> per filtrare per sede.
    # SearchFilter permette ?search=<testo> per ricerca testuale.
    filter_backends = [DjangoFilterBackend, SearchFilter]

    # Campo su cui viene applicato il filtro esatto per FK.
    filterset_fields = ["office"]

    # Campo su cui viene applicata la ricerca testuale.
    search_fields = ["name"]


# ---------------------------------------------------------------------------
# EmployeeViewSet
# ---------------------------------------------------------------------------


class EmployeeViewSet(ModelViewSet):
    """
    ViewSet CRUD per il modello Employee (dipendente).

    Usa select_related('team__office') per ottimizzare le query sulla catena
    FK Employee -> Team -> Office. Supporta filtraggio avanzato, ricerca
    testuale e ordinamento. Include un'action custom per i festeggiati di oggi.

    Endpoint standard:
        GET    /api/employees/              – lista dei dipendenti
        POST   /api/employees/             – crea un nuovo dipendente
        GET    /api/employees/{id}/         – dettaglio di un dipendente
        PUT    /api/employees/{id}/         – aggiornamento completo
        PATCH  /api/employees/{id}/         – aggiornamento parziale
        DELETE /api/employees/{id}/         – elimina un dipendente

    Endpoint custom:
        GET    /api/employees/birthdays-today/ – dipendenti che festeggiano oggi
    """

    # select_related('team__office') precarica la catena FK in un'unica query JOIN.
    queryset = Employee.objects.select_related("team__office").all()

    # Serializer completo con campi calcolati (age, is_birthday_today, team_detail).
    serializer_class = EmployeeSerializer

    # Backend di filtraggio:
    # - DjangoFilterBackend: filtri esatti per FK e boolean
    # - SearchFilter: ricerca testuale su nome, cognome ed email
    # - OrderingFilter: ordinamento dei risultati tramite ?ordering=<campo>
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    # Campi su cui è possibile applicare filtri esatti tramite query string.
    filterset_fields = ["is_active", "team", "team__office"]

    # Campi su cui viene applicata la ricerca testuale con ?search=<testo>.
    search_fields = ["first_name", "last_name", "email"]

    # Campi su cui è possibile ordinare i risultati con ?ordering=<campo>.
    ordering_fields = ["last_name", "birth_date", "created_at"]

    @action(detail=False, methods=["get"], url_path="birthdays-today")
    def birthdays_today(self, request: Request) -> Response:
        """
        Action custom: restituisce i dipendenti che festeggiano oggi.

        Chiama il servizio get_todays_celebrants() che gestisce automaticamente
        il caso dei nati il 29 febbraio in anni non bisestili (li include il 28/02).

        Endpoint: GET /api/employees/birthdays-today/

        Returns:
            Response con lista dei festeggiati serializzati con EmployeeBriefSerializer
            e il conteggio totale.
        """
        # Recupera i festeggiati del giorno tramite il servizio dedicato.
        # Viene usata la data odierna (nessun parametro passato).
        celebrants = get_todays_celebrants()

        # Serializza con il serializer compatto (id, nome, cognome, email, età).
        serializer = EmployeeBriefSerializer(celebrants, many=True)
        data = serializer.data

        return Response(
            {
                "count": len(data),
                "results": data,
            }
        )


# ---------------------------------------------------------------------------
# EmailTemplateViewSet
# ---------------------------------------------------------------------------


class EmailTemplateViewSet(ModelViewSet):
    """
    ViewSet CRUD per il modello EmailTemplate (template email compleanno).

    Include un'action custom per impostare un template come predefinito,
    rimuovendo il flag is_default da tutti gli altri template.

    Endpoint standard:
        GET    /api/templates/          – lista dei template
        POST   /api/templates/          – crea un nuovo template
        GET    /api/templates/{id}/     – dettaglio di un template
        PUT    /api/templates/{id}/     – aggiornamento completo
        PATCH  /api/templates/{id}/     – aggiornamento parziale
        DELETE /api/templates/{id}/     – elimina un template

    Endpoint custom:
        POST   /api/templates/{id}/set-default/ – imposta come template predefinito
    """

    # Queryset senza ordinamento specifico; l'ordinamento di default è per PK.
    queryset = EmailTemplate.objects.all()

    # Serializer che espone tutti i campi del modello EmailTemplate.
    serializer_class = EmailTemplateSerializer

    @action(detail=True, methods=["post"], url_path="set-default")
    def set_default(self, request: Request, pk=None) -> Response:
        """
        Action custom: imposta questo template come predefinito (is_default=True).

        Rimuove il flag is_default da tutti gli altri template usando un aggiornamento
        bulk in una singola query SQL per efficienza, poi imposta is_default=True
        sul template corrente.

        Endpoint: POST /api/templates/{id}/set-default/

        Returns:
            Response con il template aggiornato serializzato e il messaggio di conferma.
        """
        # Recupera il template dall'URL (get_object gestisce anche il 404).
        template = self.get_object()

        # Rimuove il flag is_default da tutti gli altri template in una singola query.
        # Questo garantisce che esista sempre al più un template predefinito.
        EmailTemplate.objects.exclude(pk=template.pk).update(is_default=False)

        # Imposta il flag sul template corrente e salva solo il campo modificato.
        template.is_default = True
        template.save(update_fields=["is_default"])

        # Serializza il template aggiornato per la risposta.
        serializer = self.get_serializer(template)

        logger.info(f"[EmailTemplate] Template #{template.pk} ({template.name!r}) impostato come predefinito.")

        return Response(serializer.data)


# ---------------------------------------------------------------------------
# SendLogViewSet
# ---------------------------------------------------------------------------


class SendLogViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """
    ViewSet in sola lettura per il modello SendLog (log degli invii newsletter).

    Espone solo le operazioni list e retrieve per consultazione dei log.
    Usa prefetch_related per precaricare le entry e le loro relazioni M2M
    ed evitare il problema N+1 sulle query nested.

    Endpoint:
        GET    /api/send-logs/          – lista dei log di invio
        GET    /api/send-logs/{id}/     – dettaglio di un log di invio
    """

    # prefetch_related precarica la catena:
    # entries -> recipient (FK) e entries -> celebrants_included (M2M)
    # in query SQL separate ma efficienti, evitando N+1.
    queryset = SendLog.objects.prefetch_related(
        "entries__recipient",
        "entries__celebrants_included",
    ).all()

    # Serializer che include le entry nested con i festeggiati.
    serializer_class = SendLogSerializer

    # Backend di filtraggio:
    # - DjangoFilterBackend: filtri esatti per status e data di invio
    # - OrderingFilter: ordinamento per data di trigger e data di invio
    filter_backends = [DjangoFilterBackend, OrderingFilter]

    # Campi su cui è possibile applicare filtri esatti.
    filterset_fields = ["status", "send_date"]

    # Campi su cui è possibile ordinare i risultati.
    ordering_fields = ["triggered_at", "send_date"]


# ---------------------------------------------------------------------------
# TriggerNewsletterView
# ---------------------------------------------------------------------------


class TriggerNewsletterView(APIView):
    """
    APIView per il trigger manuale dell'invio della newsletter di compleanno.

    Accoda il task asincrono run_birthday_newsletter nel backend Django Tasks.
    Il client può opzionalmente specificare la data di riferimento e il template
    da usare. Se omessi, vengono usati i valori predefiniti (oggi e template default).

    Endpoint:
        POST /api/newsletter/trigger/

    Request body (tutti i campi opzionali):
        {
            "date": "YYYY-MM-DD",   # data di riferimento (default: oggi)
            "template_id": 1        # ID del template (default: template predefinito)
        }

    Responses:
        202 Accepted  – task accodato con successo
        400 Bad Request – dati di input non validi
        500 Internal Server Error – impossibile accodare il task
    """

    def post(self, request: Request) -> Response:
        """
        Valida l'input e accoda il task di invio newsletter.

        Usa TriggerSendSerializer per validare e deserializzare i dati in ingresso.
        Converte la date in stringa ISO prima di passarla al task, perché il Django
        Task Framework serializza i parametri come JSON e non supporta oggetti date.

        Args:
            request: La richiesta HTTP con i parametri opzionali nel body.

        Returns:
            Response 202 con il task ID se l'accodamento ha avuto successo.
            Response 400 se i dati di input non sono validi.
            Response 500 se il task non può essere accodato.
        """
        # Valida i dati in ingresso tramite il serializer dedicato.
        serializer = TriggerSendSerializer(data=request.data)
        if not serializer.is_valid():
            # Restituisce i dettagli degli errori di validazione.
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Estrae i campi validati (entrambi possono essere None se omessi).
        reference_date = serializer.validated_data.get("date")
        template_id = serializer.validated_data.get("template_id")

        # Converte la data in stringa ISO se presente, perché il Django Task Framework
        # serializza i parametri come JSON e gli oggetti datetime.date non sono
        # direttamente serializzabili in JSON dal framework.
        reference_date_str = reference_date.isoformat() if reference_date is not None else None

        try:
            # Accoda il task nel backend Django Tasks tramite il metodo enqueue().
            # enqueue() è il metodo del Task Framework per accodare un task.
            task = run_birthday_newsletter.enqueue(reference_date_str, template_id)

            logger.info(
                f"[TriggerNewsletterView] Task accodato con successo – "
                f"task.id={task.id!r}, reference_date_str={reference_date_str!r}, "
                f"template_id={template_id!r}"
            )

            return Response(
                {
                    "message": f"Newsletter accodata con successo. Task ID: {task.id}",
                    "task_id": str(task.id),
                },
                status=status.HTTP_202_ACCEPTED,
            )

        except Exception:
            # Logga l'errore completo per il debug, restituisce 500 al client.
            logger.exception(
                "[TriggerNewsletterView] Errore durante l'accodamento del task newsletter."
            )
            return Response(
                {"error": "Impossibile accodare il task di invio newsletter. Riprovare più tardi."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ---------------------------------------------------------------------------
# TodaysCelebrantsView
# ---------------------------------------------------------------------------


class TodaysCelebrantsView(APIView):
    """
    APIView in sola lettura per consultare i festeggiati di oggi (o di una data).

    Chiama il servizio get_todays_celebrants() che gestisce la logica di business
    incluso il caso speciale dei nati il 29 febbraio. Supporta un parametro opzionale
    nella query string per specificare una data diversa da oggi.

    Endpoint:
        GET /api/newsletter/celebrants-today/
        GET /api/newsletter/celebrants-today/?date=YYYY-MM-DD

    Responses:
        200 OK – lista dei festeggiati con conteggio
        400 Bad Request – formato della data non valido
    """

    def get(self, request: Request) -> Response:
        """
        Restituisce i dipendenti che festeggiano nella data specificata (default: oggi).

        Legge il parametro opzionale 'date' dalla query string. Se fornito,
        lo converte in oggetto date; se il formato è invalido, restituisce 400.
        Se assente, passa None al servizio che usa la data odierna.

        Args:
            request: La richiesta HTTP con il parametro opzionale ?date=YYYY-MM-DD.

        Returns:
            Response 200 con la lista serializzata dei festeggiati e il conteggio totale.
            Response 400 se il formato della data fornita non è valido.
        """
        # Legge il parametro 'date' dalla query string (es. ?date=2026-03-10).
        date_str = request.query_params.get("date")

        # Converte la stringa in oggetto date se fornita, altrimenti usa None.
        reference_date = None
        if date_str is not None:
            try:
                # Valida il formato ISO 8601 (YYYY-MM-DD).
                reference_date = date_type.fromisoformat(date_str)
            except ValueError:
                # Il formato della data non è valido: restituisce 400 con messaggio esplicativo.
                return Response(
                    {"error": f"Formato data non valido: {date_str!r}. Usa il formato YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Chiama il servizio per ottenere i festeggiati della data specificata.
        # Il servizio gestisce automaticamente:
        # - i nati il 29 febbraio in anni non bisestili (inclusi il 28/02)
        # - il filtraggio per dipendenti attivi
        celebrants = get_todays_celebrants(reference_date)

        # Serializza la lista con il serializer compatto (id, nome, cognome, email, età).
        serializer = EmployeeBriefSerializer(celebrants, many=True)
        data = serializer.data

        return Response(
            {
                "date": (reference_date or date_type.today()).isoformat(),
                "count": len(data),
                "results": data,
            }
        )
