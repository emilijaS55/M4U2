from  telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import schedule
import threading
import time
from config import *
from logic import DatabaseManager, hide_img

bot = TeleBot(API_TOKEN)
db = DatabaseManager(DATABASE)

# ================== КНОПКА ==================
def gen_markup(prize_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🎯 Получить!", callback_data=str(prize_id)))
    return markup


# ================== CALLBACK ==================
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    prize_id = call.data
    user_id = call.message.chat.id
    username = call.from_user.username

    if db.get_winners_count(prize_id) < 3:
        res = db.add_winner(user_id, username, prize_id)

        if res:
            img = db.get_prize(prize_id)

            # 💰 начисляем монеты
            db.add_coins(user_id, 10)

            with open(f'img/{img}', 'rb') as photo:
                bot.send_photo(
                    user_id,
                    photo,
                    caption="🎉 Ты выиграл картинку!\n💰 +10 монет"
                )
        else:
            bot.send_message(user_id, "Ты уже забрал эту картинку!")
    else:
        bot.send_message(user_id, "😢 Ты не успел! Попробуй /retry")


# ================== РАССЫЛКА ==================
def send_message():
    prize = db.get_random_prize()
    if not prize:
        return

    prize_id, img = prize[:2]

    db.mark_prize_used(prize_id)
    hide_img(img)

    for user in db.get_users():
        with open(f'hidden_img/{img}', 'rb') as photo:
            bot.send_photo(
                user,
                photo,
                caption="🔥 Новая картинка!\nУспей нажать!",
                reply_markup=gen_markup(prize_id)
            )


def schedule_thread():
    schedule.every(1).minutes.do(send_message)

    while True:
        schedule.run_pending()
        time.sleep(1)


# ================== СТАРТ ==================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    username = message.from_user.username

    if user_id in db.get_users():
        bot.send_message(user_id, "Ты уже зарегистрирован!")
    else:
        db.add_user(user_id, username)
        bot.send_message(user.chat.id, """🎮 Добро пожаловать!

Каждую минуту приходит картинка.
🏆 Первые 3 получают её
💰 За победу даются монеты

Команды:
/coins — баланс
/retry — купить попытку
/rating — рейтинг
""")


# ================== МОНЕТЫ ==================
@bot.message_handler(commands=['coins'])
def coins(message):
    user_id = message.chat.id
    coins = db.get_coins(user_id)

    bot.send_message(user_id, f"💰 У тебя {coins} монет")


# ================== RETRY ==================
@bot.message_handler(commands=['retry'])
def retry(message):
    user_id = message.chat.id
    cost = 5

    coins = db.get_coins(user_id)

    if coins >= cost:
        db.add_coins(user_id, -cost)

        prize = db.get_random_prize()
        if not prize:
            bot.send_message(user_id, "Нет доступных картинок 😢")
            return

        prize_id, img = prize[:2]

        with open(f'img/{img}', 'rb') as photo:
            bot.send_photo(user_id, photo, caption="🎁 Ты купил попытку!")
    else:
        bot.send_message(user_id, "❌ Недостаточно монет")


# ================== РЕЙТИНГ ==================
@bot.message_handler(commands=['rating'])
def rating(message):
    res = db.get_rating()

    text = "🏆 Рейтинг:\n\n"
    for i, user in enumerate(res, start=1):
        text += f"{i}. @{user[0]} — {user[1]} побед\n"

    bot.send_message(message.chat.id, text)


# ================== АДМИН ==================
@bot.message_handler(commands=['add'])
def add_image(message):
    if message.chat.id not in ADMINS:
        return

    if message.reply_to_message and message.reply_to_message.photo:
        bot.send_message(message.chat.id, "✅ Картинка добавлена (можно доработать сохранение)")


# ================== ЗАПУСК ==================
def polling():
    bot.polling(none_stop=True)


if __name__ == '__main__':
    db.create_tables()

    t1 = threading.Thread(target=polling)
    t2 = threading.Thread(target=schedule_thread)

    t1.start()
    t2.start()