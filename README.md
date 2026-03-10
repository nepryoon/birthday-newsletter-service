# birthday-newsletter-service

Servizio Django per l'invio automatico di email di auguri di compleanno ai dipendenti aziendali.

## Dati di esempio (fixture)

Il file `newsletter/fixtures/sample_data.json` contiene dati di esempio pronti all'uso per l'app `newsletter`.

### Cosa include

| Tipo          | N. | Dettagli |
|---------------|----|----------|
| **Office**    | 3  | Roma, Milano, Londra |
| **Team**      | 4  | Backend e Frontend (Roma), Data Science (Milano), DevOps (Londra) |
| **Employee**  | 15 | Nomi italiani e internazionali, distribuiti tra i team |
| **EmailTemplate** | 2 | Template predefinito + template alternativo |

### Dipendenti con compleanno oggi (10 marzo)

La fixture assume che la data corrente sia il **10 marzo** (l'anno non è rilevante: il servizio confronta solo giorno e mese). I due dipendenti con compleanno oggi sono:

| pk | Nome          | Data di nascita |
|----|---------------|-----------------|
| 1  | Marco Rossi   | 1990-03-10      |
| 2  | Laura Bianchi | 1985-03-10      |

### Caricare la fixture

```bash
python manage.py migrate
python manage.py loaddata newsletter/fixtures/sample_data.json
```

### Adattare le date di compleanno a oggi

Se si utilizza la fixture in una data diversa dal 10 marzo, è necessario aggiornare manualmente le date di nascita dei dipendenti "festeggiati" affinché corrispondano al giorno odierno.

**Esempio:** se oggi è il **25 luglio**, aprire `newsletter/fixtures/sample_data.json` e sostituire le date dei dipendenti con pk 1 e pk 2:

```json
{ "birth_date": "1990-03-10" }  →  { "birth_date": "1990-07-25" }
{ "birth_date": "1985-03-10" }  →  { "birth_date": "1985-07-25" }
```

In alternativa, è possibile aggiornare le date direttamente nel database dopo aver caricato la fixture:

```bash
python manage.py shell -c "
from newsletter.models import Employee
from datetime import date
today = date.today()
Employee.objects.filter(pk=1).update(birth_date=today.replace(year=1990))
Employee.objects.filter(pk=2).update(birth_date=today.replace(year=1985))
"
```