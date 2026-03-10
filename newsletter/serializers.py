"""
Serializer dell'app "newsletter" per il servizio di birthday newsletter aziendale.

Questo file definisce i serializer DRF usati per la serializzazione/deserializzazione
dei modelli nelle API REST. Ogni serializer corrisponde a un modello o a un caso d'uso
specifico (es. lista compatta, trigger manuale, dettaglio con relazioni nested).
"""

from __future__ import annotations

from datetime import date

from rest_framework import serializers

from .models import (
    EmailTemplate,
    Employee,
    Office,
    SendLog,
    SendLogEntry,
    Team,
)


# ---------------------------------------------------------------------------
# OfficeSerializer
# ---------------------------------------------------------------------------

class OfficeSerializer(serializers.ModelSerializer):
    """
    Serializer completo per il modello Office.

    Espone tutti i campi della sede aziendale, incluso il fuso orario e la
    data di creazione. Usato negli endpoint CRUD per le sedi.
    """

    class Meta:
        model = Office
        fields = "__all__"


# ---------------------------------------------------------------------------
# TeamSerializer
# ---------------------------------------------------------------------------

class TeamSerializer(serializers.ModelSerializer):
    """
    Serializer per il modello Team con informazioni aggiuntive sulla sede.

    Aggiunge il campo 'office_name' (read-only) che evita di dover fare una
    chiamata nested completa per ottenere il nome della sede. Il campo 'office'
    rimane un PrimaryKeyRelatedField scrivibile per supportare il CRUD.
    """

    # Campo calcolato: nome della sede del team.
    # source="office.name" attraversa la FK e legge direttamente il campo name.
    # Evita di restituire un oggetto Office nested completo nella risposta.
    office_name = serializers.CharField(source="office.name", read_only=True)

    class Meta:
        model = Team
        fields = "__all__"


# ---------------------------------------------------------------------------
# TeamNestedSerializer
# ---------------------------------------------------------------------------

class TeamNestedSerializer(serializers.ModelSerializer):
    """
    Versione compatta del serializer Team per l'uso in contesti nested.

    Espone solo id e name, sufficiente per identificare il team senza
    appesantire la risposta con dati non necessari. Usato in EmployeeSerializer.
    """

    class Meta:
        model = Team
        fields = ["id", "name"]


# ---------------------------------------------------------------------------
# EmployeeSerializer
# ---------------------------------------------------------------------------

class EmployeeSerializer(serializers.ModelSerializer):
    """
    Serializer completo per il modello Employee.

    Include tutti i campi del modello più:
    - 'age': età calcolata tramite la property del modello (read-only)
    - 'is_birthday_today': flag compleanno odierno (read-only)
    - 'team_detail': rappresentazione nested del team (read-only)

    Il campo 'team' rimane un PrimaryKeyRelatedField scrivibile per permettere
    la creazione e l'aggiornamento del dipendente con un semplice ID intero.
    """

    # Età calcolata in anni interi delegando alla property Employee.age.
    # read_only=True perché è un valore derivato, non impostabile dall'utente.
    age = serializers.SerializerMethodField()

    # True se oggi è il compleanno del dipendente, False altrimenti.
    # Delegato alla property Employee.is_birthday_today del modello.
    is_birthday_today = serializers.SerializerMethodField()

    # Rappresentazione compatta del team in sola lettura.
    # source="team" punta alla FK team del modello Employee.
    # Il campo 'team' scrivibile rimane separato (PrimaryKeyRelatedField implicito).
    team_detail = TeamNestedSerializer(source="team", read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "birth_date",
            "team",
            "team_detail",
            "is_active",
            "created_at",
            "updated_at",
            "age",
            "is_birthday_today",
        ]

    def get_age(self, instance: Employee) -> int:
        """Restituisce l'età del dipendente delegando alla property del modello."""
        return instance.age

    def get_is_birthday_today(self, instance: Employee) -> bool:
        """Restituisce True se oggi è il compleanno del dipendente."""
        return instance.is_birthday_today


# ---------------------------------------------------------------------------
# EmployeeBriefSerializer
# ---------------------------------------------------------------------------

class EmployeeBriefSerializer(serializers.ModelSerializer):
    """
    Versione compatta del serializer Employee per liste e contesti di log.

    Espone solo i campi essenziali per identificare un dipendente: id,
    nome, cognome, email ed età calcolata. Usato nelle email di auguri e
    nei SendLogEntry per rappresentare i festeggiati inclusi.
    """

    # Età calcolata, inclusa anche nella versione compatta per la visualizzazione
    # nell'email (es. "Mario Rossi compie 35 anni").
    age = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ["id", "first_name", "last_name", "email", "age"]

    def get_age(self, instance: Employee) -> int:
        """Restituisce l'età del dipendente delegando alla property del modello."""
        return instance.age


# ---------------------------------------------------------------------------
# EmailTemplateSerializer
# ---------------------------------------------------------------------------

class EmailTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer completo per il modello EmailTemplate.

    Espone tutti i campi del template email, inclusi subject, body e il flag
    is_default che indica il template predefinito del sistema.
    """

    class Meta:
        model = EmailTemplate
        fields = "__all__"


# ---------------------------------------------------------------------------
# SendLogEntrySerializer
# ---------------------------------------------------------------------------

class SendLogEntrySerializer(serializers.ModelSerializer):
    """
    Serializer per il modello SendLogEntry (singola email inviata).

    Aggiunge:
    - 'recipient_email': email del destinatario (read-only, source="recipient.email")
      per evitare di dover fare un join nested solo per l'indirizzo email.
    - 'celebrants_brief': lista compatta dei festeggiati inclusi nell'email,
      usando EmployeeBriefSerializer per ogni elemento del ManyToManyField.
    """

    # Email del destinatario ricavata attraversando la FK recipient.
    # allow_null=True perché recipient può essere None (SET_NULL se eliminato).
    recipient_email = serializers.EmailField(
        source="recipient.email",
        read_only=True,
        allow_null=True,
    )

    # Lista compatta dei festeggiati inclusi in questa email.
    # many=True perché celebrants_included è un ManyToManyField.
    # source="celebrants_included" punta al campo M2M del modello.
    celebrants_brief = EmployeeBriefSerializer(
        source="celebrants_included",
        many=True,
        read_only=True,
    )

    class Meta:
        model = SendLogEntry
        fields = "__all__"


# ---------------------------------------------------------------------------
# SendLogSerializer
# ---------------------------------------------------------------------------

class SendLogSerializer(serializers.ModelSerializer):
    """
    Serializer per il modello SendLog (log di un run giornaliero).

    Aggiunge:
    - 'entries': lista di tutte le email inviate in questo run (read-only).
    - 'template_name': nome del template usato (read-only, source="template_used.name")
      per evitare un join nested completo sul template.
    """

    # Lista nested di tutte le righe del log associate a questo run.
    # many=True perché entries è il related_name della FK SendLogEntry.log.
    entries = SendLogEntrySerializer(many=True, read_only=True)

    # Nome del template usato per l'invio, ricavato attraversando la FK template_used.
    # allow_null=True perché template_used può essere None (SET_NULL se eliminato).
    template_name = serializers.CharField(
        source="template_used.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = SendLog
        fields = "__all__"


# ---------------------------------------------------------------------------
# TriggerSendSerializer
# ---------------------------------------------------------------------------

class TriggerSendSerializer(serializers.Serializer):
    """
    Serializer per l'endpoint di trigger manuale dell'invio newsletter.

    Permette di avviare un run specificando opzionalmente la data e il template.
    Se i campi vengono omessi, il sistema usa la data odierna e il template
    predefinito (is_default=True).

    Validazione:
    - 'date': non può essere una data futura (per evitare invii anticipati).
    - 'template_id': non viene validato qui (la view verifica l'esistenza nel DB).
    """

    # Data per cui cercare i compleanni e inviare le email.
    # Opzionale: se omessa, la view usa date.today().
    # allow_null=True e required=False permettono di inviare la richiesta senza questo campo.
    date = serializers.DateField(
        required=False,
        allow_null=True,
        default=None,
    )

    # ID del template email da usare per l'invio.
    # Opzionale: se omesso, la view seleziona il template con is_default=True.
    template_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None,
    )

    def validate_date(self, value: date | None) -> date | None:
        """
        Impedisce di specificare una data futura per l'invio.

        Le date future non sono permesse perché il servizio invia auguri per
        compleanni avvenuti oggi o nel passato. Un invio anticipato non avrebbe
        senso logico e potrebbe creare confusione nei destinatari.

        Args:
            value: La data fornita nella richiesta, o None se omessa.

        Returns:
            Il valore validato (date o None).

        Raises:
            serializers.ValidationError: se la data è successiva a oggi.
        """
        if value is not None and value > date.today():
            raise serializers.ValidationError(
                "La data non può essere nel futuro. Specifica la data odierna o una data passata."
            )
        return value
