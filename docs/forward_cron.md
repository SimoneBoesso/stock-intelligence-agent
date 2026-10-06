# Cron: forward-test daily job

Come schedulare `scripts/forward_daily.py` sui giorni lavorativi.

Pipeline eseguita dal job: Finnhub + GDELT → news index → prices/labels → `forward_resolve` → `forward_log` → `forward_report`.

## Prerequisiti

- Repo clonato, venv in `.venv`
- File `.env` in root con `GROQ_API_KEY` e `FINNHUB_API_KEY`
- Directory `logs/` presente (oppure creata al primo run se lo script la crea; l’output cron usa `logs/forward_daily.out`)

Prova manuale prima del cron:

```bash
cd /home/simone/Scrivania/stock-intelligence-agent
.venv/bin/python scripts/forward_daily.py --tickers AAPL,MSFT,PG
```

## Setup

```bash
crontab -e
```

La prima volta il sistema può chiedere **quale editor** usare (`1`–`5`). Scegli un numero (es. `1` per nano), **poi** incolla la riga cron nel file che si apre — non nel prompt `Choose 1-5`.

In nano: salva con `Ctrl+O`, Invio, esci con `Ctrl+X`.

Verifica:

```bash
crontab -l
```

## Riga consigliata

Lun–ven alle 18:30 (ora locale della macchina):

```cron
30 18 * * 1-5 cd /home/simone/Scrivania/stock-intelligence-agent && .venv/bin/python scripts/forward_daily.py --tickers AAPL,MSFT,PG >> logs/forward_daily.out 2>&1
```

Adatta path e ticker se serve. Per l’universo intero ometti `--tickers …`.

## Spiegazione del comando

### Quando (i 5 campi cron)

`30 18 * * 1-5`

| Campo | Valore | Significato |
|---|---|---|
| minuto | `30` | al minuto 30 |
| ora | `18` | alle 18 |
| giorno del mese | `*` | ogni giorno del mese |
| mese | `*` | ogni mese |
| giorno della settimana | `1-5` | lunedì–venerdì |

→ ogni giorno lavorativo alle **18:30**.

### Cosa (shell)

1. **`cd …/stock-intelligence-agent`** — entra nella root del repo (path relativi, `.venv`, `.env`).
2. **`&&`** — esegue il resto solo se il `cd` riesce.
3. **`.venv/bin/python scripts/forward_daily.py --tickers AAPL,MSFT,PG`** — Python del venv; pipeline forward solo su quei ticker.
4. **`>> logs/forward_daily.out`** — append dello stdout su quel file.
5. **`2>&1`** — redirect anche dello stderr nello stesso file (errori nel log).

## Dove guardare

| File | Contenuto |
|---|---|
| `logs/forward_daily.out` | stdout/stderr del job cron |
| `logs/forward_log.log` | log di `forward_log.py` |
| `logs/forward_resolve.log` | log di `forward_resolve.py` |
| `data/processed/forward_forecasts.parquet` | registro previsioni (label dopo ~30 giorni di trading) |

## Opzioni utili di `forward_daily.py`

| Flag | Effetto |
|---|---|
| `--tickers AAPL,MSFT` | limita GDELT + log a quei ticker |
| `--skip-news` / `--skip-prices` / `--skip-resolve` / `--skip-log` / `--skip-report` | salta uno step |
| `--date YYYY-MM-DD` | override data forecast |
| `--k` / `--sleep` | top-k RAG e pausa tra ticker (passati a `forward_log`) |

## Note

- Cron usa l’ora del sistema (`timedatectl` per verificare timezone).
- L’ambiente di cron è minimale: usa sempre il path assoluto al repo e `.venv/bin/python`, non `python` generico.
- Le label delle previsioni si popolano quando esistono in `labels.parquet` (di solito dopo ~30 giorni di trading), tipicamente al run successivo di `forward_resolve` dentro questo job.
