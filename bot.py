import asyncio
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import BOT_TOKEN
from database import (
    get_all_cars, get_car_by_name, get_car_by_id,
    add_car, delete_car_by_id,
    add_parking_order, get_active_orders, get_recent_orders
)
from parkspot import submit_pass


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Временное хранение времени для выбора машины
pending_time = {}


def parse_time(time_str: str) -> datetime | None:
    """Парсит время из строки"""
    time_str = time_str.strip().lower()
    now = datetime.now()
    target_date = now.date()

    if "завтра" in time_str:
        target_date = (now + timedelta(days=1)).date()
        time_str = time_str.replace("завтра", "").strip()

    patterns = [
        r"(\d{1,2})[:\.](\d{2})",
        r"^(\d{2})(\d{2})$",
    ]

    for pattern in patterns:
        match = re.search(pattern, time_str)
        if match:
            hours, minutes = int(match.group(1)), int(match.group(2))
            if 0 <= hours <= 23 and 0 <= minutes <= 59:
                return datetime.combine(target_date, datetime.min.time().replace(hour=hours, minute=minutes))

    return None


def get_cars_keyboard(action: str = "park") -> InlineKeyboardMarkup:
    """Создаёт клавиатуру с машинами"""
    cars = get_all_cars()
    buttons = []
    for car_id, name, number, model in cars:
        buttons.append([InlineKeyboardButton(
            text=f"{name} ({number})",
            callback_data=f"{action}:{car_id}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_delete_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для удаления машин"""
    cars = get_all_cars()
    buttons = []
    for car_id, name, number, model in cars:
        buttons.append([InlineKeyboardButton(
            text=f"❌ {name} ({number})",
            callback_data=f"del:{car_id}"
        )])
    buttons.append([InlineKeyboardButton(text="Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# === Команды ===

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я помогу заказать пропуск на parkspot.ru\n\n"
        "Команды:\n"
        "/cars — список машин\n"
        "/add — добавить машину\n"
        "/del — удалить машину\n"
        "/history — активные парковки\n\n"
        "Просто напиши время (15:30) и выбери машину,\n"
        "или напиши с именем: секвойя 15:30"
    )


@dp.message(Command("cars"))
async def cmd_cars(message: types.Message):
    cars = get_all_cars()
    if not cars:
        await message.answer("База машин пуста. Добавь машину: /add")
        return

    text = "🚗 Машины в базе:\n\n"
    for car_id, name, number, model in cars:
        text += f"• {name}: {number} ({model})\n"

    await message.answer(text)


@dp.message(Command("add"))
async def cmd_add(message: types.Message):
    await message.answer(
        "Чтобы добавить машину, напиши:\n\n"
        "/add имя номер марка\n\n"
        "Пример:\n"
        "/add камри А123ВС777 Тойота"
    )


@dp.message(Command("del"))
async def cmd_del(message: types.Message):
    cars = get_all_cars()
    if not cars:
        await message.answer("База машин пуста.")
        return

    await message.answer("Выбери машину для удаления:", reply_markup=get_delete_keyboard())


@dp.message(Command("history"))
async def cmd_history(message: types.Message):
    active = get_active_orders()
    recent = get_recent_orders(5)

    text = ""

    if active:
        text += "✅ Активные парковки:\n\n"
        for order in active:
            order_id, car_name, car_number, car_model, entry_time, created_at, response = order
            entry_dt = datetime.fromisoformat(entry_time)
            text += f"• {car_name} ({car_number})\n"
            text += f"  Въезд: {entry_dt.strftime('%d.%m.%Y %H:%M')}\n\n"
    else:
        text += "Нет активных парковок.\n\n"

    if recent:
        text += "📋 Последние заказы:\n\n"
        for order in recent:
            order_id, car_name, car_number, car_model, entry_time, created_at, response = order
            entry_dt = datetime.fromisoformat(entry_time)
            created_dt = datetime.fromisoformat(created_at)
            text += f"• {car_name}: {entry_dt.strftime('%d.%m %H:%M')} (заказ {created_dt.strftime('%d.%m %H:%M')})\n"

    await message.answer(text or "История пуста.")


# === Обработка добавления машины ===

@dp.message(F.text.startswith("/add "))
async def handle_add_car(message: types.Message):
    parts = message.text[5:].strip().split(maxsplit=2)

    if len(parts) < 3:
        await message.answer("Формат: /add имя номер марка\nПример: /add камри А123ВС777 Тойота")
        return

    name, number, model = parts

    if get_car_by_name(name):
        await message.answer(f"Машина '{name}' уже существует.")
        return

    if add_car(name, number, model):
        await message.answer(f"✅ Машина добавлена:\n{name}: {number.upper()} ({model})")
    else:
        await message.answer("Ошибка при добавлении машины.")


# === Callback обработчики ===

@dp.callback_query(F.data.startswith("del:"))
async def callback_delete(callback: CallbackQuery):
    car_id = int(callback.data.split(":")[1])
    car = get_car_by_id(car_id)

    if car and delete_car_by_id(car_id):
        await callback.message.edit_text(f"✅ Машина '{car[1]}' удалена.")
    else:
        await callback.message.edit_text("Машина не найдена.")

    await callback.answer()


@dp.callback_query(F.data == "cancel")
async def callback_cancel(callback: CallbackQuery):
    await callback.message.edit_text("Отменено.")
    await callback.answer()


@dp.callback_query(F.data.startswith("park:"))
async def callback_park(callback: CallbackQuery):
    user_id = callback.from_user.id
    car_id = int(callback.data.split(":")[1])

    if user_id not in pending_time:
        await callback.message.edit_text("Время не найдено. Напиши время заново.")
        await callback.answer()
        return

    entry_time = pending_time.pop(user_id)
    car = get_car_by_id(car_id)

    if not car:
        await callback.message.edit_text("Машина не найдена.")
        await callback.answer()
        return

    car_id, car_name, car_number, car_model = car

    await callback.message.edit_text(
        f"Оформляю пропуск...\n"
        f"Машина: {car_name} ({car_number}, {car_model})\n"
        f"Время: {entry_time.strftime('%d.%m.%Y %H:%M')}"
    )
    await callback.answer()

    result = await submit_pass(car_number, car_model, entry_time)

    # Сохраняем в историю
    add_parking_order(car_name, car_number, car_model, entry_time, result.get("message", ""))

    response_text = result.get("message", "Нет ответа")
    await callback.message.answer(f"Ответ сайта:\n\n{response_text}")


# === Обработка сообщений с временем ===

@dp.message()
async def handle_message(message: types.Message):
    text = message.text
    if not text:
        return

    text_lower = text.strip().lower()

    # Проверяем, указано ли имя машины
    cars = get_all_cars()
    found_car = None
    time_part = text_lower

    for car_id, name, number, model in cars:
        if text_lower.startswith(name.lower()):
            found_car = (car_id, name, number, model)
            time_part = text_lower[len(name):].strip()
            break

    entry_time = parse_time(time_part)

    if entry_time is None:
        await message.answer(
            "Не понял время. Примеры:\n"
            "  15:30\n"
            "  завтра 10:00\n"
            "  секвойя 18:45"
        )
        return

    # Если машина указана явно — сразу оформляем
    if found_car:
        car_id, car_name, car_number, car_model = found_car

        await message.answer(
            f"Оформляю пропуск...\n"
            f"Машина: {car_name} ({car_number}, {car_model})\n"
            f"Время: {entry_time.strftime('%d.%m.%Y %H:%M')}"
        )

        result = await submit_pass(car_number, car_model, entry_time)
        add_parking_order(car_name, car_number, car_model, entry_time, result.get("message", ""))

        response_text = result.get("message", "Нет ответа")
        await message.answer(f"Ответ сайта:\n\n{response_text}")
    else:
        # Показываем клавиатуру для выбора машины
        pending_time[message.from_user.id] = entry_time
        await message.answer(
            f"Время: {entry_time.strftime('%d.%m.%Y %H:%M')}\n\nВыбери машину:",
            reply_markup=get_cars_keyboard("park")
        )


async def main():
    print("Бот запущен...", flush=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
