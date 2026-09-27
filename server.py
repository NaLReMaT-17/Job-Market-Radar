from __future__ import annotations

import json
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

from src.collect import collect_all_roles, DATA_DIR, JSON_FILE

HOST = "127.0.0.1"
PORT = 8000

_state = {"running": False, "message": "Готов", "count": 0}
_lock = threading.Lock()


class Handler(SimpleHTTPRequestHandler):
    # --- GET ------------------------------------------------------------------
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/vacancies":
            self._json(self._load_vacancies())
        elif parsed.path == "/api/status":
            self._json(_state)
        else:
            # Статика (app.html, data/*.json и т.д.)
            super().do_GET()

    # --- POST -----------------------------------------------------------------
    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/collect":
            self._handle_collect()
        else:
            self.send_error(404, "Not found")

    # --- Внутренняя логика ----------------------------------------------------
    def _handle_collect(self):
        with _lock:
            if _state["running"]:
                self._json({"error": "already_running"}, status=409)
                return
            _state["running"] = True
            _state["message"] = "Сбор запущен..."

        threading.Thread(target=self._run_collect, daemon=True).start()
        self._json({"status": "started"})

    def _run_collect(self):
        try:
            data = collect_all_roles()
            _state["count"] = len(data)
            _state["message"] = f"Готово: {len(data)} вакансий"
        except Exception as e:
            _state["message"] = f"Ошибка: {e}"
        finally:
            _state["running"] = False

    def _load_vacancies(self):
        if JSON_FILE.exists():
            try:
                return json.loads(JSON_FILE.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _json(self, obj, status: int = 200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # приглушаем шум от каждого GET-а
        pass


def run():
    # Создаём папку data заранее
    DATA_DIR.mkdir(exist_ok=True)

    server = HTTPServer((HOST, PORT), Handler)
    print(f"▶ Сервер: http://{HOST}:{PORT}/app.html")
    print(f"▶ Сбор запускается кнопкой в приложении или: python -m src.collect")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹ Остановлено.")
        server.server_close()


if __name__ == "__main__":
    run()