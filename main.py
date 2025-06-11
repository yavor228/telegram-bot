# Install the required package: python-telegram-bot
# pip install python-telegram-bot --upgrade

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)
import sqlite3
import os
import random
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise EnvironmentError("BOT_TOKEN not found in environment variables. Please check your .env file.")

DATE, TYPE, DURATION = range(3)

MOTIVATION_LIST = [
    "Не зупиняйся, навіть якщо важко.",
    "Твоє тіло працює — і результати не за горами.",
    "Кожне тренування наближає тебе до мети.",
    "Зроби сьогодні те, за що завтра подякуєш собі.",
    "Сила в регулярності — не здавайся."
]

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        ["➕ Додати", "📋 Останні"],
        ["📊 Статистика", "💡 Мотивація"],
        ["🗑 Очистити"]
    ],
    resize_keyboard=True
)

def init_db():
    conn = sqlite3.connect("trainings.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trainings (
            user_id INTEGER,
            date TEXT,
            type TEXT,
            duration INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Вибери дію з меню нижче:", reply_markup=keyboard
    )

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📅 Введи дату тренування (напр. 2025-05-20):")
    return DATE

async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['date'] = update.message.text
    await update.message.reply_text("🏋️ Тип тренування:")
    return TYPE

async def get_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['type'] = update.message.text
    await update.message.reply_text("⏱ Тривалість у хвилинах:")
    return DURATION

async def get_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        duration = int(update.message.text)
    except ValueError:
        await update.message.reply_text("⚠️ Введи число.")
        return DURATION

    user_id = update.message.from_user.id
    date = context.user_data['date']
    type_ = context.user_data['type']

    conn = sqlite3.connect("trainings.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO trainings (user_id, date, type, duration) VALUES (?, ?, ?, ?)",
        (user_id, date, type_, duration)
    )
    conn.commit()
    conn.close()

    await update.message.reply_text("✅ Тренування збережено!", reply_markup=keyboard)
    return ConversationHandler.END

async def list_trainings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    conn = sqlite3.connect("trainings.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT date, type, duration FROM trainings WHERE user_id = ? ORDER BY date DESC LIMIT 5",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("У тебе ще немає тренувань.")
        return

    msg = "📋 Останні тренування:\n"
    for row in rows:
        msg += f"{row[0]} — {row[1]}, {row[2]} хв\n"
    await update.message.reply_text(msg)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    conn = sqlite3.connect("trainings.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(duration) FROM trainings WHERE user_id = ?", (user_id,))
    total, minutes = cursor.fetchone()
    cursor.execute("SELECT type, COUNT(*) FROM trainings WHERE user_id = ? GROUP BY type", (user_id,))
    by_type = cursor.fetchall()
    conn.close()

    msg = f"📊 Всього тренувань: {total or 0}\n🕒 Загальна тривалість: {minutes or 0} хв\n"
    if by_type:
        msg += "\nТипи тренувань:\n"
        for t, c in by_type:
            msg += f"– {t}: {c}\n"
    await update.message.reply_text(msg)

async def motivate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💡 {random.choice(MOTIVATION_LIST)}")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    conn = sqlite3.connect("trainings.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM trainings WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text("🗑 Всі тренування видалено.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Скасовано.")
    return ConversationHandler.END

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "➕ Додати":
        return await add(update, context)
    elif text == "📋 Останні":
        return await list_trainings(update, context)
    elif text == "📊 Статистика":
        return await stats(update, context)
    elif text == "💡 Мотивація":
        return await motivate(update, context)
    elif text == "🗑 Очистити":
        return await clear(update, context)
    else:
        await update.message.reply_text("Команда не розпізнана.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Додати$"), add)],
        states={
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)],
            TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_type)],
            DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_duration)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

    print("Бот запущено.")
    app.run_polling()

if __name__ == '__main__':
    main()
