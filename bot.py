import asyncio
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from config import BOT_TOKEN, CARS, DEFAULT_CAR
from parkspot import submit_pass


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def parse_time(time_str: str) -> datetime | None:
    """
    Парсит время из строки. Поддерживает форматы:
    - 15:30
    - 15.30
    - 1530
    - завтра 15:30
    """
    time_str = time_str.strip().lower()
    now = datetime.now()
    target_date = now.date()

    # Проверяем "завтра"
    if "завтра" in time_str:
        target_date = (now + timedelta(days=1)).date()
        time_str = time_str.replace("завтра", "").strip()

    # Паттерны для времени
    patterns = [
        r"(\d{1,2})[:\.](\d{2})",  # 15:30 или 15.30
        r"^(\d{2})(\d{2})$",       # 1530
    ]

    for pattern in patterns:
        match = re.search(pattern, time_str)
        if match:
            hours, minutes = int(match.group(1)), int(match.group(2))
            if 0 <= hours <= 23 and 0 <= minutes <= 59:
                return datetime.combine(target_date, datetime.min.time().replace(hour=hours, minute=minutes))

    return None


def parse_message(text: str) -> tuple[str | None, datetime | None]:
    """
    Парсит сообщение пользователя.
    Возвращает (имя_машины, время)

    Форматы:
    - "15:30" -> (DEFAULT_CAR, время)
    - "секвойя 15:30" -> ("секвойя", время)
    """
    text = text.strip().lower()

    # Ищем имя машины в начале
    car_name = None
    for name in CARS.keys():
        if text.startswith(name):
            car_name = name
            text = text[len(name):].strip()
            break

    if car_name is None:
        car_name = DEFAULT_CAR

    # Парсим время
    entry_time = parse_time(text)

    return car_name, entry_time


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    cars_list = "\n".join([f"  - {name}: {data[0]} ({data[1]})" for name, data in CARS.items()])
    await message.answer(
        f"Привет! Я помогу заказать пропуск на parkspot.ru\n\n"
        f"Просто напиши время въезда:\n"
        f"  15:30 - пропуск на сегодня 15:30\n"
        f"  завтра 10:00 - пропуск на завтра\n\n"
        f"Доступные машины:\n{cars_list}\n\n"
        f"По умолчанию: {DEFAULT_CAR}\n\n"
        f"Пример: секвойя 15:30"
    )


@dp.message(Command("cars"))
async def cmd_cars(message: types.Message):
    cars_list = "\n".join([f"  {name}: {data[0]} ({data[1]})" for name, data in CARS.items()])
    await message.answer(f"Машины в базе:\n{cars_list}")


@dp.message()
async def handle_message(message: types.Message):
    text = message.text
    if not text:
        return

    car_name, entry_time = parse_message(text)

    if entry_time is None:
        await message.answer(
            "Не понял время. Примеры:\n"
            "  15:30\n"
            "  завтра 10:00\n"
            "  секвойя 18:45"
        )
        return

    if car_name not in CARS:
        await message.answer(f"Машина '{car_name}' не найдена в базе")
        return

    car_number, car_model = CARS[car_name]

    await message.answer(
        f"Оформляю пропуск...\n"
        f"Машина: {car_name} ({car_number}, {car_model})\n"
        f"Время: {entry_time.strftime('%d.%m.%Y %H:%M')}"
    )

    result = await submit_pass(car_number, car_model, entry_time)

    # Показываем точный ответ сайта
    response_text = result.get("message", "Нет ответа")

    if result["success"]:
        await message.answer(f"Ответ сайта:\n\n{response_text}")
    else:
        await message.answer(f"Ошибка:\n\n{response_text}")


async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
