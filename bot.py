from telebot import TeleBot, types
from config import TOKEN, ADMIN_CHAT_ID
from db import *
from db_export import export_to_xlsx
import texts
import os

bot = TeleBot(TOKEN)
user_data = {}

# Создаем папку data если её нет
os.makedirs('data', exist_ok=True)

# ========== ПОЛЬЗОВАТЕЛЬСКИЕ КОМАНДЫ ==========

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(texts.MENU_BUTTON_TEXT, callback_data="menu"))
    bot.send_message(message.chat.id, texts.WELCOME_MESSAGE, reply_markup=markup)

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """📖 Справка по командам:

👤 Для пользователей:
/start - Начать работу с ботом
/help - Показать эту справку

🛍 Чтобы сделать заказ, нажмите кнопку "Открыть меню" и выберите товар."""

    if str(message.chat.id) == str(ADMIN_CHAT_ID):
        help_text += """

👑 Команды администратора:
/edit_menu - Изменить текст меню
/add_category - Добавить категорию
/delete_category - Удалить категорию
/edit_category - Редактировать категорию
/add_position - Добавить позицию
/delete_position - Удалить позицию
/edit_position - Редактировать позицию
/table - Экспортировать заказы в Excel"""

    bot.send_message(message.chat.id, help_text)

@bot.callback_query_handler(func=lambda call: call.data == "menu")
def show_menu(call):
    markup = types.InlineKeyboardMarkup(row_width=2)

    # Получаем все категории
    categories = get_all_categories()
    for cat in categories:
        cat_id, emoji, text, description, picture = cat
        display_text = f"{emoji} {text}" if emoji else text
        markup.add(types.InlineKeyboardButton(display_text, callback_data=f"cat:{cat_id}"))

    # Получаем позиции в корне (category_id = 0)
    root_positions = get_positions_by_category(0)
    for pos in root_positions:
        pos_id, _, emoji, text, description, price, amount = pos
        display_text = f"{emoji} {text}" if emoji else text
        markup.add(types.InlineKeyboardButton(display_text, callback_data=f"pos:{pos_id}"))

    menu_text = get_menu_text()
    try:
        bot.edit_message_text(menu_text, call.message.chat.id, call.message.id, reply_markup=markup)
    except:
        bot.send_message(call.message.chat.id, menu_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cat:"))
def show_category(call):
    cat_id = int(call.data.split(":")[1])
    category = get_category(cat_id)

    if not category:
        bot.answer_callback_query(call.id, "❌ Категория не найдена")
        return

    _, emoji, text, description, picture = category
    display_name = f"{emoji} {text}" if emoji else text

    # Получаем позиции в категории
    positions = get_positions_by_category(cat_id)
    markup = types.InlineKeyboardMarkup(row_width=2)

    for pos in positions:
        pos_id, _, p_emoji, p_text, p_desc, price, amount = pos
        display_text = f"{p_emoji} {p_text}" if p_emoji else p_text
        markup.add(types.InlineKeyboardButton(display_text, callback_data=f"pos:{pos_id}"))

    markup.add(types.InlineKeyboardButton("⬅️ Назад в меню", callback_data="menu"))

    # Формируем полное сообщение с описанием
    message_text = f"📁 Категория: {display_name}"
    if description:
        message_text += f"\n\n{description}"
    message_text += "\n\nВыберите позицию:"

    # Если есть картинка - отправляем её с описанием в caption и клавиатурой
    if picture and os.path.exists(picture):
        try:
            with open(picture, 'rb') as photo:
                bot.send_photo(call.message.chat.id, photo, caption=message_text, reply_markup=markup)
        except Exception as e:
            print(f"Ошибка при отправке картинки: {e}")
            # Если не удалось отправить картинку, отправляем текстовое сообщение
            bot.send_message(call.message.chat.id, message_text, reply_markup=markup)
    else:
        # Если картинки нет - отправляем текстовое сообщение
        bot.send_message(call.message.chat.id, message_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pos:"))
def show_position(call):
    pos_id = int(call.data.split(":")[1])
    position = get_position(pos_id)

    if not position:
        bot.answer_callback_query(call.id, "❌ Позиция не найдена")
        return

    _, cat_id, emoji, text, description, price, amount = position

    user_data[call.from_user.id] = {"position_id": pos_id}

    display_text = f"{emoji} {text}" if emoji else text
    info_text = f"📦 {display_text}\n"
    if description:
        info_text += f"\n{description}\n"
    info_text += f"\n💰 Цена: {price}₽\n📊 В наличии: {amount} шт.\n\nНапишите ФИО и отряд получателя через запятую:"

    markup = types.InlineKeyboardMarkup()
    if cat_id == 0:
        markup.add(types.InlineKeyboardButton("⬅️ Назад в меню", callback_data="menu"))
    else:
        markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"cat:{cat_id}"))

    bot.send_message(call.message.chat.id, info_text, reply_markup=markup)
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, get_user_name)

def get_user_name(message):
    user_id = message.from_user.id

    if message.text and message.text.startswith('/'):
        return

    if user_id not in user_data:
        return

    user_data[user_id]["user_name"] = message.text

    position = get_position(user_data[user_id]["position_id"])
    _, _, emoji, text, description, price, _ = position
    display_text = f"{emoji} {text}" if emoji else text

    order_id = add_order(user_data[user_id]["position_id"], message.text, "", 0)
    user_data[user_id]["order_id"] = order_id

    # Уведомление админу
    admin_msg = f"📦 Новый заказ #{order_id}\n\n"
    admin_msg += f"Позиция: {display_text}\n"
    admin_msg += f"Цена: {price}₽\n"
    admin_msg += f"Покупатель: {message.text}\n"
    admin_msg += f"Оплата: ❌ Нет"
    bot.send_message(ADMIN_CHAT_ID, admin_msg)

    payment_text = f"{texts.PAYMENT_INSTRUCTIONS}\n\n{texts.ASK_PAYMENT_SCREENSHOT}"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ Назад в меню", callback_data="menu"))
    bot.send_message(message.chat.id, payment_text, reply_markup=markup)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    print(f"📸 Получено фото от chat_id={chat_id}")
    print(f"📊 Текущий user_data: {user_data}")
    print(f"🔍 chat_id in user_data: {chat_id in user_data}")
    if chat_id in user_data:
        print(f"🔍 Содержимое user_data[{chat_id}]: {user_data[chat_id]}")

    # Проверка на команду edit_category (изменение картинки)
    if chat_id in user_data and "edit_category_picture" in user_data[chat_id]:
        print(f"✅ Обрабатываем изменение картинки категории")
        cat_id = user_data[chat_id]["edit_category_picture"]

        # Получаем старую картинку
        category = get_category(cat_id)
        old_picture = category[4] if category else None

        # Удаляем старую картинку если была
        if old_picture and os.path.exists(old_picture):
            try:
                os.remove(old_picture)
                print(f"🗑️ Удалена старая картинка: {old_picture}")
            except Exception as e:
                print(f"⚠️ Не удалось удалить старую картинку: {e}")

        # Сохраняем новую картинку
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        filename = f"./data/category_{cat_id}.jpg"
        with open(filename, 'wb') as new_file:
            new_file.write(downloaded_file)

        print(f"💾 Сохранена новая картинка: {filename}")

        update_category_picture(cat_id, filename)
        bot.send_message(message.chat.id, "✅ Картинка категории обновлена!")
        del user_data[chat_id]["edit_category_picture"]
        return

    # Обработка оплаты
    if chat_id in user_data and "order_id" in user_data[chat_id]:
        order_id = user_data[chat_id]["order_id"]

        update_order_payment(order_id, 1)
        order = get_order(order_id)

        bot.forward_message(ADMIN_CHAT_ID, message.chat.id, message.id)
        bot.send_message(ADMIN_CHAT_ID, f"✅ Оплата для заказа #{order_id}\nПокупатель: {order[3]}")

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(texts.ORDER_MORE_BUTTON_TEXT, callback_data="menu"))
        bot.send_message(message.chat.id, texts.SUCCESS_MESSAGE, reply_markup=markup)

        del user_data[chat_id]

# ========== АДМИНИСТРАТИВНЫЕ КОМАНДЫ ==========

def is_admin(chat_id):
    return str(chat_id) == str(ADMIN_CHAT_ID)

# ===== /edit_menu =====
@bot.message_handler(commands=['edit_menu'])
def edit_menu(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "❌ У вас нет прав на выполнение этой команды")
        return

    current_text = get_menu_text()
    bot.send_message(message.chat.id, f"Текущий текст меню:\n\n{current_text}\n\n📝 Отправьте новый текст меню:")
    bot.register_next_step_handler(message, process_edit_menu)

def process_edit_menu(message):
    if message.text and message.text.startswith('/'):
        return
    update_menu_text(message.text)
    bot.send_message(message.chat.id, "✅ Текст меню обновлен!")

# ===== /add_category =====
@bot.message_handler(commands=['add_category'])
def add_category_command(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "❌ У вас нет прав на выполнение этой команды")
        return

    bot.send_message(message.chat.id, "📝 Введите имя категории (можно с эмодзи в начале):")
    bot.register_next_step_handler(message, process_category_name)

def process_category_name(message):
    if message.text and message.text.startswith('/'):
        return
    user_data[message.chat.id] = {"new_category_name": message.text}
    bot.send_message(message.chat.id, "📝 Введите описание категории:")
    bot.register_next_step_handler(message, process_category_description)

def process_category_description(message):
    if message.text and message.text.startswith('/'):
        return

    name = user_data[message.chat.id]["new_category_name"]
    description = message.text

    # Разделяем эмодзи и текст
    emoji = None
    text = name

    if name:
        first_char = name[0]
        if ord(first_char) > 127:
            emoji_end = 1
            while emoji_end < len(name) and ord(name[emoji_end]) > 127:
                emoji_end += 1
            emoji = name[:emoji_end].strip()
            text = name[emoji_end:].strip()

    cat_id = add_category(emoji, text, description, None)
    display_name = f"{emoji} {text}" if emoji else text
    bot.send_message(message.chat.id, f"✅ Категория '{display_name}' создана с ID {cat_id}!")
    del user_data[message.chat.id]

# ===== /delete_category =====
@bot.message_handler(commands=['delete_category'])
def delete_category_command(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "❌ У вас нет прав на выполнение этой команды")
        return

    categories = get_all_categories()

    if not categories:
        bot.send_message(message.chat.id, "❌ Нет категорий для удаления")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for cat in categories:
        cat_id, emoji, text, description, picture = cat
        display_text = f"{emoji} {text}" if emoji else text
        # Добавляем индикатор наличия картинки
        if picture and os.path.exists(picture):
            display_text += " 🖼"
        markup.add(types.InlineKeyboardButton(display_text, callback_data=f"delcat:{cat_id}"))
    markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))

    bot.send_message(message.chat.id, "⚠️ Выберите категорию для удаления (будут удалены все вложенные позиции и картинка):", 
                     reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delcat:"))
def process_delete_category(call):
    cat_id = int(call.data.split(":")[1])
    category = get_category(cat_id)

    if category:
        _, emoji, text, description, picture = category
        display_text = f"{emoji} {text}" if emoji else text

        # Удаляем картинку если есть
        if picture and os.path.exists(picture):
            try:
                os.remove(picture)
                print(f"🗑️ Удалена картинка категории: {picture}")
            except Exception as e:
                print(f"⚠️ Не удалось удалить картинку: {e}")

        delete_category(cat_id)
        bot.answer_callback_query(call.id, f"✅ Категория удалена!")
        bot.edit_message_text(f"✅ Категория '{display_text}' удалена со всеми вложенными позициями и картинкой", 
                             call.message.chat.id, call.message.id)
    else:
        bot.answer_callback_query(call.id, "❌ Категория не найдена")

# ===== /edit_category =====
@bot.message_handler(commands=['edit_category'])
def edit_category_command(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "❌ У вас нет прав на выполнение этой команды")
        return

    categories = get_all_categories()

    if not categories:
        bot.send_message(message.chat.id, "❌ Нет категорий для редактирования")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for cat in categories:
        cat_id, emoji, text, description, picture = cat
        display_text = f"{emoji} {text}" if emoji else text
        # Добавляем индикатор наличия картинки
        if picture and os.path.exists(picture):
            display_text += " 🖼"
        markup.add(types.InlineKeyboardButton(display_text, callback_data=f"editcat:{cat_id}"))
    markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))

    bot.send_message(message.chat.id, "Выберите категорию для редактирования:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("editcat:") and len(call.data.split(":")) == 2)
def show_edit_category_menu(call):
    cat_id = int(call.data.split(":")[1])
    category = get_category(cat_id)

    if not category:
        bot.answer_callback_query(call.id, "❌ Категория не найдена")
        return

    _, emoji, text, description, picture = category
    display_name = f"{emoji} {text}" if emoji else text

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("✏️ Изменить имя", callback_data=f"editcatname:{cat_id}"),
        types.InlineKeyboardButton("📝 Изменить описание", callback_data=f"editcatdesc:{cat_id}"),
        types.InlineKeyboardButton("🖼 Изменить картинку", callback_data=f"editcatpic:{cat_id}")
    )

    # Добавляем кнопку удаления картинки если она есть
    if picture and os.path.exists(picture):
        markup.add(types.InlineKeyboardButton("🗑 Удалить картинку", callback_data=f"delcatpic:{cat_id}"))

    markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))

    info = f"Редактирование категории: {display_name}\n"
    if description:
        info += f"\nОписание: {description}\n"

    # Показываем картинку если есть
    if picture and os.path.exists(picture):
        try:
            with open(picture, 'rb') as photo:
                bot.send_photo(call.message.chat.id, photo, caption=info + "\n🖼 Картинка категории")
        except:
            info += "\n🖼 Картинка: ✅ Есть"
    else:
        info += "\n🖼 Картинка: ❌ Нет"

    bot.edit_message_text(f"{info}\n\nЧто вы хотите изменить?", 
                         call.message.chat.id, call.message.id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("editcatname:"))
def edit_category_name(call):
    cat_id = int(call.data.split(":")[1])
    user_data[call.message.chat.id] = {"edit_category_name": cat_id}
    bot.send_message(call.message.chat.id, "📝 Введите новое имя категории (можно с эмодзи в начале):")
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, process_edit_category_name)

def process_edit_category_name(message):
    if message.text and message.text.startswith('/'):
        return

    cat_id = user_data[message.chat.id]["edit_category_name"]

    # Разделяем эмодзи и текст
    emoji = None
    text = message.text

    if message.text:
        first_char = message.text[0]
        if ord(first_char) > 127:
            emoji_end = 1
            while emoji_end < len(message.text) and ord(message.text[emoji_end]) > 127:
                emoji_end += 1
            emoji = message.text[:emoji_end].strip()
            text = message.text[emoji_end:].strip()

    update_category_text(cat_id, text)
    if emoji:
        update_category_emoji(cat_id, emoji)

    bot.send_message(message.chat.id, "✅ Имя категории обновлено!")
    del user_data[message.chat.id]["edit_category_name"]

@bot.callback_query_handler(func=lambda call: call.data.startswith("editcatdesc:"))
def edit_category_desc(call):
    cat_id = int(call.data.split(":")[1])
    user_data[call.message.chat.id] = {"edit_category_desc": cat_id}
    bot.send_message(call.message.chat.id, "📝 Введите новое описание категории:")
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, process_edit_category_desc)

def process_edit_category_desc(message):
    if message.text and message.text.startswith('/'):
        return

    cat_id = user_data[message.chat.id]["edit_category_desc"]
    update_category_description(cat_id, message.text)
    bot.send_message(message.chat.id, "✅ Описание категории обновлено!")
    del user_data[message.chat.id]["edit_category_desc"]

@bot.callback_query_handler(func=lambda call: call.data.startswith("editcatpic:"))
def edit_category_picture(call):
    cat_id = int(call.data.split(":")[1])
    chat_id = call.message.chat.id
    user_data[chat_id] = {"edit_category_picture": cat_id}
    print(f"🔧 Установлено состояние для chat_id={chat_id}: edit_category_picture={cat_id}")
    print(f"📊 Текущий user_data: {user_data}")
    bot.send_message(chat_id, "🖼 Отправьте новую картинку для категории:")

@bot.callback_query_handler(func=lambda call: call.data.startswith("delcatpic:"))
def delete_category_picture(call):
    cat_id = int(call.data.split(":")[1])
    category = get_category(cat_id)

    if category:
        _, emoji, text, description, picture = category

        # Удаляем картинку если есть
        if picture and os.path.exists(picture):
            try:
                os.remove(picture)
                print(f"🗑️ Удалена картинка: {picture}")
                update_category_picture(cat_id, None)
                bot.answer_callback_query(call.id, "✅ Картинка удалена!")
                bot.edit_message_text(f"✅ Картинка категории удалена", 
                                     call.message.chat.id, call.message.id)
            except Exception as e:
                bot.answer_callback_query(call.id, f"❌ Ошибка: {e}")
        else:
            bot.answer_callback_query(call.id, "❌ Картинка не найдена")
    else:
        bot.answer_callback_query(call.id, "❌ Категория не найдена")

# ===== /add_position =====
@bot.message_handler(commands=['add_position'])
def add_position_command(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "❌ У вас нет прав на выполнение этой команды")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📁 Корень (без категории)", callback_data="addpos:0"))

    categories = get_all_categories()
    for cat in categories:
        cat_id, emoji, text, description, _ = cat
        display_text = f"{emoji} {text}" if emoji else text
        markup.add(types.InlineKeyboardButton(display_text, callback_data=f"addpos:{cat_id}"))
    markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))

    bot.send_message(message.chat.id, "Выберите категорию для новой позиции:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("addpos:"))
def process_add_position_category(call):
    cat_id = int(call.data.split(":")[1])
    user_data[call.message.chat.id] = {"new_position_category": cat_id}
    bot.send_message(call.message.chat.id, "📝 Введите имя позиции (можно с эмодзи в начале):")
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, process_position_name)

def process_position_name(message):
    if message.text and message.text.startswith('/'):
        return
    user_data[message.chat.id]["new_position_name"] = message.text
    bot.send_message(message.chat.id, "📝 Введите описание позиции:")
    bot.register_next_step_handler(message, process_position_description)

def process_position_description(message):
    if message.text and message.text.startswith('/'):
        return
    user_data[message.chat.id]["new_position_description"] = message.text
    bot.send_message(message.chat.id, "💰 Введите цену позиции (в рублях):")
    bot.register_next_step_handler(message, process_position_price)

def process_position_price(message):
    if message.text and message.text.startswith('/'):
        return
    try:
        price = int(message.text)
        user_data[message.chat.id]["new_position_price"] = price
        bot.send_message(message.chat.id, "📊 Введите количество:")
        bot.register_next_step_handler(message, process_position_amount)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат цены. Введите число:")
        bot.register_next_step_handler(message, process_position_price)

def process_position_amount(message):
    if message.text and message.text.startswith('/'):
        return
    try:
        amount = int(message.text)

        cat_id = user_data[message.chat.id]["new_position_category"]
        name = user_data[message.chat.id]["new_position_name"]
        description = user_data[message.chat.id]["new_position_description"]
        price = user_data[message.chat.id]["new_position_price"]

        # Разделяем эмодзи и текст
        emoji = None
        text = name

        if name:
            first_char = name[0]
            if ord(first_char) > 127:
                emoji_end = 1
                while emoji_end < len(name) and ord(name[emoji_end]) > 127:
                    emoji_end += 1
                emoji = name[:emoji_end].strip()
                text = name[emoji_end:].strip()

        pos_id = add_position(cat_id, emoji, text, description, price, amount)
        display_name = f"{emoji} {text}" if emoji else text
        bot.send_message(message.chat.id, f"✅ Позиция '{display_name}' создана с ID {pos_id}!")

        del user_data[message.chat.id]
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат количества. Введите число:")
        bot.register_next_step_handler(message, process_position_amount)

# ===== /delete_position =====
@bot.message_handler(commands=['delete_position'])
def delete_position_command(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "❌ У вас нет прав на выполнение этой команды")
        return

    show_position_tree(message.chat.id, 0, None)

def show_position_tree(chat_id, cat_id, message_id):
    markup = types.InlineKeyboardMarkup(row_width=1)

    if cat_id == 0:
        markup.add(types.InlineKeyboardButton("📁 КОРЕНЬ", callback_data="info"))

        categories = get_all_categories()
        for cat in categories:
            c_id, emoji, text, description, _ = cat
            display_text = f"📁 {emoji} {text}" if emoji else f"📁 {text}"
            markup.add(types.InlineKeyboardButton(display_text, callback_data=f"navcat:{c_id}"))

        positions = get_positions_by_category(0)
        for pos in positions:
            p_id, _, emoji, text, description, _, _ = pos
            display_text = f"📦 {emoji} {text}" if emoji else f"📦 {text}"
            markup.add(types.InlineKeyboardButton(display_text, callback_data=f"delpos:{p_id}"))
    else:
        category = get_category(cat_id)
        _, emoji, text, description, _ = category
        display_text = f"{emoji} {text}" if emoji else text
        markup.add(types.InlineKeyboardButton(f"📁 {display_text}", callback_data="info"))

        positions = get_positions_by_category(cat_id)
        for pos in positions:
            p_id, _, emoji, text, description, _, _ = pos
            display_text = f"📦 {emoji} {text}" if emoji else f"📦 {text}"
            markup.add(types.InlineKeyboardButton(display_text, callback_data=f"delpos:{p_id}"))

        markup.add(types.InlineKeyboardButton("⬅️ Назад в корень", callback_data="navcat:0"))

    markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    text_msg = "⚠️ Выберите позицию для удаления или категорию для просмотра:"

    if message_id:
        try:
            bot.edit_message_text(text_msg, chat_id, message_id, reply_markup=markup)
        except:
            bot.send_message(chat_id, text_msg, reply_markup=markup)
    else:
        bot.send_message(chat_id, text_msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("navcat:"))
def navigate_category(call):
    cat_id = int(call.data.split(":")[1])
    show_position_tree(call.message.chat.id, cat_id, call.message.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delpos:"))
def process_delete_position(call):
    pos_id = int(call.data.split(":")[1])
    position = get_position(pos_id)

    if position:
        _, _, emoji, text, description, _, _ = position
        display_text = f"{emoji} {text}" if emoji else text

        delete_position(pos_id)
        bot.answer_callback_query(call.id, f"✅ Позиция удалена!")
        bot.edit_message_text(f"✅ Позиция '{display_text}' удалена", 
                             call.message.chat.id, call.message.id)
    else:
        bot.answer_callback_query(call.id, "❌ Позиция не найдена")

# ===== /edit_position =====
@bot.message_handler(commands=['edit_position'])
def edit_position_command(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "❌ У вас нет прав на выполнение этой команды")
        return

    positions = get_all_positions()

    if not positions:
        bot.send_message(message.chat.id, "❌ Нет позиций для редактирования")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for pos in positions:
        pos_id, _, emoji, text, description, _, _ = pos
        display_text = f"{emoji} {text}" if emoji else text
        markup.add(types.InlineKeyboardButton(display_text, callback_data=f"editpos:{pos_id}"))
    markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))

    bot.send_message(message.chat.id, "Выберите позицию для редактирования:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("editpos:") and len(call.data.split(":")) == 2)
def show_edit_position_menu(call):
    pos_id = int(call.data.split(":")[1])
    position = get_position(pos_id)

    if not position:
        bot.answer_callback_query(call.id, "❌ Позиция не найдена")
        return

    _, _, emoji, text, description, price, amount = position
    display_name = f"{emoji} {text}" if emoji else text

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("✏️ Изменить имя", callback_data=f"editposname:{pos_id}"),
        types.InlineKeyboardButton("📝 Изменить описание", callback_data=f"editposdesc:{pos_id}"),
        types.InlineKeyboardButton("💰 Изменить цену", callback_data=f"editposprice:{pos_id}"),
        types.InlineKeyboardButton("📊 Изменить количество", callback_data=f"editposamount:{pos_id}"),
        types.InlineKeyboardButton("❌ Отмена", callback_data="cancel")
    )

    info = f"Редактирование позиции: {display_name}\n"
    if description:
        info += f"Описание: {description}\n"
    info += f"Цена: {price}₽\n"
    info += f"Количество: {amount} шт."

    bot.edit_message_text(f"{info}\n\nЧто вы хотите изменить?", 
                         call.message.chat.id, call.message.id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("editposname:"))
def edit_position_name(call):
    pos_id = int(call.data.split(":")[1])
    user_data[call.message.chat.id] = {"edit_position_name": pos_id}
    bot.send_message(call.message.chat.id, "📝 Введите новое имя позиции (можно с эмодзи в начале):")
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, process_edit_position_name)

def process_edit_position_name(message):
    if message.text and message.text.startswith('/'):
        return

    pos_id = user_data[message.chat.id]["edit_position_name"]

    emoji = None
    text = message.text

    if message.text:
        first_char = message.text[0]
        if ord(first_char) > 127:
            emoji_end = 1
            while emoji_end < len(message.text) and ord(message.text[emoji_end]) > 127:
                emoji_end += 1
            emoji = message.text[:emoji_end].strip()
            text = message.text[emoji_end:].strip()

    update_position_text(pos_id, text)
    if emoji:
        update_position_emoji(pos_id, emoji)

    bot.send_message(message.chat.id, "✅ Имя позиции обновлено!")
    del user_data[message.chat.id]["edit_position_name"]

@bot.callback_query_handler(func=lambda call: call.data.startswith("editposdesc:"))
def edit_position_desc(call):
    pos_id = int(call.data.split(":")[1])
    user_data[call.message.chat.id] = {"edit_position_desc": pos_id}
    bot.send_message(call.message.chat.id, "📝 Введите новое описание позиции:")
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, process_edit_position_desc)

def process_edit_position_desc(message):
    if message.text and message.text.startswith('/'):
        return

    pos_id = user_data[message.chat.id]["edit_position_desc"]
    update_position_description(pos_id, message.text)
    bot.send_message(message.chat.id, "✅ Описание позиции обновлено!")
    del user_data[message.chat.id]["edit_position_desc"]

@bot.callback_query_handler(func=lambda call: call.data.startswith("editposprice:"))
def edit_position_price(call):
    pos_id = int(call.data.split(":")[1])
    user_data[call.message.chat.id] = {"edit_position_price": pos_id}
    bot.send_message(call.message.chat.id, "💰 Введите новую цену позиции (в рублях):")
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, process_edit_position_price)

def process_edit_position_price(message):
    if message.text and message.text.startswith('/'):
        return

    try:
        price = int(message.text)
        pos_id = user_data[message.chat.id]["edit_position_price"]
        update_position_price(pos_id, price)
        bot.send_message(message.chat.id, "✅ Цена позиции обновлена!")
        del user_data[message.chat.id]["edit_position_price"]
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат цены. Введите число:")
        bot.register_next_step_handler(message, process_edit_position_price)

@bot.callback_query_handler(func=lambda call: call.data.startswith("editposamount:"))
def edit_position_amount(call):
    pos_id = int(call.data.split(":")[1])
    user_data[call.message.chat.id] = {"edit_position_amount": pos_id}
    bot.send_message(call.message.chat.id, "📊 Введите новое количество:")
    bot.register_next_step_handler_by_chat_id(call.message.chat.id, process_edit_position_amount)

def process_edit_position_amount(message):
    if message.text and message.text.startswith('/'):
        return

    try:
        amount = int(message.text)
        pos_id = user_data[message.chat.id]["edit_position_amount"]
        update_position_amount(pos_id, amount)
        bot.send_message(message.chat.id, "✅ Количество обновлено!")
        del user_data[message.chat.id]["edit_position_amount"]
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат количества. Введите число:")
        bot.register_next_step_handler(message, process_edit_position_amount)

# ===== /table =====
@bot.message_handler(commands=['table'])
def send_table(message):
    if not is_admin(message.chat.id):
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

# ===== Обработчики отмены и информационных кнопок =====
@bot.callback_query_handler(func=lambda call: call.data == "cancel")
def cancel_action(call):
    bot.edit_message_text("❌ Действие отменено", call.message.chat.id, call.message.id)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "info")
def info_action(call):
    bot.answer_callback_query(call.id, "ℹ️ Это информационная кнопка")

def run():
    print("🤖 Бот запущен...")
    init_db()
    bot.infinity_polling()