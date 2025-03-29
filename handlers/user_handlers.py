from telebot import types
from datetime import datetime
import sqlite3
from config import INITIAL_SPINS, REFERAL_BONUS, PRIZES, CURRENCY, MIN_WITHDRAWAL, ADMIN_ID, REFERAL_SPINS
import random



def get_random_prize():
    return random.choice(PRIZES)

def format_money(amount):
    return f"{amount:,} so'm"

def setup_user_handlers(bot):
    @bot.message_handler(commands=['start'])
    def handle_start(message):
        user_id = message.from_user.id
        username = message.from_user.username or ""
        full_name = message.from_user.full_name or ""

        # Foydalanuvchini bazaga qo'shish
        conn = sqlite3.connect('pul_yutish.db')
        cursor = conn.cursor()
        
        # Foydalanuvchi mavjudligini tekshirish
        cursor.execute("SELECT spins_left FROM users WHERE user_id=?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            # Yangi foydalanuvchi
            cursor.execute(
                "INSERT INTO users (user_id, username, full_name, spins_left) VALUES (?, ?, ?, ?)",
                (user_id, username, full_name, INITIAL_SPINS)
            )
            spins_left = INITIAL_SPINS
        else:
            spins_left = user[0]

        # Referalni tekshirish
        if len(message.text.split()) > 1:
            referal_code = message.text.split()[1]
            if referal_code.startswith('ref'):
                referer_id = int(referal_code[3:])
                if referer_id != user_id:  # O'ziga referal qilishni oldini olish
                    # Referalni qo'shamiz
                    cursor.execute(
                        "INSERT INTO referals (referer_id, referee_id, date) VALUES (?, ?, ?)",
                        (referer_id, user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    )
                    # Referal egasiga bonus beramiz
                    cursor.execute(
                        "UPDATE users SET spins_left=spins_left+?, balance=balance+? WHERE user_id=?",
                        (REFERAL_SPINS, REFERAL_BONUS, referer_id)
                    )
                    
                    try:
                        bot.send_message(
                            referer_id,
                            f"🎉 Yangi referalingiz @{username} ro'yxatdan o'tdi!\n"
                            f"Sizga *{REFERAL_BONUS}* so'm bonus berildi!",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        print(f"Xabar yuborishda xato: {e}")

        conn.commit()
        conn.close()

        # Kanal obunasini tekshirish
        check_subscription(message)

    def check_subscription(message):
        user_id = message.from_user.id
        conn = sqlite3.connect('pul_yutish.db')
        cursor = conn.cursor()
        
        # Barcha majburiy kanallarni olish
        cursor.execute("SELECT channel_id, channel_name FROM channels")
        channels = cursor.fetchall()
        
        if not channels:
            # Agar kanal qo'shilmagan bo'lsa, oddiy menyuni ko'rsatamiz
            show_main_menu(message)
            return
        
        # Foydalanuvchi obuna bo'lmagan kanallarni aniqlash
        unsubscribed = []
        for channel_id, channel_name in channels:
            try:
                member = bot.get_chat_member(channel_id, user_id)
                if member.status not in ['member', 'administrator', 'creator']:
                    unsubscribed.append((channel_id, channel_name))
            except Exception as e:
                print(f"Kanal obunasini tekshirishda xato: {e}")
                unsubscribed.append((channel_id, channel_name))
        
        if unsubscribed:
            # Obuna bo'lish uchun kanallarni ko'rsatamiz
            keyboard = types.InlineKeyboardMarkup()
            for channel_id, channel_name in unsubscribed:
                keyboard.add(types.InlineKeyboardButton(
                    text=f"👉 {channel_name}",
                    url=f"https://t.me/{channel_id[1:] if channel_id.startswith('@') else channel_id}"
                ))
            
            keyboard.add(types.InlineKeyboardButton(
                text="✅ Obunani tekshirish",
                callback_data="check_subscription"
            ))
            
            bot.send_message(
                message.chat.id,
                "📢 Botdan to'liq foydalanish uchun quyidagi kanallarga obuna bo'ling:",
                reply_markup=keyboard
            )
        else:
            # Barcha kanallarga obuna bo'lgan
            show_main_menu(message)

    @bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
    def handle_check_subscription(call):
        user_id = call.from_user.id
        conn = sqlite3.connect('pul_yutish.db')
        cursor = conn.cursor()
        
        # Barcha kanallarni olish
        cursor.execute("SELECT channel_id, channel_name FROM channels")
        channels = cursor.fetchall()
        
        # Har bir kanalda obuna bo'lganligini tekshirish
        all_subscribed = True
        for channel_id, channel_name in channels:
            try:
                member = bot.get_chat_member(channel_id, user_id)
                if member.status not in ['member', 'administrator', 'creator']:
                    all_subscribed = False
                    break
                
                # Bazaga obunani qo'shamiz
                cursor.execute(
                    "INSERT OR IGNORE INTO user_subscriptions (user_id, channel_id, subscribe_date) VALUES (?, ?, ?)",
                    (user_id, channel_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
            except Exception as e:
                print(f"Error checking subscription: {e}")
                all_subscribed = False
                break
        
        if all_subscribed:
            conn.commit()
            bot.answer_callback_query(call.id, "✅ Barcha kanallarga obuna bo'ldingiz!")
            show_main_menu(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Hali barcha kanallarga obuna bo'lmagansiz!", show_alert=True)
            check_subscription(call.message)
        
        conn.close()

    def show_main_menu(message):
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
        keyboard.row(types.KeyboardButton("🎡 Aylantirish"))
        
        keyboard.row(
            types.KeyboardButton("💰 Balans"),
            types.KeyboardButton("👥 Do'stlarni taklif qilish")
        )

        # Agar admin bo'lsa, "👑 Admin" tugmasini qo'shamiz
        if user_id == ADMIN_ID:
            keyboard.row(types.KeyboardButton("👑 Admin"))


        
        bot.send_message(
            message.chat.id,
            f"🎰 *Pul Yutish Botiga xush kelibsiz!*\n\n"
            f"💵 Balans: {format_money(balance)}\n"
            f"🎡 Aylantirishlar: {spins_left}\n\n"
            f"Har bir do'stingizni taklif qilganingizda *{REFERAL_BONUS}* so'm bonus olasiz!",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    @bot.message_handler(func=lambda m: m.text == "🎡 Aylantirish")
    def handle_spin(message):
        user_id = message.from_user.id
        conn = sqlite3.connect('pul_yutish.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT spins_left, balance FROM users WHERE user_id=?", (user_id,))
        spins_left, balance = cursor.fetchone()
        
        if spins_left <= 0:
            bot.send_message(message.chat.id, 
                f"ℹ️ *Sizda aylantirish imkoniyati qolmadi.* \n\n"
                f"👥 Do'stlaringizni taklif qiling!\n"
                f"✅ Har bir do'stingizni taklif qilganingizda *{REFERAL_BONUS}* so'm bonus olasiz!",
                parse_mode="Markdown"
            )
            conn.close()
            return
        
        # Aylantirish jarayoni
        prize = get_random_prize()
        new_balance = balance + prize
        new_spins = spins_left - 1
        
        # Bazaga yozish
        cursor.execute(
            "UPDATE users SET balance=?, spins_left=? WHERE user_id=?",
            (new_balance, new_spins, user_id)
        )
        cursor.execute(
            "INSERT INTO prizes (user_id, amount, date) VALUES (?, ?, ?)",
            (user_id, prize, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        
        conn.commit()
        conn.close()
        
        bot.send_message(
            message.chat.id,
            f"🎉 Tabriklaymiz! Siz yutdingiz: *{format_money(prize)}*!\n\n"
            f"💵 Yangi balans: {format_money(new_balance)}\n"
            f"🎡 Qolgan aylantirishlar: {new_spins}",
            parse_mode="Markdown"
        )

    @bot.message_handler(func=lambda m: m.text == "💰 Balans")
    def handle_balance(message):
        user_id = message.from_user.id
        conn = sqlite3.connect('pul_yutish.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        balance = cursor.fetchone()[0]
        conn.close()
        
        keyboard = types.InlineKeyboardMarkup()
        if balance >= MIN_WITHDRAWAL:
            keyboard.add(types.InlineKeyboardButton("💳 Pul yechish", callback_data="withdraw"))
        
        bot.send_message(
            message.chat.id,
            f"💵 Sizning balansingiz: *{format_money(balance)}*\n\n"
            f"💸 Minimal pul yechish miqdori: {format_money(MIN_WITHDRAWAL)}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    @bot.message_handler(func=lambda m: m.text == "👥 Do'stlarni taklif qilish")
    def handle_referal(message):
        user_id = message.from_user.id
        bot.send_message(
            message.chat.id,
            f"<b>💁‍♂ Yana bepul baraban aylantirishni istaysizmi?</b>\n\n"
            f"<b>👤 Har bir taklif qilingan kishi sizga 1️⃣ marotaba baraban aylantirish imkonini beradi.</b>\n\n"
            f"<b>💸 Bundan tashqari har bir taklif qilgan kishi uchun biz 500 soʻmdan toʻlaymiz.</b>\n",
            parse_mode="HTML" 
        )
        bot.send_message(
            message.chat.id,
            f"<b>📯 Baraban aylantirib pul ishlash vaqti keldi!</b>\n\n"
            f"Omad barabani [bot] - da turli imkoniyatlarni sinab pul ishlang\n\n"
            f"https://t.me/{bot.get_me().username}?start=ref{user_id}\n\n",
            parse_mode="HTML" 
        )