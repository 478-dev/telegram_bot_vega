import sqlite3
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from config import DB_PATH

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def export_to_xlsx(filepath):
    conn = get_conn()
    cur = conn.cursor()
    
    # Получаем оплаченные заказы с информацией о товаре
    cur.execute("""
        SELECT o.ID, g.CATEGORY, g.SQUAD, o.NAME, g.PRICE, o.PAYMENT 
        FROM ORDERS o
        LEFT JOIN GOODS g ON o.ORDER_ID = g.ID
        WHERE o.PAYMENT = 1
    """)
    paid_orders = cur.fetchall()
    
    # Получаем неоплаченные заказы
    cur.execute("""
        SELECT o.ID, g.CATEGORY, g.SQUAD, o.NAME, g.PRICE, o.PAYMENT 
        FROM ORDERS o
        LEFT JOIN GOODS g ON o.ORDER_ID = g.ID
        WHERE o.PAYMENT = 0
    """)
    unpaid_orders = cur.fetchall()
    
    conn.close()
    
    # Создаем Excel файл
    wb = Workbook()
    wb.remove(wb.active)
    
    # Лист с оплаченными
    ws_paid = wb.create_sheet("Оплаченные")
    ws_paid.append(["ID заказа", "Категория", "Отряд", "Имя покупателя", "Цена", "Статус"])
    
    header_fill = PatternFill(start_color="4CAF50", end_color="4CAF50", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for cell in ws_paid[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    
    for order in paid_orders:
        ws_paid.append([order[0], order[1] or "—", order[2] or "—", order[3], order[4] or "—", "✅ Оплачено"])
    
    # Лист с неоплаченными
    ws_unpaid = wb.create_sheet("Неоплаченные")
    ws_unpaid.append(["ID заказа", "Категория", "Отряд", "Имя покупателя", "Цена", "Статус"])
    
    header_fill = PatternFill(start_color="FF9800", end_color="FF9800", fill_type="solid")
    
    for cell in ws_unpaid[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    
    for order in unpaid_orders:
        ws_unpaid.append([order[0], order[1] or "—", order[2] or "—", order[3], order[4] or "—", "❌ Не оплачено"])
    
    # Установим ширину колонок
    for ws in [ws_paid, ws_unpaid]:
        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 25
        ws.column_dimensions['C'].width = 20
        ws.column_dimensions['D'].width = 20
        ws.column_dimensions['E'].width = 10
        ws.column_dimensions['F'].width = 15
    
    wb.save(filepath)
    return filepath
