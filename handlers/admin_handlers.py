from telebot import types
from datetime import datetime
import sqlite3
from config import ADMIN_ID, REFERAL_BONUS
import telebot
from telebot.apihelper import ApiTelegramException

def format_money(amount):
    return f"{amount:,} so'm"

def validate_markdown(text):
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text

def setup_admin_handlers(bot_instance, admin_id):
    global bot
    bot = bot_instance
    @bot.message_handler(commands=['admin'])
    def handle_admin(message):
        if message.from_user.id != admin_id:
            bot.send_message(message.chat.id, "❌ Sizga ruxsat yo'q!")
            return
        
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("📊 Statistika")
        btn2 = types.KeyboardButton("💸 To'lov so'rovlari")
        btn3 = types.KeyboardButton("📢 Kanallar")
        btn5 = types.KeyboardButton("🔙 Asosiy menyu")
        keyboard.add(btn1, btn2, btn3, btn5)
        
        bot.send_message(
            message.chat.id,
            "👑 *Admin paneli*",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    @bot.message_handler(func=lambda m: m.text == "📊 Statistika" and m.from_user.id == admin_id)
    def show_stats(message):
        conn = sqlite3.connect('pul_yutish.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM referals")
        total_referals = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(amount) FROM payments WHERE status='completed'")
        total_payout = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(amount) FROM prizes")
        total_prizes = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM payments WHERE status='pending'")
        pending_payments = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM channels")
        total_channels = cursor.fetchone()[0]
        
        conn.close()
        
        bot.send_message(
            message.chat.id,
            f"📊 *Bot statistikasi*\n\n"
            f"👥 Jami foydalanuvchilar: {total_users}\n"
            f"🤝 Jami referallar: {total_referals}\n"
            f"📢 Jami kanallar: {total_channels}\n"
            f"🎯 Jami yutqazilgan summa: {format_money(total_prizes)}\n"
            f"💰 Jami to'langan summa: {format_money(total_payout)}\n"
            f"⏳ Ko'rib chiqilishi kerak bo'lgan to'lovlar: {pending_payments}",
            parse_mode="Markdown"
        )

    @bot.message_handler(func=lambda m: m.text == "💸 To'lov so'rovlari" and m.from_user.id == admin_id)
    def show_payment_requests(message):
        conn = sqlite3.connect('pul_yutish.db')
        cursor = conn.cursor()

        cursor.execute('''SELECT p.id, u.username, p.card_number, p.card_holder, p.amount, p.request_date 
                        FROM payments p
                        JOIN users u ON p.user_id = u.user_id
                        WHERE p.status='pending'
                        ORDER BY p.request_date DESC''')
        requests = cursor.fetchall()
        conn.close()

        if not requests:
            bot.send_message(message.chat.id, "⏳ Hozircha yangi to'lov so'rovlari mavjud emas.")
            return

        for req in requests:
            req_id, username, card_number, card_holder, amount, req_date = req

            # Karta raqamini yashirib ko'rsatamiz
            masked_card = f"**** **** **** {card_number[-4:]}" if card_number and len(card_number) >= 4 else "Noma'lum"

            keyboard = types.InlineKeyboardMarkup()
            btn_confirm = types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"confirm_pay_{req_id}")
            btn_reject = types.InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_pay_{req_id}")
            keyboard.add(btn_confirm, btn_reject)

            bot.send_message(
                message.chat.id,
                f"🆔 So'rov ID: {req_id}\n"
                f"👤 Foydalanuvchi: @{username}\n"
                f"💰 Miqdor: {format_money(amount)}\n"
                f"💳 Karta raqami: {card_number}\n"
                f"👤 Karta egasi: {card_holder}\n"
                f"📅 Sana: {req_date}",
                reply_markup=keyboard
            )

    @bot.message_handler(func=lambda m: m.text == "📢 Kanallar" and m.from_user.id == admin_id)
    def handle_channels_menu(message):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("➕ Kanal qo'shish")
        btn2 = types.KeyboardButton("➖ Kanal olib tashlash")
        btn3 = types.KeyboardButton("📋 Kanallar ro'yxati")
        btn4 = types.KeyboardButton("🔙 Admin menyusi")
        keyboard.add(btn1, btn2, btn3, btn4)
        
        bot.send_message(
            message.chat.id,
            "📢 *Majburiy kanallar boshqaruvi*",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    @bot_instance.message_handler(func=lambda m: m.text == "🔙 Admin menyusi" and m.from_user.id == admin_id)
    def back_to_admin_main_menu(message):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.row(
            types.KeyboardButton("📊 Statistika"),
            types.KeyboardButton("💸 To'lov so'rovlari"),
            types.KeyboardButton("📢 Kanallar")
        )
        keyboard.row(
            types.KeyboardButton("🔙 Asosiy menyu")
        )
        
        bot_instance.send_message(
            message.chat.id,
            "👑 *Admin paneli*",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    # Kanalar menyusini yaratishda tugmani qo'shamiz
    @bot_instance.message_handler(func=lambda m: m.text == "📢 Kanallar" and m.from_user.id == admin_id)
    def handle_channels_menu(message):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.row(
            types.KeyboardButton("➕ Kanal qo'shish"),
            types.KeyboardButton("➖ Kanal olib tashlash")
        )
        keyboard.row(
            types.KeyboardButton("📋 Kanallar ro'yxati"),
            types.KeyboardButton("🔙 Admin menyusi")  # Yangi qo'shilgan tugma
        )
        
        bot_instance.send_message(
            message.chat.id,
            "📢 *Majburiy kanallar boshqaruvi*",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    @bot.message_handler(func=lambda m: m.text == "➕ Kanal qo'shish" and m.from_user.id == admin_id)
    def handle_add_channel(message):
        msg = bot.send_message(
            message.chat.id,
            "Yangi kanal qo'shish uchun kanal username yoki ID sini yuboring:\n\n"
            "Namuna: @channel_name yoki -1001234567890\n\n"
            "❗ Kanalga bot admin qilinganligiga ishonch hosil qiling!"
        )
        bot.register_next_step_handler(msg, process_add_channel)

    def process_add_channel(message):
        if message.text in ["📋 Kanallar ro'yxati", "➖ Kanal olib tashlash", "🔙 Admin menyusi"]:
            bot.send_message(
                message.chat.id,
                "❌ Iltimos, avval kanal username yoki ID sini kiriting yoki boshqa tugmani bosmang."
            )
            return

        channel_id = message.text.strip()
        try:
            chat = bot.get_chat(channel_id)
            
            conn = sqlite3.connect('pul_yutish.db')
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO channels (channel_id, channel_name, added_by, add_date) VALUES (?, ?, ?, ?)",
                (channel_id, chat.title, message.from_user.id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            
            conn.commit()
            conn.close()
            
            bot.send_message(
                message.chat.id,
                f"✅ Kanal qo'shildi: {chat.title} ({channel_id})"
            )
        except Exception as e:
            bot.send_message(
                message.chat.id,
                f"❌ Xato: {str(e)}\nKanal qo'shilmadi. Iltimos, to'g'ri kanal username yoki ID sini kiriting."
            )

    @bot.message_handler(func=lambda m: m.text == "➖ Kanal olib tashlash" and m.from_user.id == admin_id)
    def handle_remove_channel(message):
        conn = sqlite3.connect('pul_yutish.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT channel_id, channel_name FROM channels")
        channels = cursor.fetchall()
        conn.close()
        
        if not channels:
            bot.send_message(message.chat.id, "❌ Hozircha kanallar mavjud emas")
            return
        
        keyboard = types.InlineKeyboardMarkup()
        for channel_id, channel_name in channels:
            keyboard.add(types.InlineKeyboardButton(
                text=f"❌ {channel_name}",
                callback_data=f"remove_channel_{channel_id}"
            ))
        
        bot.send_message(
            message.chat.id,
            "Olib tashlamoqchi bo'lgan kanalni tanlang:",
            reply_markup=keyboard
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith('remove_channel_'))
    def handle_remove_channel_callback(call):
        if call.from_user.id != admin_id:
            bot.answer_callback_query(call.id, "❌ Sizga ruxsat yo'q!")
            return

        channel_id = call.data.split('remove_channel_')[-1]  # Ensure correct parsing of channel_id

        conn = sqlite3.connect('pul_yutish.db')
        cursor = conn.cursor()

        try:
            # Fetch the channel name for confirmation
            cursor.execute("SELECT channel_name FROM channels WHERE channel_id=?", (channel_id,))
            result = cursor.fetchone()
            if not result:
                bot.answer_callback_query(call.id, "❌ Kanal topilmadi!")
                return

            channel_name = result[0]

            # Delete the channel and related subscriptions
            cursor.execute("DELETE FROM channels WHERE channel_id=?", (channel_id,))
            cursor.execute("DELETE FROM user_subscriptions WHERE channel_id=?", (channel_id,))
            conn.commit()

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"✅ Kanal olib tashlandi: {channel_name}"
            )
            bot.answer_callback_query(call.id, "✅ Kanal muvaffaqiyatli olib tashlandi!")
        except Exception as e:
            conn.rollback()
            bot.answer_callback_query(call.id, f"❌ Xato: {str(e)}")
            print(f"Error removing channel: {e}")
        finally:
            conn.close()

    @bot.message_handler(func=lambda m: m.text == "📋 Kanallar ro'yxati" and m.from_user.id == admin_id)
    def handle_list_channels(message):
        conn = sqlite3.connect('pul_yutish.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT channel_id, channel_name FROM channels")
        channels = cursor.fetchall()
        conn.close()
        
        if not channels:
            bot.send_message(message.chat.id, "❌ Hozircha kanallar mavjud emas")
            return
        
        try:
            response = "📋 *Majburiy kanallar ro'yxati:*\n\n"
            for i, (channel_id, channel_name) in enumerate(channels, 1):
                response += f"{i}. {channel_name} ({channel_id})\n"
            response = validate_markdown(response)  # Validate and escape Markdown
            bot.send_message(message.chat.id, response, parse_mode="Markdown")
        except ApiTelegramException as e:
            error_message = f"Failed to send message: {e.description}"
            bot.send_message(message.chat.id, error_message)
            # Optionally log the error or notify the admin
            print(error_message)

    @bot.message_handler(func=lambda m: m.text == "💸 To'lov so'rovlari" and m.from_user.id == admin_id)
    def show_payment_requests(message):
        try:
            conn = sqlite3.connect('pul_yutish.db')
            cursor = conn.cursor()
            
            cursor.execute('''SELECT p.id, u.username, p.card_holder, p.amount, p.request_date 
                            FROM payments p
                            JOIN users u ON p.user_id = u.user_id
                            WHERE p.status='pending'
                            ORDER BY p.request_date DESC''')
            requests = cursor.fetchall()
            conn.close()
            
            if not requests:
                bot.send_message(message.chat.id, "⏳ Hozircha yangi to'lov so'rovlari mavjud emas.")
                return
            
            for req in requests:
                req_id, username, card_holder, card_number, amount, req_date = req
                
                keyboard = types.InlineKeyboardMarkup()
                btn_confirm = types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"confirm_pay_{req_id}")
                btn_reject = types.InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_pay_{req_id}")
                keyboard.add(btn_confirm, btn_reject)
                
                bot.send_message(
                    message.chat.id,
                    f"🆔 So'rov ID: {req_id}\n"
                    f"👤 Foydalanuvchi: @{username}\n"
                    f"💳 Karta raqami: {card_number}\n"
                    f"👤 Karta egasi: {card_holder}\n"
                    f"💰 Miqdor: {format_money(amount)}\n"
                    f"📅 Sana: {req_date}",
                    reply_markup=keyboard
                )
        except Exception as e:
            print(f"Show payment requests error: {e}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith(('confirm_pay_', 'reject_pay_')))
    def handle_payment_decision(call):
        if call.from_user.id != admin_id:
            bot.answer_callback_query(call.id, "❌ Sizga ruxsat yo'q!")
            return
        
        req_id = call.data.split('_')[-1]
        conn = None
        try:
            conn = sqlite3.connect('pul_yutish.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT user_id, amount FROM payments WHERE id=?", (req_id,))
            result = cursor.fetchone()
            
            if not result:
                bot.answer_callback_query(call.id, "❌ So'rov topilmadi!")
                return
                
            user_id, amount = result
            
            if call.data.startswith('confirm_pay_'):
                cursor.execute("UPDATE payments SET status='completed' WHERE id=?", (req_id,))
                bot.answer_callback_query(call.id, "✅ To'lov tasdiqlandi!")
                bot.send_message(
                    user_id,
                    f"✅ {format_money(amount)} miqdordagi to'lovingiz tasdiqlandi!\n"
                    "Pul 10 daqiqa ichida kartangizga tushadi."
                )
            else:
                cursor.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, user_id))
                cursor.execute("UPDATE payments SET status='rejected' WHERE id=?", (req_id,))
                bot.answer_callback_query(call.id, "❌ To'lov rad etildi!")
                bot.send_message(
                    user_id,
                    f"❌ {format_money(amount)} miqdordagi to'lov so'rovingiz rad etildi.\n"
                    f"💰 {format_money(amount)} miqdor hisobingizga qaytarildi."
                )
            
            conn.commit()
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"{call.message.text}\n\n🔹 Status: {'✅ Tasdiqlangan' if call.data.startswith('confirm_pay_') else '❌ Rad etilgan'}",
                reply_markup=None
            )
            
        except Exception as e:
            if conn:
                conn.rollback()
            bot.answer_callback_query(call.id, f"❌ Xato: {str(e)}")
            print(f"Payment decision error: {e}")
        finally:
            if conn:
                conn.close()
        # Xabarni yangilash
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"{call.message.text}\n\n🔹 Status: {'✅ Tasdiqlangan' if call.data.startswith('confirm_pay_') else '❌ Rad etilgan'}",
            reply_markup=None
        )

    @bot.message_handler(func=lambda m: m.text == "🔙 Asosiy menyu" and m.from_user.id == admin_id)
    def back_to_main_menu(message):
        try:
            user_id = message.from_user.id
            conn = sqlite3.connect('pul_yutish.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT balance, spins_left FROM users WHERE user_id=?", (user_id,))
            user_data = cursor.fetchone()
            conn.close()
            
            if not user_data:
                balance = 0
                spins_left = 0
            else:
                balance, spins_left = user_data
            
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.row(
                types.KeyboardButton("💰 Balans"),
                types.KeyboardButton("🎡 Aylantirish"),
                types.KeyboardButton("👥 Do'stlarni taklif qilish")
            )
            if user_id == ADMIN_ID:
                keyboard.row(types.KeyboardButton("👑 Admin"))

            bot.send_message(
                message.chat.id,
                f"🎰 *Pul Yutish Boti Asosiy Menu!*\n\n"
                f"💵 Balans: {format_money(balance)}\n"
                f"🎡 Aylantirishlar: {spins_left}",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Xato yuz berdi: {e}")
            bot.send_message(message.chat.id, "❌ Xato yuz berdi. Iltimos, qayta urinib ko'ring.")

    @bot.message_handler(func=lambda m: m.text == "👑 Admin" and m.from_user.id == admin_id)
    def handle_admin_menu(message):
        handle_admin(message)