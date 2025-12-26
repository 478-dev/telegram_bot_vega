from telebot import TeleBot, types
from config import TOKEN, ADMIN_CHAT_ID
from db import add_order, update_order_payment, get_order, find_item_id
from db_export import export_to_xlsx
import texts
import os

bot = TeleBot(TOKEN)
user_data = {}

CAT_IDS = {
    "💯 Отрядные открытки": "otkr",
    "☃️ Новогодние открытки": "ng",
    "🤣 Набор смешных стикеров": "fun",
    "🫂 Набор милых стикеров": "cute",
    "🎀 Обвесы": "obv",
    "😈 Пак мемологии": "memo"
}

ID_TO_CAT = {v: k for k, v in CAT_IDS.items()}

CATEGORIES = {
    "💯 Отрядные открытки": {
        "squads": texts.SQUADS_POSTCARDS,
        "text": texts.SQUAD_PROMPT
    },
    "☃️ Новогодние открытки": {
        "squads": texts.NY_POSTCARDS,
        "text": texts.POSTCARD_PROMPT
    },
    "🎀 Обвесы": {
        "squads": texts.SQUADS_ACCESSORIES,
        "text": texts.SQUAD_PROMPT
    }
}

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(texts.MENU_BUTTON_TEXT, callback_data="menu"))
    bot.send_message(message.chat.id, texts.WELCOME_MESSAGE, reply_markup=markup)

@bot.message_handler(commands=['table'])
def send_table(message):
    if str(message.chat.id) != str(ADMIN_CHAT_ID):
        bot.send_message(message.chat.id, "❌ У вас нет прав на выполнение этой команды")
        return
    
    try:
        filepath = "/tmp/orders.xlsx"
        export_to_xlsx(filepath)
        
        with open(filepath, 'rb') as file:
            bot.send_document(message.chat.id, file, caption="📊 Отчет по заказам")
        
        os.remove(filepath)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при экспорте: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "menu")
def show_categories(call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    for cat in texts.CATEGORIES_LIST:
        cat_id = CAT_IDS.get(cat, cat[:10])
        markup.add(types.InlineKeyboardButton(cat, callback_data=f"c:{cat_id}"))
    bot.edit_message_text(texts.CATEGORIES_MENU_TEXT, call.message.chat.id, call.message.id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("c:"))
def handle_category(call):
    cat_id = call.data[2:]
    category = ID_TO_CAT.get(cat_id, cat_id)
    user_id = call.from_user.id
    user_data[user_id] = {"category": category, "cat_id": cat_id}
    
    photo_url = texts.PHOTOS.get(category)
    if photo_url:
        try:
            bot.send_photo(call.message.chat.id, photo_url, caption=f"Пример: {category}")
        except:
            pass
    
    description = texts.DESCRIPTIONS.get(category, "")
    if description:
        bot.send_message(call.message.chat.id, description)
    
    if category in CATEGORIES:
        markup = types.InlineKeyboardMarkup(row_width=2)
        squads = CATEGORIES[category]["squads"]
        for i, squad in enumerate(squads):
            markup.add(types.InlineKeyboardButton(squad, callback_data=f"s:{i}"))
        markup.add(types.InlineKeyboardButton(texts.BACK_BUTTON_TEXT, callback_data="back_cat"))
        bot.send_message(call.message.chat.id, CATEGORIES[category]["text"], reply_markup=markup)
    else:
        user_data[user_id]["item"] = category
        user_data[user_id]["squad"] = "Не указан"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(texts.BACK_BUTTON_TEXT, callback_data="back_cat"))
        bot.send_message(call.message.chat.id, texts.selected_category(category), reply_markup=markup)
        bot.register_next_step_handler_by_chat_id(call.message.chat.id, get_name)

@bot.callback_query_handler(func=lambda call: call.data == "back_cat")
def back_to_categories(call):
    show_categories(call)

@bot.callback_query_handler(func=lambda call: call.data == "back_squad")
def back_to_squad_selection(call):
    user_id = call.from_user.id
    if user_id in user_data:
        category = user_data[user_id].get("category")
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        squads = CATEGORIES[category]["squads"]
        for i, squad in enumerate(squads):
            markup.add(types.InlineKeyboardButton(squad, callback_data=f"s:{i}"))
        markup.add(types.InlineKeyboardButton(texts.BACK_BUTTON_TEXT, callback_data="back_cat"))
        bot.edit_message_text(CATEGORIES[category]["text"], call.message.chat.id, call.message.id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("s:"))
def handle_squad(call):
    squad_idx = int(call.data[2:])
    user_id = call.from_user.id
    
    if user_id not in user_data:
        return
    
    category = user_data[user_id]["category"]
    squad = CATEGORIES[category]["squads"][squad_idx]
    user_data[user_id]["squad"] = squad
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(texts.BACK_BUTTON_TEXT, callback_data="back_squad"))
    bot.edit_message_text(texts.selected_squad(category, squad), call.message.chat.id, call.message.id, reply_markup=markup)
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, get_name)

def get_name(message):
    user_id = message.from_user.id
    
    if message.text and message.text.startswith('/'):
        return
    
    if user_id not in user_data:
        return
        
    user_data[user_id]["name"] = message.text
    
    category = user_data[user_id].get("category", "")
    squad = user_data[user_id].get("squad", "Не указан")
    
    # Находим реальный ID товара из таблицы GOODS
    item_id = find_item_id(category, (squad if squad == "Не указан" else squad[2:]))
    
    if item_id is None:
        item_id = 0  # Если не найден товар, ставим 0
    
    order_id = add_order(item_id, message.text, (squad if squad == "Не указан" else squad[2:]), 0)
    user_data[user_id]["order_id"] = order_id
    
    bot.send_message(ADMIN_CHAT_ID, texts.new_order_admin(order_id, category, squad, message.text))
    
    payment_message = f"{texts.PAYMENT_INSTRUCTIONS}\n\n{texts.ASK_PAYMENT_SCREENSHOT}"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(texts.BACK_BUTTON_TEXT, callback_data="menu"))
    bot.send_message(message.chat.id, payment_message, reply_markup=markup)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    if user_id in user_data:
        order_id = user_data[user_id].get("order_id")
        if order_id:
            update_order_payment(order_id, 1)
            order = get_order(order_id)
            bot.forward_message(ADMIN_CHAT_ID, message.chat.id, message.id)
            bot.send_message(ADMIN_CHAT_ID, texts.payment_confirmed_admin(order_id, order[2], order[3]))
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(texts.ORDER_MORE_BUTTON_TEXT, callback_data="menu"))
            bot.send_message(message.chat.id, texts.SUCCESS_MESSAGE, reply_markup=markup)
            del user_data[user_id]

def run():
    bot.infinity_polling()
