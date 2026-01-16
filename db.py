import sqlite3
import os
from config import DB_PATH

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Таблица категорий
    cur.execute("""
        CREATE TABLE IF NOT EXISTS CATEGORIES (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emoji TEXT,
            text TEXT NOT NULL,
            description TEXT,
            picture TEXT
        )
    """)

    # Таблица позиций
    cur.execute("""
        CREATE TABLE IF NOT EXISTS POSITIONS (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            emoji TEXT,
            text TEXT NOT NULL,
            description TEXT,
            price INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            FOREIGN KEY (category_id) REFERENCES CATEGORIES(id)
        )
    """)

    # Таблица заказов
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ORDERSS (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position_id INTEGER,
            payment INTEGER NOT NULL DEFAULT 0,
            user_name TEXT,
            user_info TEXT,
            FOREIGN KEY (position_id) REFERENCES POSITIONS(id)
        )
    """)

    # Создаем root категорию если её нет
    cur.execute("SELECT id FROM CATEGORIES WHERE id = 0")
    if not cur.fetchone():
        cur.execute("INSERT INTO CATEGORIES (id, emoji, text, description, picture) VALUES (0, NULL, 'root', NULL, NULL)")

    conn.commit()
    conn.close()

# Функции для работы с категориями
def add_category(emoji, text, description=None, picture=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO CATEGORIES (emoji, text, description, picture) VALUES (?, ?, ?, ?)", 
                (emoji, text, description, picture))
    cat_id = cur.lastrowid
    conn.commit()
    conn.close()
    return cat_id

def get_all_categories():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, emoji, text, description, picture FROM CATEGORIES WHERE id != 0")
    categories = cur.fetchall()
    conn.close()
    return categories

def get_category(cat_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, emoji, text, description, picture FROM CATEGORIES WHERE id = ?", (cat_id,))
    category = cur.fetchone()
    conn.close()
    return category

def update_category_text(cat_id, text):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE CATEGORIES SET text = ? WHERE id = ?", (text, cat_id))
    conn.commit()
    conn.close()

def update_category_emoji(cat_id, emoji):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE CATEGORIES SET emoji = ? WHERE id = ?", (emoji, cat_id))
    conn.commit()
    conn.close()

def update_category_description(cat_id, description):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE CATEGORIES SET description = ? WHERE id = ?", (description, cat_id))
    conn.commit()
    conn.close()

def update_category_picture(cat_id, picture):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE CATEGORIES SET picture = ? WHERE id = ?", (picture, cat_id))
    conn.commit()
    conn.close()

def delete_category(cat_id):
    conn = get_conn()
    cur = conn.cursor()
    # Удаляем все позиции в категории
    cur.execute("DELETE FROM POSITIONS WHERE category_id = ?", (cat_id,))
    # Удаляем саму категорию
    cur.execute("DELETE FROM CATEGORIES WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()

# Функции для работы с позициями
def add_position(category_id, emoji, text, description, price, amount):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO POSITIONS (category_id, emoji, text, description, price, amount) VALUES (?, ?, ?, ?, ?, ?)", 
                (category_id, emoji, text, description, price, amount))
    pos_id = cur.lastrowid
    conn.commit()
    conn.close()
    return pos_id

def get_all_positions():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, category_id, emoji, text, description, price, amount FROM POSITIONS")
    positions = cur.fetchall()
    conn.close()
    return positions

def get_positions_by_category(cat_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, category_id, emoji, text, description, price, amount FROM POSITIONS WHERE category_id = ?", (cat_id,))
    positions = cur.fetchall()
    conn.close()
    return positions

def get_position(pos_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, category_id, emoji, text, description, price, amount FROM POSITIONS WHERE id = ?", (pos_id,))
    position = cur.fetchone()
    conn.close()
    return position

def update_position_text(pos_id, text):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE POSITIONS SET text = ? WHERE id = ?", (text, pos_id))
    conn.commit()
    conn.close()

def update_position_emoji(pos_id, emoji):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE POSITIONS SET emoji = ? WHERE id = ?", (emoji, pos_id))
    conn.commit()
    conn.close()

def update_position_description(pos_id, description):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE POSITIONS SET description = ? WHERE id = ?", (description, pos_id))
    conn.commit()
    conn.close()

def update_position_price(pos_id, price):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE POSITIONS SET price = ? WHERE id = ?", (price, pos_id))
    conn.commit()
    conn.close()

def update_position_amount(pos_id, amount):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE POSITIONS SET amount = ? WHERE id = ?", (amount, pos_id))
    conn.commit()
    conn.close()

def delete_position(pos_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM POSITIONS WHERE id = ?", (pos_id,))
    conn.commit()
    conn.close()

# Функции для работы с заказами
def add_order(position_id, user_name, user_info, payment=0):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO ORDERSS (position_id, payment, user_name, user_info) VALUES (?, ?, ?, ?)",
                (position_id, payment, user_name, user_info))
    order_id = cur.lastrowid
    conn.commit()
    conn.close()
    return order_id

def update_order_payment(order_id, payment=1):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE ORDERSS SET payment = ? WHERE id = ?", (payment, order_id))
    conn.commit()
    conn.close()

def get_order(order_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, position_id, payment, user_name, user_info FROM ORDERSS WHERE id = ?", (order_id,))
    order = cur.fetchone()
    conn.close()
    return order

# Функция для получения текста меню
def get_menu_text():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT text FROM CATEGORIES WHERE id = 0")
    result = cur.fetchone()
    conn.close()
    return result[0] if result else "Меню"

def update_menu_text(text):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE CATEGORIES SET text = ? WHERE id = 0", (text,))
    conn.commit()
    conn.close()
