"""
Registrazione dei modelli dell'app "newsletter" nel pannello di amministrazione Django.

Per ogni modello vengono configurate le colonne visualizzate nell'elenco,
i filtri laterali, i campi di ricerca e i campi in sola lettura, in modo
da rendere la navigazione dell'admin intuitiva per chi gestisce il servizio.
"""

from django.contrib import admin

from .models import EmailTemplate, Employee, Office, SendLog, SendLogEntry, Team


# ---------------------------------------------------------------------------
# Admin per il modello Office (Sede aziendale)
# ---------------------------------------------------------------------------

@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    """
    Configurazione admin per le sedi aziendali.

    La visualizzazione di base è sufficiente perché le sedi sono poche
    e non richiedono filtri o ricerche avanzate.
    """

    # Colonne mostrate nell'elenco delle sedi: nome e fuso orario
    # per identificare rapidamente ogni sede.
    list_display = ("name", "timezone", "created_at")


# ---------------------------------------------------------------------------
# Admin per il modello Team
# ---------------------------------------------------------------------------

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    """
    Configurazione admin per i team aziendali.

    Il filtro per sede permette di navigare rapidamente tra i team
    di una specifica sede senza dover scorrere l'intero elenco.
    """

    # Colonne mostrate nell'elenco: nome del team e sede di appartenenza.
    list_display = ("name", "office")

    # Filtro laterale per sede: utile in aziende con più uffici.
    list_filter = ("office",)


# ---------------------------------------------------------------------------
# Admin per il modello Employee (Dipendente)
# ---------------------------------------------------------------------------

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    """
    Configurazione admin per i dipendenti.

    L'elenco mostra i campi più rilevanti per la gestione del servizio,
    incluso il flag 'is_birthday_today' per identificare a colpo d'occhio
    chi compie gli anni nella data odierna. I filtri per stato attivo e sede
    permettono di segmentare rapidamente i dipendenti. La ricerca testuale
    copre nome, cognome ed email per trovare rapidamente un dipendente.
    I campi 'created_at' e 'updated_at' sono in sola lettura perché vengono
    gestiti automaticamente da Django (auto_now_add / auto_now).
    """

    # Colonne visualizzate nell'elenco dei dipendenti.
    # 'is_birthday_today' è una property del modello: Django ne mostra il
    # valore restituito (True/False) come testo nella colonna dell'elenco.
    list_display = (
        "first_name",   # Nome di battesimo
        "last_name",    # Cognome
        "email",        # Indirizzo email aziendale
        "team",         # Team di appartenenza (usa __str__ del modello Team)
        "is_active",    # Indicatore attivo/inattivo
        "is_birthday_today",  # Oggi è il compleanno? (calcolato dinamicamente)
    )

    # Filtri laterali per restringere l'elenco.
    # 'is_active' permette di separare dipendenti attivi da quelli cessati.
    # 'team__office' permette di filtrare per sede, attraversando la relazione
    # Employee → Team → Office.
    list_filter = ("is_active", "team__office")

    # Campi su cui viene eseguita la ricerca testuale.
    # Coprono le informazioni anagrafiche e di contatto principali.
    search_fields = ("first_name", "last_name", "email")

    # Campi impostati in sola lettura perché gestiti automaticamente da Django.
    # 'created_at' usa auto_now_add (impostato solo alla creazione),
    # 'updated_at' usa auto_now (aggiornato ad ogni salvataggio).
    # Mostrarli come readonly permette di consultarli senza poterli modificare.
    readonly_fields = ("created_at", "updated_at")


# ---------------------------------------------------------------------------
# Admin per il modello EmailTemplate (Template email configurabile)
# ---------------------------------------------------------------------------

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    """
    Configurazione admin per i template email.

    Il flag 'is_default' viene evidenziato nell'elenco per rendere
    immediatamente visibile quale template è attualmente quello predefinito.
    """

    # Colonne mostrate nell'elenco: nome, flag default e date di gestione.
    list_display = ("name", "is_default", "created_at", "updated_at")

    # Filtro per template predefinito: utile per identificare subito il template attivo.
    list_filter = ("is_default",)


# ---------------------------------------------------------------------------
# Admin per il modello SendLog (Log di un invio giornaliero)
# ---------------------------------------------------------------------------

@admin.register(SendLog)
class SendLogAdmin(admin.ModelAdmin):
    """
    Configurazione admin per i log degli invii giornalieri.

    L'elenco mostra le informazioni essenziali per monitorare l'andamento
    del servizio: data, orario di avvio, stato e statistiche di invio.
    Il filtro per stato permette di trovare rapidamente gli invii falliti.
    Il campo 'triggered_at' è in sola lettura perché impostato automaticamente
    da Django al momento della creazione del record (auto_now_add=True).
    """

    # Colonne mostrate nell'elenco dei log di invio.
    list_display = (
        "send_date",          # Data a cui si riferisce il run
        "triggered_at",       # Data e ora esatta di avvio del task
        "status",             # Stato corrente (PENDING/RUNNING/COMPLETED/FAILED)
        "total_recipients",   # Numero totale di email inviate
        "total_celebrants",   # Numero di dipendenti festeggiati
    )

    # Filtro laterale per stato: permette di isolare rapidamente gli invii
    # falliti (FAILED) o quelli in esecuzione (RUNNING).
    list_filter = ("status",)

    # 'triggered_at' è in sola lettura perché impostato automaticamente
    # da Django con auto_now_add=True al momento della creazione del record.
    readonly_fields = ("triggered_at",)


# ---------------------------------------------------------------------------
# Admin per il modello SendLogEntry (Riga del log: singola email inviata)
# ---------------------------------------------------------------------------

@admin.register(SendLogEntry)
class SendLogEntryAdmin(admin.ModelAdmin):
    """
    Configurazione admin per le righe dei log di invio.

    Ogni riga corrisponde a un'email inviata a un singolo destinatario.
    La visualizzazione è pensata per il debugging: mostra destinatario,
    log di riferimento, esito e orario di invio.
    """

    # Colonne mostrate nell'elenco delle righe di log.
    list_display = ("recipient", "log", "success", "sent_at")

    # Filtro per esito: permette di trovare rapidamente le email fallite.
    list_filter = ("success",)
