"""
Modelli dell'app "newsletter" per il servizio di birthday newsletter aziendale.

Questo file definisce la struttura del database del servizio: sedi aziendali,
team, dipendenti, template email e log degli invii. Ogni modello rappresenta
una tabella nel database relazionale.
"""

from datetime import date

from django.db import models


# ---------------------------------------------------------------------------
# Modello Office (Sede aziendale)
# ---------------------------------------------------------------------------

class Office(models.Model):
    """
    Rappresenta una sede aziendale.

    Ogni sede può avere un proprio fuso orario, necessario per calcolare
    correttamente l'orario di invio delle email di compleanno in aziende
    distribuite su più paesi o continenti.
    """

    # Nome della sede (es. "Roma", "Milano", "Londra").
    # Deve essere univoco per evitare duplicati nel sistema.
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nome sede",
    )

    # Fuso orario della sede, espresso nel formato standard IANA (es. "Europe/Rome").
    # Il valore predefinito è "Europe/Rome" perché il servizio nasce come prodotto italiano.
    # In un'azienda multinazionale ogni sede può avere un fuso orario diverso.
    timezone = models.CharField(
        max_length=50,
        default="Europe/Rome",
        verbose_name="Fuso orario",
    )

    # Data e ora in cui il record è stato creato nel database.
    # auto_now_add=True imposta automaticamente il valore al momento dell'inserimento
    # e lo rende non modificabile in seguito.
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data creazione",
    )

    class Meta:
        verbose_name = "Sede"
        verbose_name_plural = "Sedi"

    def __str__(self) -> str:
        return self.name


# ---------------------------------------------------------------------------
# Modello Team
# ---------------------------------------------------------------------------

class Team(models.Model):
    """
    Rappresenta un team all'interno di una sede aziendale.

    La relazione con Office permette di avere team con lo stesso nome in sedi
    diverse (es. "Marketing Roma" e "Marketing Milano"), grazie al vincolo
    unique_together nella classe Meta.
    """

    # Sede a cui appartiene il team.
    # on_delete=CASCADE: se la sede viene eliminata, vengono eliminati anche
    # tutti i team ad essa associati (e a cascata i dipendenti).
    office = models.ForeignKey(
        Office,
        on_delete=models.CASCADE,
        related_name="teams",
        verbose_name="Sede",
    )

    # Nome del team all'interno della sede (es. "Marketing", "Sviluppo").
    name = models.CharField(
        max_length=100,
        verbose_name="Nome team",
    )

    class Meta:
        verbose_name = "Team"
        verbose_name_plural = "Team"
        # Un team deve avere nome univoco all'interno della stessa sede.
        # Questo permette di avere "Marketing" sia a Roma che a Milano.
        unique_together = [("office", "name")]

    def __str__(self) -> str:
        # Formato "Sede - Team" per identificare immediatamente il contesto
        return f"{self.office} - {self.name}"


# ---------------------------------------------------------------------------
# Modello Employee (Dipendente)
# ---------------------------------------------------------------------------

class Employee(models.Model):
    """
    Rappresenta un dipendente aziendale iscritto al servizio di newsletter.

    Ogni dipendente appartiene a un team (e quindi indirettamente a una sede).
    I campi is_active e updated_at permettono di gestire i dipendenti senza
    eliminarli fisicamente dal database, preservando lo storico degli invii.
    """

    # Nome di battesimo del dipendente.
    first_name = models.CharField(
        max_length=100,
        verbose_name="Nome",
    )

    # Cognome del dipendente.
    last_name = models.CharField(
        max_length=100,
        verbose_name="Cognome",
    )

    # Indirizzo email aziendale, univoco nel sistema.
    # EmailField garantisce la validazione del formato dell'indirizzo.
    email = models.EmailField(
        unique=True,
        verbose_name="Email",
    )

    # Data di nascita del dipendente.
    # Usata per calcolare l'età e determinare il giorno del compleanno.
    birth_date = models.DateField(
        verbose_name="Data di nascita",
    )

    # Team di appartenenza del dipendente.
    # on_delete=SET_NULL: se il team viene eliminato, il dipendente rimane nel
    # sistema ma con team=None, evitando perdite di dati sugli invii passati.
    # null=True è necessario per permettere SET_NULL come comportamento di cancellazione.
    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        related_name="employees",
        verbose_name="Team",
    )

    # Indica se il dipendente è attivo nel sistema.
    # Un dipendente inattivo (es. che ha lasciato l'azienda) non riceve email
    # ma viene mantenuto nel database per preservare lo storico degli invii.
    is_active = models.BooleanField(
        default=True,
        verbose_name="Attivo",
    )

    # Data e ora di inserimento del record nel database.
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data creazione",
    )

    # Data e ora dell'ultimo aggiornamento del record.
    # auto_now=True aggiorna automaticamente il valore ad ogni salvataggio.
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Ultimo aggiornamento",
    )

    @property
    def age(self) -> int:
        """
        Calcola l'età attuale del dipendente in anni interi.

        Gestisce il caso speciale del 29 febbraio: se un dipendente è nato
        il 29 febbraio ma l'anno corrente non è bisestile, il suo compleanno
        viene considerato il 28 febbraio. Questo garantisce che i nati il
        29 febbraio ricevano comunque le congratulazioni ogni anno.
        """
        today = date.today()
        birth = self.birth_date

        # Gestione del 29 febbraio per anni non bisestili:
        # si sostituisce il giorno di nascita con il 28 febbraio.
        try:
            birthday_this_year = birth.replace(year=today.year)
        except ValueError:
            # ValueError si verifica quando birth_date è il 29/02
            # e l'anno corrente non è bisestile.
            birthday_this_year = birth.replace(year=today.year, day=28)

        # Se il compleanno di quest'anno non è ancora avvenuto,
        # sottraiamo 1 per ottenere l'età corretta.
        if birthday_this_year > today:
            return today.year - birth.year - 1
        return today.year - birth.year

    @property
    def is_birthday_today(self) -> bool:
        """
        Restituisce True se oggi è il compleanno del dipendente.

        Applica la stessa logica di 'age' per il 29 febbraio:
        i nati il 29/02 festeggiano il 28/02 negli anni non bisestili.
        """
        today = date.today()
        birth = self.birth_date

        # Gestione del 29 febbraio per anni non bisestili:
        # il compleanno è considerato il 28 febbraio.
        try:
            birthday_this_year = birth.replace(year=today.year)
        except ValueError:
            # ValueError si verifica quando birth_date è il 29/02
            # e l'anno corrente non è bisestile.
            birthday_this_year = birth.replace(year=today.year, day=28)

        return birthday_this_year == today

    class Meta:
        verbose_name = "Dipendente"
        verbose_name_plural = "Dipendenti"
        # Ordinamento predefinito per cognome e poi per nome, come in un elenco aziendale.
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        # Formato "Nome Cognome (email)" per identificare univocamente il dipendente
        return f"{self.first_name} {self.last_name} ({self.email})"


# ---------------------------------------------------------------------------
# Modello EmailTemplate (Template email configurabile)
# ---------------------------------------------------------------------------

class EmailTemplate(models.Model):
    """
    Rappresenta un template configurabile per le email di compleanno.

    Supporta placeholder che vengono sostituiti dinamicamente al momento
    dell'invio con i dati reali (nome destinatario, elenco festeggiati, ecc.).
    Un solo template può essere marcato come predefinito (is_default=True).
    """

    # Nome identificativo del template (es. "Template Standard", "Template Natalizio").
    # Deve essere univoco per permettere la selezione senza ambiguità.
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nome template",
    )

    # Oggetto dell'email. Supporta i seguenti placeholder:
    # {date}        → data dell'invio (es. "10 marzo 2026")
    # {team_name}   → nome del team del destinatario
    # {office_name} → nome della sede del destinatario
    subject = models.CharField(
        max_length=200,
        verbose_name="Oggetto email",
    )

    # Corpo dell'email in formato testo. Supporta i seguenti placeholder:
    # {recipient_name}  → nome del destinatario dell'email
    # {celebrants_list} → elenco dei dipendenti che compiono gli anni oggi
    # {date}            → data dell'invio (es. "10 marzo 2026")
    body = models.TextField(
        verbose_name="Corpo email",
    )

    # Indica se questo è il template predefinito del sistema.
    # Viene usato quando non viene specificato un template esplicito per un invio.
    # La gestione dell'unicità del template di default (uno solo attivo) è
    # delegata alla business logic (serializer/view/task) per semplicità.
    is_default = models.BooleanField(
        default=False,
        verbose_name="Template predefinito",
    )

    # Data e ora di creazione del record.
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data creazione",
    )

    # Data e ora dell'ultimo aggiornamento del record.
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Ultimo aggiornamento",
    )

    def render_subject(self, context_dict: dict) -> str:
        """
        Restituisce il subject con i placeholder sostituiti dai valori in context_dict.

        I placeholder non presenti in context_dict vengono lasciati invariati
        grazie al comportamento predefinito di str.format_map con default_factory.
        """
        return _render_template_string(self.subject, context_dict)

    def render_body(self, context_dict: dict) -> str:
        """
        Restituisce il body con i placeholder sostituiti dai valori in context_dict.

        I placeholder non presenti in context_dict vengono lasciati invariati
        grazie al comportamento predefinito di str.format_map con default_factory.
        """
        return _render_template_string(self.body, context_dict)

    class Meta:
        verbose_name = "Template email"
        verbose_name_plural = "Template email"

    def __str__(self) -> str:
        # Aggiunge "(default)" al nome se è il template predefinito,
        # rendendo immediatamente riconoscibile il template attivo nell'admin.
        if self.is_default:
            return f"{self.name} (default)"
        return self.name


def _render_template_string(template: str, context_dict: dict) -> str:
    """
    Sostituisce i placeholder in formato {chiave} nel testo con i valori del dizionario.

    I placeholder non trovati nel dizionario vengono lasciati invariati.
    Questa funzione è usata internamente da EmailTemplate.render_subject
    e EmailTemplate.render_body.
    """

    class _SafeDict(dict):
        """Dict che restituisce il placeholder originale per chiavi mancanti."""

        def __missing__(self, key: str) -> str:
            return "{" + key + "}"

    return template.format_map(_SafeDict(context_dict))


# ---------------------------------------------------------------------------
# Modello SendLog (Log di un invio giornaliero)
# ---------------------------------------------------------------------------

class SendLog(models.Model):
    """
    Rappresenta il log di un singolo run giornaliero del servizio di newsletter.

    Ogni volta che il task di invio viene eseguito, viene creato un SendLog
    che traccia quante email sono state inviate, quanti festeggiati sono stati
    trovati, e l'esito complessivo dell'operazione.
    """

    # Scelte possibili per il campo 'status'.
    # Usare costanti di classe per evitare stringhe magiche sparse nel codice.
    class Status(models.TextChoices):
        # Il task è in attesa di essere eseguito
        PENDING = "PENDING", "In attesa"
        # Il task è attualmente in esecuzione
        RUNNING = "RUNNING", "In esecuzione"
        # Il task è terminato con successo
        COMPLETED = "COMPLETED", "Completato"
        # Il task è terminato con un errore
        FAILED = "FAILED", "Fallito"

    # Data a cui si riferisce questo run (es. "2026-03-10").
    # Non è la data di esecuzione (quella è 'triggered_at'), ma il giorno
    # per cui si cercano i compleanni.
    send_date = models.DateField(
        verbose_name="Data invio",
    )

    # Data e ora esatta in cui il task è stato avviato.
    triggered_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Avviato il",
    )

    # Numero totale di email inviate durante questo run.
    total_recipients = models.IntegerField(
        default=0,
        verbose_name="Destinatari totali",
    )

    # Numero totale di dipendenti che compiono gli anni nella data 'send_date'.
    total_celebrants = models.IntegerField(
        default=0,
        verbose_name="Festeggiati totali",
    )

    # Stato corrente del run. Inizia come PENDING, passa a RUNNING durante
    # l'esecuzione, e termina come COMPLETED o FAILED.
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Stato",
    )

    # Messaggio di errore in caso di fallimento del run.
    # blank=True permette il valore vuoto nei form; null=True permette NULL nel DB.
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name="Messaggio di errore",
    )

    # Template email usato per questo run.
    # on_delete=SET_NULL: se il template viene eliminato, il log rimane valido
    # con template_used=None, preservando lo storico degli invii.
    template_used = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Template utilizzato",
    )

    class Meta:
        verbose_name = "Log invio"
        verbose_name_plural = "Log invii"
        # Ordina i log dal più recente al più vecchio, utile nell'admin.
        ordering = ["-triggered_at"]

    def __str__(self) -> str:
        return f"Invio del {self.send_date} - {self.status}"


# ---------------------------------------------------------------------------
# Modello SendLogEntry (Riga del log: un'email inviata a un destinatario)
# ---------------------------------------------------------------------------

class SendLogEntry(models.Model):
    """
    Rappresenta una singola email inviata nell'ambito di un run giornaliero.

    Ogni riga corrisponde a un destinatario che ha ricevuto (o avrebbe dovuto
    ricevere) l'email di auguri. Il campo 'celebrants_included' registra quali
    dipendenti sono stati inclusi nell'email inviata a quel destinatario,
    permettendo di ricostruire esattamente cosa è stato comunicato.
    """

    # Log del run a cui appartiene questa riga.
    # on_delete=CASCADE: eliminare il log elimina anche tutte le sue righe.
    log = models.ForeignKey(
        SendLog,
        on_delete=models.CASCADE,
        related_name="entries",
        verbose_name="Log invio",
    )

    # Dipendente che ha ricevuto l'email.
    # on_delete=SET_NULL: se il dipendente viene eliminato, la riga del log rimane
    # nel sistema con recipient=None, preservando lo storico degli invii.
    recipient = models.ForeignKey(
        "Employee",
        on_delete=models.SET_NULL,
        null=True,
        related_name="received_logs",
        verbose_name="Destinatario",
    )

    # Dipendenti i cui compleanni sono stati inclusi in questa email.
    # ManyToManyField perché un'email può contenere più festeggiati, e un
    # festeggiato può essere incluso in più email (una per ogni collega del team).
    # blank=True permette email senza festeggiati (es. in caso di errore logico).
    celebrants_included = models.ManyToManyField(
        "Employee",
        related_name="celebrated_in_logs",
        blank=True,
        verbose_name="Festeggiati inclusi",
    )

    # Data e ora esatta di invio dell'email.
    sent_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Inviata il",
    )

    # True se l'email è stata inviata con successo, False in caso di errore.
    success = models.BooleanField(
        default=True,
        verbose_name="Successo",
    )

    # Dettaglio dell'errore in caso di fallimento dell'invio singolo.
    # blank=True e null=True perché il campo è opzionale (rilevante solo in caso di errore).
    error_detail = models.TextField(
        blank=True,
        null=True,
        verbose_name="Dettaglio errore",
    )

    class Meta:
        verbose_name = "Riga log invio"
        verbose_name_plural = "Righe log invio"

    def __str__(self) -> str:
        # Gestione difensiva: recipient potrebbe essere None se il dipendente
        # è stato eliminato (a causa di SET_NULL sul ForeignKey).
        recipient_email = self.recipient.email if self.recipient else "destinatario eliminato"
        return f"Email a {recipient_email} per invio {self.log.send_date}"
