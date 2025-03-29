import telebot
from config import ADMIN_ID, BOT_TOKEN
from database import init_db
from handlers.user_handlers import setup_user_handlers
from handlers.payment_handler import setup_payment_handler
from handlers.admin_handlers import setup_admin_handlers
from keep_alive import keep_alive
keep_alive()

bot = telebot.TeleBot(BOT_TOKEN)

def main():
    # Ma'lumotlar bazasini ishga tushirish
    init_db()
    
    # Handlerlarni sozlash
    setup_user_handlers(bot)
    setup_payment_handler(bot, ADMIN_ID)
    setup_admin_handlers(bot, ADMIN_ID)
    
    print("Bot ishga tushdi...")
    bot.infinity_polling()

if __name__ == '__main__':
    main()