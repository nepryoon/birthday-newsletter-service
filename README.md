# Birthday Newsletter Service

Servizio Django per l'invio automatico di email di auguri di compleanno ai dipendenti aziendali. Il sistema identifica ogni giorno i dipendenti che compiono gli anni, seleziona il template email configurato come predefinito e invia una notifica personalizzata a tutti i colleghi attivi. L'invio avviene in modo asincrono tramite un worker dedicato, garantendo scalabilità e tracciabilità completa di ogni operazione.

---

## Stack Tecnologico

- **Python 3.11+**
- **Django 5.1** — framework web principale
- **Django REST Framework 3.15** — esposizione delle API REST
- **django-tasks 0.7** — gestione asincrona dei task con backend su database (DEPS-0014)
- **django-filter 24.x** — filtri avanzati sugli endpoint API
- **python-dateutil 2.9.x** — utilità per la gestione delle date

---

## Modello Dati

Il servizio è organizzato attorno a sei entità principali:

- **Office** — rappresenta una sede aziendale (es. Roma, Milano, Londra), con relativo fuso orario.
- **Team** — un gruppo di lavoro appartenente a una sede. Ogni team ha una relazione molti-a-uno con `Office`.
- **Employee** — il dipendente aziendale. Appartiene a un `Team` (opzionale), ha una data di nascita e un flag `is_active`. Espone proprietà calcolate come `age` e `is_birthday_today`. Gestisce in modo nativo i compleanni del 29 febbraio.
- **EmailTemplate** — il template testuale dell'email di auguri, con soggetto e corpo parametrizzabili tramite segnaposto (`{recipient_name}`, `{celebrants_list}`, `{date}`, `{team_name}`, `{office_name}`). Un solo template alla volta può essere marcato come `is_default`.
- **SendLog** — registro di ogni esecuzione del processo di invio newsletter (data, stato, numero di destinatari e festeggiati, eventuale messaggio di errore).
- **SendLogEntry** — riga di dettaglio per ogni email individuale inviata nell'ambito di un `SendLog`, con riferimento al destinatario, ai festeggiati inclusi nel messaggio e all'esito dell'invio.

---

## Istruzioni di Avvio

1. **Clona il repository**

   ```bash
   git clone https://github.com/nepryoon/birthday-newsletter-service.git
   cd birthday-newsletter-service
   ```

2. **Crea e attiva un ambiente virtuale**

   ```bash
   python -m venv venv
   source venv/bin/activate        # Linux / macOS
   venv\Scripts\activate           # Windows
   ```

3. **Installa le dipendenze**

   ```bash
   pip install -r requirements.txt
   ```

4. **Applica le migrazioni del database**

   ```bash
   python manage.py migrate
   ```

5. **Carica i dati di esempio**

   ```bash
   python manage.py loaddata newsletter/fixtures/sample_data.json
   ```

   La fixture include 3 sedi, 4 team, 15 dipendenti e 2 template email. I dipendenti con pk 1 (Marco Rossi) e pk 2 (Laura Bianchi) hanno il compleanno il **10 marzo**.

6. **Avvia il server Django**

   ```bash
   python manage.py runserver
   ```

   Il server sarà disponibile su `http://127.0.0.1:8000/`.

7. **Avvia il worker dei task** *(in un secondo terminale, con il virtualenv attivato)*

   ```bash
   python manage.py db_worker
   ```

   Questo processo rimane in ascolto sul database e processa i task accodati tramite l'API (es. l'endpoint `POST /api/newsletter/trigger/`). Senza il worker attivo, i task vengono salvati in stato `PENDING` ma non eseguiti.

---

## Endpoints API

| Metodo | URL | Descrizione |
|---|---|---|
| GET / POST | `/api/employees/` | Lista e creazione dipendenti |
| GET / PUT / PATCH / DELETE | `/api/employees/{id}/` | Dettaglio e modifica dipendente |
| GET | `/api/employees/birthdays-today/` | Festeggiati di oggi |
| GET / POST | `/api/offices/` | Gestione sedi |
| GET / PUT / PATCH / DELETE | `/api/offices/{id}/` | Dettaglio e modifica sede |
| GET / POST | `/api/teams/` | Gestione team |
| GET / PUT / PATCH / DELETE | `/api/teams/{id}/` | Dettaglio e modifica team |
| GET / POST | `/api/templates/` | Gestione template email |
| GET / PUT / PATCH / DELETE | `/api/templates/{id}/` | Dettaglio e modifica template |
| POST | `/api/templates/{id}/set-default/` | Imposta template come predefinito |
| POST | `/api/newsletter/trigger/` | Trigger manuale invio newsletter |
| GET | `/api/newsletter/celebrants-today/` | Consulta i festeggiati di oggi |
| GET | `/api/send-logs/` | Storico degli invii |
| GET | `/api/send-logs/{id}/` | Dettaglio di un singolo invio |

---

## Esempi di Chiamate API (curl)

### 1. Creazione di un dipendente

```bash
# Crea un nuovo dipendente attivo nel team con id=1
curl -s -X POST http://127.0.0.1:8000/api/employees/ \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Giulia",
    "last_name": "Conti",
    "email": "giulia.conti@azienda.com",
    "birth_date": "1995-03-10",
    "team": 1,
    "is_active": true
  }' | python -m json.tool
```

### 2. Lista dipendenti filtrati per team

```bash
# Restituisce solo i dipendenti appartenenti al team con id=1
curl -s "http://127.0.0.1:8000/api/employees/?team=1" | python -m json.tool
```

### 3. Trigger manuale della newsletter per oggi

```bash
# Accoda il task di invio newsletter per la data odierna,
# usando il template predefinito
curl -s -X POST http://127.0.0.1:8000/api/newsletter/trigger/ \
  -H "Content-Type: application/json" \
  -d '{}' | python -m json.tool
```

### 4. Trigger con data specifica

```bash
# Accoda il task di invio newsletter per il 10 marzo 2026,
# usando il template con id=1
curl -s -X POST http://127.0.0.1:8000/api/newsletter/trigger/ \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-03-10",
    "template_id": 1
  }' | python -m json.tool
```

### 5. Consultazione storico invii

```bash
# Restituisce la lista paginata di tutti i log di invio
curl -s "http://127.0.0.1:8000/api/send-logs/" | python -m json.tool
```

---

## Come Testare l'Invio Email

Il progetto è configurato con il backend email **Console** (`django.core.mail.backends.console.EmailBackend`). Le email non vengono consegnate realmente: il loro contenuto viene stampato direttamente nel terminale dove è in esecuzione `python manage.py runserver`.

Per testare un invio completo:

1. Assicurarsi che il server (`runserver`) e il worker (`db_worker`) siano entrambi in esecuzione in due terminali separati.
2. Inviare la richiesta di trigger tramite curl (vedi esempi sopra).
3. Osservare l'output nel terminale del server. Apparirà un blocco simile al seguente per ogni email inviata:

```
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Subject: =?utf-8?b?8J+OgiBDb21wbGVhbm5pIGRlbCAxMCBtYXJ6byAyMDI2IC0gVGVhbSBCYWNrZW5k?=
From: newsletter@azienda.com
To: mario.ferrari@azienda.com
Date: Tue, 10 Mar 2026 09:00:00 +0100
Message-ID: <...>

Ciao Mario,

Oggi festeggiamo i seguenti colleghi:

- Marco Rossi (36 anni)
- Laura Bianchi (41 anni)

Unisciti a noi nel fare gli auguri!

Il Team HR
-------------------------------------------------------------------------------
```

---

## Regole di Business Implementate

- **Chi riceve le notifiche**: tutti i dipendenti con `is_active=True` ricevono l'email di auguri, indipendentemente dal team o dalla sede.
- **Dipendenti inattivi**: i dipendenti con `is_active=False` sono esclusi sia dalla lista dei destinatari che da quella dei festeggiati. Non compaiono in nessun contesto di invio.
- **Gestione del 29 febbraio**: i dipendenti nati il 29 febbraio vengono festeggiati il **28 febbraio** negli anni non bisestili, garantendo che non vengano mai saltati.
- **Template configurabile**: il sistema seleziona automaticamente il template marcato come `is_default=True`. È possibile cambiare il template predefinito in qualsiasi momento tramite l'endpoint `POST /api/templates/{id}/set-default/`.

---

## Dati di Esempio (fixture)

Il file `newsletter/fixtures/sample_data.json` include:

| Tipo | N. | Dettagli |
|---|---|---|
| **Office** | 3 | Roma, Milano, Londra |
| **Team** | 4 | Backend e Frontend (Roma), Data Science (Milano), DevOps (Londra) |
| **Employee** | 15 | Nomi italiani e internazionali, distribuiti tra i team |
| **EmailTemplate** | 2 | Template predefinito + template alternativo |

**Dipendenti con compleanno il 10 marzo** (utili per test immediati):

| pk | Nome | Data di nascita |
|---|---|---|
| 1 | Marco Rossi | 1990-03-10 |
| 2 | Laura Bianchi | 1985-03-10 |

Per adattare i festeggiati a una data diversa, aggiornare le date di nascita nel file JSON oppure via shell:

```bash
python manage.py shell -c "
from newsletter.models import Employee
from datetime import date
today = date.today()
Employee.objects.filter(pk=1).update(birth_date=today.replace(year=1990))
Employee.objects.filter(pk=2).update(birth_date=today.replace(year=1985))
"
```

---

## Idee per Miglioramenti Futuri

1. **Scheduling automatico** — integrare un job scheduler (es. Celery Beat, APScheduler o django-crontab) per eseguire automaticamente la newsletter ogni mattina senza intervento manuale.
2. **Filtro per team o sede** — consentire di inviare la newsletter solo ai membri di uno specifico team o sede, riducendo il volume di email nei contesti aziendali distribuiti.
3. **Preferenze di notifica** — aggiungere un campo per-dipendente che permetta di disattivare la ricezione delle email di auguri, rispettando la privacy e le preferenze individuali.
4. **Internazionalizzazione (i18n)** — supportare più lingue per i template email, selezionando automaticamente la lingua in base alla sede o al profilo del destinatario.
5. **Dashboard di monitoring** — realizzare un'interfaccia web (o integrare con strumenti come Grafana/Metabase) per visualizzare statistiche sugli invii, tassi di errore e trend nel tempo.
6. **Test coverage** — aggiungere una suite di test automatizzati (unit test e integration test) con coverage report, per garantire la robustezza del servizio durante le evoluzioni future.
7. **Autenticazione API** — proteggere gli endpoint con un sistema di autenticazione (es. Token Authentication o OAuth2/JWT) per un uso in ambienti non esclusivamente interni.