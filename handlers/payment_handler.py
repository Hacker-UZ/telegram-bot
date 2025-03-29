from telebot import types
from config import MIN_WITHDRAWAL, CURRENCY
from database import get_user, update_user
import sqlite3
from datetime import datetime

def format_money(amount):
    return f"{amount:,} so'm"

def setup_payment_handler(bot, admin_id):
    @bot.callback_query_handler(func=lambda call: call.data == "withdraw")
    def handle_withdraw(call):
        user_id = call.from_user.id
        conn = sqlite3.connect('pul_yutish.db')
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        balance = cursor.fetchone()[0]
        conn.close()

        if balance < MIN_WITHDRAWAL:
            bot.send_message(
                call.message.chat.id,
                f"❌ Minimal pul yechish miqdori {format_money(MIN_WITHDRAWAL)}\n"
                f"Sizning balansingiz: {format_money(balance)}"
            )
            return

        # Aniq formatda so'rov yuboramiz
        msg = bot.send_message(
            call.message.chat.id,
            "💳 Pul yechish uchun quyidagi formatda ma'lumotlarni yuboring:\n\n"
            "8600123456789012\n"
            "John Doe\n\n"
            "1-qator: Karta raqami (faqat raqamlar)\n"
            "2-qator: Karta egasining ismi (lotin harflarida)"
        )
        bot.register_next_step_handler(msg, process_payment_info, user_id, balance)

    def process_payment_info(message, user_id, amount):
        try:
            # Ma'lumotlarni ajratib olish
            data = message.text.split('\n')
            if len(data) < 2:
                raise ValueError("Ma'lumotlar to'liq kiritilmagan")
            
            card_number = data[0].strip()
            card_holder = data[1].strip()
            
            # Karta raqamini tekshirish
            if not card_number.isdigit() or len(card_number) < 12:
                raise ValueError("Noto'g'ri karta raqami formati")

            # Ma'lumotlarni bazaga saqlash
            conn = sqlite3.connect('pul_yutish.db')
            cursor = conn.cursor()
            
            cursor.execute('''INSERT INTO payments 
                            (user_id, card_number, card_holder, amount, request_date)
                            VALUES (?, ?, ?, ?, ?)''',
                         (user_id, card_number, card_holder, amount, 
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            # Balansni yangilash
            cursor.execute("UPDATE users SET balance=0 WHERE user_id=?", (user_id,))
            
            conn.commit()
            conn.close()
            
            # Foydalanuvchiga xabar
            bot.send_message(
                message.chat.id,
                f"✅ {format_money(amount)} miqdordagi to'lov so'rovingiz qabul qilindi!\n"
                "Adminlarimiz 24 soat ichida to'lovni amalga oshiradilar.\n\n"
                f"💳 Karta raqami: {card_number[:4]} **** **** {card_number[-4:]}\n"
                f"👤 Karta egasi: {card_holder}"
            )
            
            # Adminlarga xabar
            notify_admin(user_id, card_number, card_holder, amount)
            
        except Exception as e:
            bot.send_message(
                message.chat.id,
                f"❌ Xato: {str(e)}\n\n"
                "Iltimos, ma'lumotlarni quyidagi formatda qayta yuboring:\n\n"
                "8600123456789012\n"
                "John Doe\n\n"
                "1-qator: Karta raqami\n"
                "2-qator: Karta egasining ismi"
            )

    def notify_admin(user_id, card_number, card_holder, amount):
        conn = sqlite3.connect('pul_yutish.db')
        cursor = conn.cursor()
        
        # Foydalanuvchi ma'lumotlari
        cursor.execute("SELECT username, full_name FROM users WHERE user_id=?", (user_id,))
        username, full_name = cursor.fetchone()
        
        keyboard = types.InlineKeyboardMarkup()
        btn_confirm = types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"confirm_pay_{user_id}")
        btn_reject = types.InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_pay_{user_id}")
        keyboard.add(btn_confirm, btn_reject)
        
        bot.send_message(
            admin_id,
            f"🆕 Yangi to'lov so'rovi:\n\n"
            f"👤 Foydalanuvchi: @{username} ({full_name})\n"
            f"💰 Miqdor: {format_money(amount)}\n"
            f"💳 Karta raqami: {card_number}\n"
            f"👤 Karta egasi: {card_holder}\n\n"
            f"📅 Sana: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            reply_markup=keyboard
        )