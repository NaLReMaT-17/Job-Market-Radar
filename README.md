# 📡 Job Market Radar

Аналитический дашборд для исследования рынка IT-вакансий на основе
открытого API портала «Работа России» (opendata.trudvsem.ru).

## Что внутри

| Файл | Назначение |
|---|---|
| `src/collect.py` | Python-скрипт сбора: Trudvsem → `data/latest.json/csv/parquet` |
| `server.py` | Локальный HTTP-сервер (stdlib), отдаёт статику и API |
| `app.html` | Дашборд на Tailwind + Chart.js |
| `.github/workflows/update-data.yml` | Авто-обновление данных по расписанию |

## Требования

- Python 3.11+
- pip

## Быстрый старт

```bash
git clone https://github.com/<ваш-логин>/job-market-radar.git
cd job-market-radar

python -m venv .venv
# Windows:
.\.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
python server.py
```

Откройте **http://127.0.0.1:8000/app.html**.

При первом открытии приложение:
- если в `data/latest.json` уже есть снапшот (обычно есть — его коммитит GitHub Actions) — покажет его сразу;
- если файла нет — автоматически запустит сбор.

Кнопка **«Собрать данные»** форсит новый сбор с Trudvsem в любой момент.

## Автономный сбор (без UI)

```bash
python -m src.collect
```

Результат: `data/latest.json`, `data/latest.csv`, `data/latest.parquet`.

## Автоматическое обновление данных

Файл `.github/workflows/update-data.yml` запускает сбор:
- раз в сутки в 03:00 UTC (= 06:00 МСК),
- вручную через вкладку **Actions → Update vacancy data → Run workflow**.

После сбора workflow коммитит `data/latest.json` и `data/latest.csv` в `main`.

Чтобы получить свежие данные локально:

```bash
git pull
python server.py
```

## Источник данных

- API: <https://opendata.trudvsem.ru/api/v1/vacancies>
- Авторизация: не требуется
- Лимиты: до 10 000 записей за раз, пауза 0.5 с между запросами

## Ограничения методологии

- **Навыки** извлекаются эвристически (regex по тексту описания), а не приходят готовым списком.
- **Опыт работы** в Trudvsem часто не заполнен.
- **Медианы зарплат** считаются только по вакансиям с явно указанной вилкой.
- **Навыки пересекаются** — сумма их долей не равна 100%.

## Лицензия

MIT
