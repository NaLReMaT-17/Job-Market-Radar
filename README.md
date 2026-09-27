# Job-Market-Radar

Аналитический дашборд для исследования рынка IT-вакансий на основе
открытого API портала «Работа России» (opendata.trudvsem.ru).

## Что внутри

- **`src/collect.py`** — Python-скрипт: собирает вакансии с Trudvsem,
  извлекает навыки из описаний, сохраняет в `data/latest.json`, `.csv`, `.parquet`.
- **`server.py`** — локальный HTTP-сервер (stdlib), отдаёт статику и три API:
  `POST /api/collect`, `GET /api/status`, `GET /api/vacancies`.
- **`app.html`** — дашборд на Tailwind + Chart.js: KPI, топ навыков,
  топ работодателей, список вакансий, экспорт CSV/JSON.

## Требования

- Python 3.11+
- pip

## Установка и запуск

```bash
# 1. Клонировать репозиторий
git clone https://github.com/<ваш-логин>/<репо>.git
cd <репо>

# 2. Создать виртуальное окружение
python -m venv .venv

# Windows:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Запустить сервер
python server.py
```

Откройте в браузере: **http://127.0.0.1:8000/app.html**

Кнопка «Собрать данные» запустит сбор с Trudvsem (30–90 секунд на 5 ролей).

## Автономный сбор без сервера

Если нужны только данные (без UI):

```bash
python -m src.collect
```

Результат: `data/latest.json`, `data/latest.csv`, `data/latest.parquet`.

## Источник данных

- API: https://opendata.trudvsem.ru/api/v1/vacancies
- Авторизация: не требуется
- Ограничения: до 10000 записей за раз, пауза 0.5 с между запросами

## Ограничения методологии

- **Навыки** извлекаются эвристически (regex по тексту описания),
  а не приходят готовым списком.
- **Опыт работы** в Trudvsem часто не заполнен.
- **Медианы зарплат** считаются только по вакансиям с явно указанной вилкой.
- **Навыки пересекаются** — сумма их долей не равна 100%.

## Лицензия

MIT (или ваша).
