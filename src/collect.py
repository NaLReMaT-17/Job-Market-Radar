from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

import pandas as pd
import requests

# --- Логирование -------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# --- Константы ----------------------------------------------------------------
BASE_URL = "https://opendata.trudvsem.ru/api/v1/vacancies"
HEADERS = {"User-Agent": "JobMarketRadar/1.0"}

DATA_DIR = Path("data")
JSON_FILE = DATA_DIR / "latest.json"
CSV_FILE = DATA_DIR / "latest.csv"
PARQUET_FILE = DATA_DIR / "latest.parquet"

MAX_PAGES = 10
PER_PAGE = 100
DELAY = 0.5

DEFAULT_ROLES = [
    "Python Developer",
    "Frontend Developer",
    "Data Engineer",
    "DevOps",
    "QA Automation",
]

# Список технологий для извлечения навыков из текста описания
KNOWN_SKILLS = [
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Golang",
    "Rust", "PHP", "Ruby", "Kotlin", "Swift", "Scala",
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "ClickHouse", "Oracle",
    "Docker", "Kubernetes", "K8s",
    "Linux", "Bash", "Git", "CI/CD", "Ansible", "Terraform", "Jenkins",
    "React", "Vue", "Angular", "Next.js", "Node.js", "Express",
    "Django", "FastAPI", "Flask", "Spring", "Laravel",
    "HTML", "CSS", "SASS",
    "REST", "REST API", "GraphQL", "gRPC",
    "Kafka", "RabbitMQ", "Airflow", "Spark", "Hadoop",
    "TensorFlow", "PyTorch", "Pandas", "NumPy",
    "PyTest", "Selenium", "Playwright",
    "AWS", "Azure", "GCP", "Yandex Cloud",
    "Asyncio",
]


# --- Извлечение навыков и графика --------------------------------------------
def extract_skills(text: str) -> list[str]:
    """Ищет упоминания известных технологий в тексте."""
    if not text:
        return []
    found = set()
    for skill in KNOWN_SKILLS:
        # не матчим внутри слова: SQL не должен ловиться в NoSQL
        pattern = r"(?<![A-Za-zА-Яа-я])" + re.escape(skill) + r"(?![A-Za-zА-Яа-я])"
        if re.search(pattern, text, re.IGNORECASE):
            found.add(skill)
    return sorted(found)


def detect_schedule(name: str, description: str) -> str:
    """Пытается определить график по тексту (Trudvsem не отдаёт его структурно)."""
    blob = f"{name or ''} {description or ''}".lower()
    if "удален" in blob or "remote" in blob or "дистанц" in blob:
        return "remote"
    if "гибк" in blob or "flexible" in blob:
        return "flexible"
    if "смен" in blob or "shift" in blob:
        return "shift"
    return "fullDay"


def average_salary(sal_min, sal_max):
    """Среднее между salary_min и salary_max (если указаны)."""
    vals = [int(x) for x in (sal_min, sal_max) if x]
    if not vals:
        return None
    return sum(vals) // len(vals)


def normalize_vacancy(v: dict, role_name: str) -> dict:
    """Преобразует сырой объект Trudvsem в схему, которую ждёт HTML-приложение."""
    company = v.get("company") or {}
    region = v.get("region") or {}
    requirement = v.get("requirement") or {}

    name = v.get("job-name") or v.get("job_name") or ""

    # Текст для извлечения навыков и определения графика
    duty = v.get("duty") or ""
    qualification = requirement.get("qualification") or ""
    description_text = f"{duty}\n{qualification}"

    skills = extract_skills(f"{name}\n{description_text}")
    schedule = detect_schedule(name, description_text)

    # Опыт — Trudvsem иногда отдаёт как объект {name: ...}, иногда как число
    experience = "Не указано"
    exp_field = requirement.get("experience")
    if isinstance(exp_field, dict):
        experience = exp_field.get("name") or experience
    elif isinstance(exp_field, str) and exp_field.strip():
        experience = exp_field

    return {
        "id": v.get("id"),
        "name": name,
        "role_name": role_name,
        "employer": company.get("name") or "Не указан",
        "area": region.get("name") or "Не указан",
        "sal_rub": average_salary(v.get("salary_min"), v.get("salary_max")),
        "schedule": schedule,
        "experience": experience,
        "skills": skills,
        "url": v.get("vac_url") or "",
        "source": "trudvsem",
    }


# --- Запросы к Trudvsem -------------------------------------------------------
def fetch_role(role: str) -> list[dict]:
    """Собирает вакансии по одной роли (пагинация через offset)."""
    vacancies: list[dict] = []

    for page in range(MAX_PAGES):
        params = {
            "text": role,
            "limit": PER_PAGE,
            "offset": page * PER_PAGE,
        }
        try:
            r = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=60)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logging.error(f"[{role}] ошибка запроса стр.{page}: {e}")
            break

        if str(data.get("status")) != "200":
            logging.error(f"[{role}] API status={data.get('status')} на стр.{page}")
            break

        raw = (data.get("results") or {}).get("vacancies") or []
        if not raw:
            break

        for item in raw:
            v = item.get("vacancy") or {}
            norm = normalize_vacancy(v, role)
            if norm["id"]:
                vacancies.append(norm)

        logging.info(f"[{role}] стр.{page + 1}: +{len(raw)} (итого {len(vacancies)})")

        if len(raw) < PER_PAGE:
            break
        time.sleep(DELAY)

    return vacancies


def collect_all_roles(roles: list[str] | None = None) -> list[dict]:
    """Собирает данные по всем ролям, дедуплицирует, сохраняет на диск."""
    roles = roles or DEFAULT_ROLES
    all_v: list[dict] = []

    logging.info("🚀 Сбор данных с портала «Работа России» (Trudvsem)...")
    for role in roles:
        logging.info(f"→ Роль: {role}")
        all_v.extend(fetch_role(role))

    # Дедупликация по id
    seen = set()
    unique = []
    for v in all_v:
        if v["id"] not in seen:
            seen.add(v["id"])
            unique.append(v)

    save_results(unique)
    logging.info(f"✅ Итого {len(unique)} уникальных вакансий сохранено.")
    return unique


def save_results(vacancies: list[dict]) -> None:
    DATA_DIR.mkdir(exist_ok=True)

    # 1) JSON — для HTML-приложения
    JSON_FILE.write_text(
        json.dumps(vacancies, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 2) CSV и Parquet — для Streamlit / аналитики
    df = pd.DataFrame(vacancies)
    # списки → строка, чтобы корректно легло в CSV
    if "skills" in df.columns:
        df_csv = df.copy()
        df_csv["skills"] = df_csv["skills"].apply(
            lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, list) else "[]"
        )
        df_csv.to_csv(CSV_FILE, index=False)

    df.to_parquet(PARQUET_FILE, index=False)

    logging.info(f"💾 Сохранено: {JSON_FILE}, {CSV_FILE}, {PARQUET_FILE}")


# --- Точка входа --------------------------------------------------------------
def main() -> None:
    collect_all_roles()


if __name__ == "__main__":
    main()