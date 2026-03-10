"""
Modulo tasks.py per l'app "newsletter" del servizio di birthday newsletter aziendale.

Questo modulo definisce il background task che viene eseguito dal Django Task Framework
(django-tasks, che implementa la specifica DEPS-0014 / Django 6.0 Task Framework).

Nota sul meccanismo di scheduling:
    Senza un sistema di scheduling giornaliero reale (es. cron, Celery Beat), il task
    viene accodato manualmente tramite l'endpoint API di trigger. Il Django Task Framework
    si occupa dell'esecuzione asincrona in background tramite il backend configurato
    (in questo progetto: DatabaseBackend).
"""

import logging
from datetime import date

from django_tasks import task

from .services import send_birthday_newsletter

# Logger del modulo: usa il nome del modulo come identificatore nei log di sistema.
# Permette di filtrare e configurare il logging separatamente per questo modulo.
logger = logging.getLogger(__name__)


@task()
def run_birthday_newsletter(reference_date_str=None, template_id=None):
    """
    Task asincrono per l'invio della newsletter di compleanno.

    Viene registrato nel Django Task Framework tramite il decoratore @task() e può
    essere accodato programmaticamente (es. dall'endpoint API di trigger) oppure
    schedulato tramite un sistema esterno (cron, ecc.).

    Nota sui parametri:
        Il Django Task Framework serializza i parametri come JSON prima di salvarli
        nel backend (database). Per questo motivo le date devono essere passate come
        stringhe nel formato ISO "YYYY-MM-DD" e non come oggetti datetime.date.

    Args:
        reference_date_str: str | None – data di riferimento nel formato "YYYY-MM-DD".
                            Se None, il servizio usa la data odierna.
        template_id: int | None – ID del template email da usare.
                     Se None, viene usato il template predefinito.
    """
    logger.info(
        f"[Task] Avvio run_birthday_newsletter – reference_date_str={reference_date_str!r}, "
        f"template_id={template_id!r}"
    )

    try:
        # I task Django serializzano i parametri come JSON, quindi le date
        # devono essere passate come stringhe e convertite qui in oggetti date.
        if reference_date_str is not None:
            reference_date = date.fromisoformat(reference_date_str)
        else:
            reference_date = None

        send_log = send_birthday_newsletter(reference_date, template_id)

        logger.info(
            f"[Task] run_birthday_newsletter completato – SendLog #{send_log.pk}, "
            f"status={send_log.status}"
        )
    except Exception:
        # Logga l'errore: il framework registra comunque il fallimento del task
        # e lo marca come FAILED nel proprio backend.
        logger.exception(
            f"[Task] Errore critico in run_birthday_newsletter – "
            f"reference_date_str={reference_date_str!r}, template_id={template_id!r}"
        )
        raise
