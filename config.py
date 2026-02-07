import os

# Telegram Bot Token (установить в переменных окружения)
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен! Добавь переменную окружения.")

# База машин: имя -> (номер, модель)
CARS = {
    "секвойя": ("А606ВО 797", "Тойота"),
    "панама": ("У657НУ 797", "Порше"),
    "паджеро": ("К860НК 150", "Митсубиси"),
}

# Машина по умолчанию
DEFAULT_CAR = "секвойя"

# URL сайта
PARKSPOT_URL = "https://parkspot.ru/"
