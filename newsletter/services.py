"""
Modulo services.py per l'app "newsletter" del servizio di birthday newsletter aziendale.

Questo modulo contiene tutta la logica di business isolata dalle view e dai task,
seguendo il principio della separazione delle responsabilità (Separation of Concerns).
Le funzioni qui definite sono chiamate dai task asincroni e potenzialmente dalle view
dell'API, evitando duplicazione di logica e facilitando i test unitari.
"""

import calendar
import logging
from datetime import date, datetime

from django.core.mail import send_mail

from .models import Employee, EmailTemplate, SendLog, SendLogEntry

# Logger del modulo: usa il nome del modulo come identificatore nei log di sistema.
# Permette di filtrare e configurare il logging separatamente per questo modulo.
logger = logging.getLogger(__name__)

# Nomi dei mesi in italiano per la formattazione delle date nelle email.
# L'indice 0 è una stringa vuota perché i mesi vanno da 1 a 12.
_MESI_ITALIANI = [
    "",
    "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
]


def _format_date_italian(d: date) -> str:
    """
    Formatta una data nel formato italiano esteso (es. "10 marzo 2026").

    Usata internamente per costruire il placeholder {date} nel contesto
    dei template email.
    """
    return f"{d.day} {_MESI_ITALIANI[d.month]} {d.year}"


# ---------------------------------------------------------------------------
# 1. get_todays_celebrants
# ---------------------------------------------------------------------------

def get_todays_celebrants(reference_date=None):
    """
    Restituisce un QuerySet di Employee attivi che compiono gli anni nella data indicata.

    Se reference_date è None, usa la data odierna (date.today()).

    Gestisce il caso speciale del 29 febbraio: se la reference_date cade il
    28 febbraio di un anno NON bisestile, include anche i dipendenti nati il
    29 febbraio, poiché in quell'anno non esiste il 29 febbraio e il loro
    compleanno viene festeggiato il 28 febbraio.

    Args:
        reference_date: date | None – data di riferimento per la ricerca dei compleanni.

    Returns:
        QuerySet[Employee] – dipendenti attivi che compiono gli anni nella data indicata.
    """
    # Usa la data odierna se non viene fornita una data di riferimento
    if reference_date is None:
        reference_date = date.today()

    # Cerca i dipendenti attivi nati nello stesso giorno e mese della reference_date
    celebrants = Employee.objects.filter(
        is_active=True,
        birth_date__month=reference_date.month,
        birth_date__day=reference_date.day,
    )

    # Gestione del caso 29 febbraio per anni non bisestili:
    # se reference_date è il 28 febbraio e l'anno non è bisestile,
    # aggiunge i dipendenti nati il 29 febbraio (festeggiati il 28 in questo anno).
    if (
        reference_date.month == 2
        and reference_date.day == 28
        and not calendar.isleap(reference_date.year)
    ):
        # Dipendenti nati il 29 febbraio che festeggiano il 28 negli anni non bisestili
        feb29_celebrants = Employee.objects.filter(
            is_active=True,
            birth_date__month=2,
            birth_date__day=29,
        )
        # Unisce i due QuerySet con l'operatore | (OR a livello SQL) per evitare duplicati
        celebrants = celebrants | feb29_celebrants

    return celebrants


# ---------------------------------------------------------------------------
# 2. get_active_recipients
# ---------------------------------------------------------------------------

def get_active_recipients():
    """
    Restituisce un QuerySet di tutti i dipendenti attivi con email valida.

    Nota di business (MVP): in questa versione tutti i dipendenti attivi ricevono
    la newsletter di compleanno. In una versione di produzione si potrebbe filtrare
    per ruolo, team, preferenze di notifica dell'utente, o sede aziendale.

    Returns:
        QuerySet[Employee] – dipendenti attivi con indirizzo email non vuoto.
    """
    # Filtra i dipendenti attivi con email presente e non vuota.
    # EmailField garantisce già la validità del formato, ma exclude(email="")
    # rimuove eventuali stringhe vuote che potrebbero essere presenti.
    return Employee.objects.filter(
        is_active=True,
        email__isnull=False,
    ).exclude(email="")


# ---------------------------------------------------------------------------
# 3. get_default_template
# ---------------------------------------------------------------------------

def get_default_template():
    """
    Restituisce l'EmailTemplate marcato come predefinito (is_default=True).

    Restituisce None se nel sistema non esiste nessun template predefinito.
    In caso di anomalia con più template marcati come predefiniti, restituisce
    il più recente (ordinato per created_at decrescente), garantendo un
    comportamento deterministico anche in caso di dati inconsistenti.

    Returns:
        EmailTemplate | None – il template predefinito o None se non esiste.
    """
    # Filtra i template con is_default=True e ordina per data di creazione decrescente.
    # In condizioni normali esiste un solo template predefinito; in caso anomalo
    # (più template default) viene restituito il più recente.
    templates = EmailTemplate.objects.filter(is_default=True).order_by("-created_at")

    # first() restituisce il primo oggetto oppure None se il QuerySet è vuoto
    return templates.first()


# ---------------------------------------------------------------------------
# 4. render_email_for_recipient
# ---------------------------------------------------------------------------

def render_email_for_recipient(recipient, celebrants, template, reference_date) -> tuple:
    """
    Renderizza l'email per un specifico destinatario con i dati dei festeggiati.

    Costruisce il dizionario di contesto con tutti i placeholder supportati
    dal template e delega la sostituzione ai metodi render_subject/render_body
    del modello EmailTemplate.

    Placeholder supportati:
        {recipient_name}  → nome del destinatario
        {date}            → data formattata in italiano (es. "10 marzo 2026")
        {team_name}       → nome del team del destinatario (o "Tutti" se senza team)
        {office_name}     → nome della sede del team (o "N/A" se non disponibile)
        {celebrants_list} → lista testuale dei festeggiati con nome e anni

    Args:
        recipient: Employee – il dipendente destinatario dell'email.
        celebrants: QuerySet[Employee] – i dipendenti che compiono gli anni oggi.
        template: EmailTemplate – il template da usare per l'email.
        reference_date: date – la data di riferimento per l'invio.

    Returns:
        tuple[str, str] – (subject_rendered, body_rendered) con i placeholder sostituiti.
    """
    # Determina il nome del team del destinatario.
    # Se il dipendente non appartiene a nessun team, usa "Tutti" come valore di default.
    if recipient.team:
        team_name = recipient.team.name
        # Determina il nome della sede associata al team.
        # Gestione difensiva: team.office potrebbe teoricamente essere None.
        office_name = recipient.team.office.name if recipient.team.office else "N/A"
    else:
        # Nessun team assegnato: usa valori di default descrittivi
        team_name = "Tutti"
        office_name = "N/A"

    # Costruisce la lista testuale dei festeggiati nel formato richiesto:
    # "- Nome Cognome (X anni)\n- Nome Cognome (Y anni)"
    celebrants_lines = []
    for celebrant in celebrants:
        # Calcola l'età del festeggiato alla data di riferimento
        birth = celebrant.birth_date

        # Gestione del 29 febbraio: se il festeggiato è nato il 29/02
        # e l'anno di riferimento non è bisestile, usa il 28/02 per il calcolo
        try:
            birthday_this_year = birth.replace(year=reference_date.year)
        except ValueError:
            # ValueError si verifica quando birth_date è il 29/02
            # e l'anno di riferimento non è bisestile
            birthday_this_year = birth.replace(year=reference_date.year, day=28)

        # Calcola l'età come differenza tra anni.
        # I festeggiati hanno per definizione il compleanno oggi (birthday_this_year == reference_date),
        # quindi l'anno compiuto è esattamente reference_date.year - birth.year.
        age = reference_date.year - birth.year

        celebrants_lines.append(
            f"- {celebrant.first_name} {celebrant.last_name} ({age} anni)"
        )

    # Unisce le righe dei festeggiati con un newline
    celebrants_list = "\n".join(celebrants_lines)

    # Costruisce il dizionario di contesto con tutti i placeholder del template
    context = {
        "recipient_name": recipient.first_name,
        "date": _format_date_italian(reference_date),
        "team_name": team_name,
        "office_name": office_name,
        "celebrants_list": celebrants_list,
    }

    # Delega la sostituzione dei placeholder ai metodi del modello EmailTemplate.
    # I placeholder non presenti nel contesto vengono lasciati invariati.
    subject_rendered = template.render_subject(context)
    body_rendered = template.render_body(context)

    return subject_rendered, body_rendered


# ---------------------------------------------------------------------------
# 5. send_birthday_newsletter
# ---------------------------------------------------------------------------

def send_birthday_newsletter(reference_date=None, template_id=None) -> SendLog:
    """
    Funzione orchestratrice principale per l'invio della newsletter di compleanno.

    Questa funzione viene chiamata dal task asincrono giornaliero e gestisce
    l'intero flusso: dalla ricerca dei festeggiati all'invio delle email,
    passando per la creazione e l'aggiornamento dettagliato del SendLog.

    Flusso operativo:
        1. Crea un SendLog con status=RUNNING
        2. Trova i festeggiati per la data di riferimento
        3. Se non ci sono festeggiati, chiude il log con COMPLETED (0 email inviate)
        4. Recupera il template (per ID o quello predefinito)
        5. Se non esiste un template, fallisce con FAILED
        6. Per ogni destinatario attivo: renderizza e invia l'email, logga il risultato
        7. Aggiorna il SendLog con i totali e status=COMPLETED
        8. In caso di errore critico, aggiorna lo status a FAILED

    Args:
        reference_date: date | None – data di riferimento (default: oggi).
        template_id: int | None – ID del template da usare (default: template predefinito).

    Returns:
        SendLog – il log aggiornato con lo stato finale dell'operazione.
    """
    # Usa la data odierna se non specificata
    if reference_date is None:
        reference_date = date.today()

    # Crea subito un SendLog con status=RUNNING per tracciare l'inizio dell'operazione.
    # Questo permette di rilevare task bloccati (rimasti RUNNING troppo a lungo) in produzione.
    log = SendLog.objects.create(
        send_date=reference_date,
        status=SendLog.Status.RUNNING,
    )
    logger.info(
        f"[SendLog #{log.pk}] Avvio invio newsletter per il {reference_date}"
    )

    try:
        # --- Passo 1: Trova i festeggiati per la data di riferimento ---
        celebrants = get_todays_celebrants(reference_date)
        total_celebrants = celebrants.count()
        logger.info(
            f"[SendLog #{log.pk}] Trovati {total_celebrants} festeggiati per il {reference_date}"
        )

        # --- Passo 2: Nessun festeggiato → chiude il log senza inviare email ---
        if total_celebrants == 0:
            log.status = SendLog.Status.COMPLETED
            log.total_celebrants = 0
            log.total_recipients = 0
            log.save()
            logger.info(
                f"[SendLog #{log.pk}] Nessun festeggiato trovato. Invio saltato."
            )
            return log

        # --- Passo 3: Recupera il template da usare ---
        # Se template_id è specificato, cerca il template per ID primario;
        # altrimenti usa il template predefinito del sistema.
        if template_id is not None:
            try:
                template = EmailTemplate.objects.get(pk=template_id)
            except EmailTemplate.DoesNotExist:
                error_msg = (
                    f"Template con ID {template_id} non trovato nel database."
                )
                logger.error(f"[SendLog #{log.pk}] {error_msg}")
                log.status = SendLog.Status.FAILED
                log.error_message = error_msg
                log.save()
                return log
        else:
            # Nessun ID specificato: usa il template predefinito
            template = get_default_template()

        # --- Passo 4: Verifica che un template sia disponibile ---
        if template is None:
            error_msg = (
                "Nessun template email predefinito configurato nel sistema. "
                "Impostare is_default=True su almeno un EmailTemplate."
            )
            logger.error(f"[SendLog #{log.pk}] {error_msg}")
            log.status = SendLog.Status.FAILED
            log.error_message = error_msg
            log.save()
            return log

        # Aggiorna il log con il riferimento al template che verrà utilizzato
        log.template_used = template
        log.save()

        # --- Passo 5: Invia l'email a ogni destinatario attivo ---
        recipients = get_active_recipients()
        total_recipients = 0

        for recipient in recipients:
            try:
                # Renderizza l'email personalizzata per questo destinatario
                subject, body = render_email_for_recipient(
                    recipient=recipient,
                    celebrants=celebrants,
                    template=template,
                    reference_date=reference_date,
                )

                # Invia l'email tramite il backend configurato in Django settings.
                # from_email=None usa il valore DEFAULT_FROM_EMAIL dalle settings.
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=None,
                    recipient_list=[recipient.email],
                    fail_silently=False,
                )

                # Crea la riga del log per questo invio con successo
                entry = SendLogEntry.objects.create(
                    log=log,
                    recipient=recipient,
                    success=True,
                )
                # Associa i festeggiati inclusi in questa email (relazione ManyToMany)
                entry.celebrants_included.set(celebrants)

                total_recipients += 1
                logger.info(
                    f"[SendLog #{log.pk}] Email inviata con successo a {recipient.email}"
                )

            except Exception as exc:
                # Cattura le eccezioni per singolo destinatario per non bloccare
                # l'invio agli altri destinatari. Ogni fallimento viene registrato
                # nel log ma non interrompe l'iterazione.
                error_detail = str(exc)
                logger.error(
                    f"[SendLog #{log.pk}] Errore nell'invio a {recipient.email}: {error_detail}"
                )

                # Crea la riga del log per questo invio fallito
                entry = SendLogEntry.objects.create(
                    log=log,
                    recipient=recipient,
                    success=False,
                    error_detail=error_detail,
                )
                # Associa comunque i festeggiati per tracciare il tentativo di invio
                entry.celebrants_included.set(celebrants)

        # --- Passo 6: Aggiorna il log con i totali e lo stato finale ---
        log.total_recipients = total_recipients
        log.total_celebrants = total_celebrants
        log.status = SendLog.Status.COMPLETED
        log.save()
        logger.info(
            f"[SendLog #{log.pk}] Invio completato: {total_recipients} email inviate, "
            f"{total_celebrants} festeggiati."
        )

    except Exception as exc:
        # Cattura eccezioni che bloccano l'intero processo (es. errore critico del DB).
        # In questo caso l'intero run viene marcato come FAILED con il messaggio di errore.
        error_msg = str(exc)
        logger.exception(
            f"[SendLog #{log.pk}] Errore critico durante l'invio: {error_msg}"
        )
        log.status = SendLog.Status.FAILED
        log.error_message = error_msg
        log.save()

    return log
