import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "parkspot.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    """Инициализация базы данных"""
    conn = get_connection()
    cursor = conn.cursor()

    # Таблица машин
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            number TEXT NOT NULL,
            model TEXT NOT NULL
        )
    ''')

    # Таблица заказов парковки
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parking_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_name TEXT NOT NULL,
            car_number TEXT NOT NULL,
            car_model TEXT NOT NULL,
            entry_time TEXT NOT NULL,
            created_at TEXT NOT NULL,
            response TEXT
        )
    ''')

    # Добавляем машины по умолчанию если база пустая
    cursor.execute('SELECT COUNT(*) FROM cars')
    if cursor.fetchone()[0] == 0:
        default_cars = [
            ("секвойя", "А606ВО 797", "Тойота"),
            ("панама", "У657НУ 797", "Порше"),
            ("паджеро", "К860НК 150", "Митсубиси"),
        ]
        cursor.executemany('INSERT INTO cars (name, number, model) VALUES (?, ?, ?)', default_cars)

    conn.commit()
    conn.close()


# === Машины ===

def get_all_cars() -> list[tuple]:
    """Получить все машины: [(id, name, number, model), ...]"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, number, model FROM cars ORDER BY name')
    cars = cursor.fetchall()
    conn.close()
    return cars


def get_car_by_name(name: str) -> tuple | None:
    """Получить машину по имени"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, number, model FROM cars WHERE LOWER(name) = LOWER(?)', (name,))
    car = cursor.fetchone()
    conn.close()
    return car


def get_car_by_id(car_id: int) -> tuple | None:
    """Получить машину по ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, number, model FROM cars WHERE id = ?', (car_id,))
    car = cursor.fetchone()
    conn.close()
    return car


def add_car(name: str, number: str, model: str) -> bool:
    """Добавить машину. Возвращает True если успешно."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO cars (name, number, model) VALUES (?, ?, ?)',
                      (name.lower(), number.upper(), model))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def delete_car(name: str) -> bool:
    """Удалить машину по имени. Возвращает True если удалена."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cars WHERE LOWER(name) = LOWER(?)', (name,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def delete_car_by_id(car_id: int) -> bool:
    """Удалить машину по ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cars WHERE id = ?', (car_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# === Заказы парковки ===

def add_parking_order(car_name: str, car_number: str, car_model: str,
                      entry_time: datetime, response: str) -> int:
    """Добавить заказ парковки. Возвращает ID заказа."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO parking_orders (car_name, car_number, car_model, entry_time, created_at, response)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (car_name, car_number, car_model,
          entry_time.isoformat(), datetime.now().isoformat(), response))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id


def get_active_orders() -> list[tuple]:
    """Получить активные заказы (время въезда >= сейчас)"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute('''
        SELECT id, car_name, car_number, car_model, entry_time, created_at, response
        FROM parking_orders
        WHERE entry_time >= ?
        ORDER BY entry_time
    ''', (now,))
    orders = cursor.fetchall()
    conn.close()
    return orders


def get_recent_orders(limit: int = 10) -> list[tuple]:
    """Получить последние заказы"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, car_name, car_number, car_model, entry_time, created_at, response
        FROM parking_orders
        ORDER BY created_at DESC
        LIMIT ?
    ''', (limit,))
    orders = cursor.fetchall()
    conn.close()
    return orders


# Инициализация при импорте
init_db()
