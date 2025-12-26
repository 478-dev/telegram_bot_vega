import sqlite3
from config import DB_PATH

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS GOODS (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            CATEGORY TEXT NOT NULL,
            SQUAD TEXT,
            PRICE INTEGER NOT NULL,
            AMOUNT INTEGER NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ORDERS (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            ORDER_ID INTEGER,
            NAME TEXT,
            SQUAD TEXT,
            PAYMENT INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def add_item(category, squad, price, amount):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO GOODS (CATEGORY, SQUAD, PRICE, AMOUNT) VALUES (?, ?, ?, ?)", 
                (category, squad, price, amount))
    conn.commit()
    conn.close()

def find_item_id(category, squad=None):
    conn = get_conn()
    cur = conn.cursor()
    
    # Убираем эмодзи из категории
    clean_category = category.replace('💯', '').replace('☃️', '').replace('🤣', '').replace('🫂', '').replace('🎀', '').replace('😈', '').strip()
    
    if squad and squad != "Не указан":
        cur.execute("SELECT ID FROM GOODS WHERE CATEGORY LIKE ? AND SQUAD = ?", (f"%{clean_category}%", squad))
    else:
        cur.execute("SELECT ID FROM GOODS WHERE CATEGORY LIKE ? AND SQUAD IS NULL", (f"%{clean_category}%",))
    
    result = cur.fetchone()
    conn.close()
    
    return result[0] if result else None

def add_order(pos_id, user_name, squad_name, paid=0):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO ORDERS (ORDER_ID, NAME, SQUAD, PAYMENT) VALUES (?, ?, ?, ?)",
        (pos_id, user_name, squad_name, paid)
    )
    order_id = cur.lastrowid
    conn.commit()
    conn.close()
    return order_id

def update_order_payment(order_id, paid=1):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE ORDERS SET PAYMENT = ? WHERE ID = ?", (paid, order_id))
    conn.commit()
    conn.close()

def get_order(order_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ORDERS WHERE ID = ?", (order_id,))
    order = cur.fetchone()
    conn.close()
    return order

def get_all_items():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT ID, CATEGORY, SQUAD, PRICE, AMOUNT FROM GOODS")
    items = cur.fetchall()
    conn.close()
    return items
