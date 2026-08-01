import os, asyncio, threading, logging
from flask import Flask, request, jsonify
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import BOT_TOKEN, WEBAPP_URL, OWNER_ID, CATEGORIES
from database import *
from handlers import *
from words import WORDS

app = Flask(__name__)
ml = asyncio.new_event_loop()

def sl():
    asyncio.set_event_loop(ml)
    ml.run_forever()

threading.Thread(target=sl, daemon=True).start()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Команды
dp.message.register(start_cmd, Command("start"))
dp.message.register(ref_menu, F.text == "👥 Рефералы")
dp.message.register(vip_menu, F.text == "💎 VIP")
dp.message.register(quick_test, F.text == "🎯 Быстрый тест")
dp.message.register(ege_test, F.text == "📝 Тест ЕГЭ")
dp.message.register(lambda m: show_stats_handler(m), F.text == "📊 Статистика")

# Callback-и
dp.callback_query.register(check_quick_cb, lambda c: c.data.startswith("ans_"))
dp.callback_query.register(toggle_ege_cb, lambda c: c.data.startswith("ege_") and c.data not in ("ege_check", "ege_reset"))
dp.callback_query.register(lambda c: user_sessions.get(c.from_user.id, {}).update({'selected_nums': []}) or c.answer("Сброшено"), lambda c: c.data == "ege_reset")
dp.callback_query.register(check_ege_cb, lambda c: c.data == "ege_check")
dp.callback_query.register(lambda c: quick_test(c.message) or c.answer(), lambda c: c.data == "next_q")
dp.callback_query.register(lambda c: ege_test(c.message) or c.answer(), lambda c: c.data == "next_ege")
dp.callback_query.register(lambda c: show_stats_handler(c), lambda c: c.data == "show_stats")
dp.callback_query.register(lambda c: c.message.edit_text("✅ Заявка отправлена!") or c.answer(), lambda c: c.data == "confirm_vip")

@app.route('/webhook', methods=['POST'])
def fw():
    future = asyncio.run_coroutine_threadsafe(dp.feed_webhook_update(bot, request.get_json()), ml)
    future.result()
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get('PORT', 8080))
    async def sw():
        try: await bot.delete_webhook(); await bot.set_webhook(f"{WEBAPP_URL}/webhook"); logging.info("OK")
        except Exception as e: logging.error(f"Error: {e}")
    asyncio.run_coroutine_threadsafe(sw(), ml)
    app.run(host='0.0.0.0', port=port)
