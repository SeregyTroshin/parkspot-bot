import requests
import re
from datetime import datetime
from config import PARKSPOT_URL


def extract_text(html: str) -> str:
    """Извлекает текст из HTML, убирая теги"""
    # Убираем script и style
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Убираем теги
    text = re.sub(r'<[^>]+>', ' ', html)
    # Убираем лишние пробелы
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def parse_car_number(car_number: str) -> tuple[str, str]:
    """
    Разбивает номер машины на номер и регион.
    'А606ВО 797' -> ('А606ВО', '797')
    'А606ВО797' -> ('А606ВО', '797')
    """
    # Убираем пробелы и разделяем
    car_number = car_number.replace(" ", "")
    # Номер - первые 6 символов, регион - остальные
    regnum = car_number[:6]
    regreg = car_number[6:]
    return regnum, regreg


async def submit_pass(car_number: str, car_model: str, entry_time: datetime) -> dict:
    """
    Отправляет заявку на пропуск через сайт parkspot.ru

    Args:
        car_number: Номер машины (например "А606ВО 797")
        car_model: Модель машины (например "Тойота")
        entry_time: Время въезда

    Returns:
        dict с результатом: {"success": bool, "message": str}
    """
    try:
        session = requests.Session()

        # Получаем страницу для cookies
        resp = session.get(PARKSPOT_URL, timeout=10)
        resp.raise_for_status()

        # Разбираем номер на части
        regnum, regreg = parse_car_number(car_number)

        # Формируем данные формы
        time_str = entry_time.strftime("%Y-%m-%dT%H:%M")

        data = {
            "regnum": regnum,           # Номер без региона (А606ВО)
            "regreg": regreg,           # Регион (797)
            "MODEL_CAR": car_model,     # Модель
            "PAS_PLAN_FROM": time_str,  # Время въезда
        }

        # Отправляем на правильный endpoint
        submit_url = PARKSPOT_URL.rstrip('/') + "/add_data_proc_7.php"
        resp = session.post(submit_url, data=data, timeout=10)

        # Извлекаем текст из ответа
        raw_text = extract_text(resp.text)

        # Ограничиваем длину для Telegram
        if len(raw_text) > 2000:
            raw_text = raw_text[:2000] + "..."

        if resp.status_code == 200:
            return {"success": True, "message": raw_text}
        else:
            return {"success": False, "message": f"HTTP {resp.status_code}: {raw_text}"}

    except requests.Timeout:
        return {"success": False, "message": "Таймаут соединения"}
    except requests.RequestException as e:
        return {"success": False, "message": f"Ошибка сети: {str(e)}"}
    except Exception as e:
        return {"success": False, "message": f"Ошибка: {str(e)}"}


async def test_connection() -> bool:
    """Проверяет доступность сайта"""
    try:
        resp = requests.get(PARKSPOT_URL, timeout=5)
        return resp.status_code == 200
    except:
        return False
