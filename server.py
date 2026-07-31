import os, random, sqlite3, asyncio, threading, logging
from flask import Flask, request, jsonify
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from words import WORDS

BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
WEBAPP_URL = os.environ.get('WEBAPP_URL', '')

CATEGORIES = {
    "all": "Все слова",
    "nouns": "Существительные",
    "adjectives": "Прилагательные",
    "verbs": "Глаголы",
    "participles": "Причастия",
    "gerunds": "Деепричастия",
    "adverbs": "Наречия"
}

WORDS_BY_CATEGORY = {
    "nouns": ["аэропОрты", "бАнты", "бОроду", "бухгАлтеров", "вероисповЕдание", "водопровОд",
              "газопровОд", "граждАнство", "дефИс", "дешевИзна", "диспансЕр", "договорЁнность",
              "докумЕнт", "досУг", "еретИк", "жалюзИ", "знАчимость", "Иксы", "каталОг",
              "квартАл", "киломЕтр", "кОнусов", "корЫсть", "крАны", "кремЕнь", "лЕкторов",
              "лОктя", "лыжнЯ", "мЕстностей", "намЕрение", "нарОст", "нЕдруг", "недУг",
              "некролОг", "нЕнависть", "нефтепровОд", "новостЕй", "нОгтя", "Отзыв", "отзЫв",
              "Отрочество", "партЕр", "портфЕль", "пОручни", "придАное", "призЫв", "свЁкла",
              "сирОты", "созЫв", "сосредотОчение", "срЕдства", "стАтуя", "столЯр", "тамОжня",
              "тОрты", "тУфля", "цемЕнт", "цЕнтнер", "цепОчка", "шАрфы", "шофЁр", "экспЕрт"],
    "adjectives": ["вернА", "знАчимый", "красИвее", "красИвейший", "кУхонный", "ловкА",
                   "мозаИчный", "оптОвый", "прозорлИвый", "прозорлИва", "слИвовый"],
    "verbs": ["бралА", "бралАсь", "взялА", "взялАсь", "влилАсь", "ворвалАсь", "воспринЯть",
              "воссоздалА", "вручИт", "гналА", "гналАсь", "добралА", "добралАсь", "дождалАсь",
              "дозвонИтся", "дозИровать", "ждалА", "жилОсь", "закУпорить", "занЯть", "зАнял",
              "занялА", "зАняли", "заперлА", "запломбировАть", "защемИт", "звалА", "звонИт",
              "кАшлянуть", "клАла", "клЕить", "крАлась", "кровоточИть", "лгалА", "лилА",
              "лилАсь", "навралА", "наделИт", "надорвалАсь", "назвалАсь", "накренИтся",
              "налилА", "нарвалА", "начАть", "нАчал", "началА", "нАчали", "обзвонИт",
              "облегчИть", "облегчИт", "облилАсь", "обнялАсь", "обогналА", "ободралА",
              "ободрИть", "ободрИт", "ободрИться", "обострИть", "одолжИть", "озлОбить",
              "оклЕить", "окружИт", "опОшлить", "освЕдомиться", "отбылА", "отдалА",
              "откУпорить", "отозвалА", "отозвалАсь", "перезвонИт", "перелилА", "плодоносИть",
              "пломбировАть", "повторИт", "позвалА", "позвонИт", "полилА", "положИть",
              "положИл", "понЯть", "понялА", "послАла", "прибЫть", "прИбыл", "прибылА",
              "прИбыли", "принЯть", "прИнял", "принялА", "прИняли", "рвалА", "сверлИт",
              "снялА", "совралА", "создалА", "сорвалА", "сорИт", "убралА", "углубИть",
              "укрепИт", "чЕрпать", "щемИт", "щЁлкать"],
    "participles": ["довезЁнный", "зАгнутый", "зАнятый", "занятА", "зАпертый", "заселЁнный",
                    "заселенА", "кормЯщий", "кровоточАщий", "нажИвший", "налИвший", "нанЯвшийся",
                    "начАвший", "нАчатый", "низведЁнный", "облегчЁнный", "ободрЁнный",
                    "обострЁнный", "отключЁнный", "повторЁнный", "поделЁнный", "понЯвший",
                    "прИнятый", "принятА", "приручЁнный", "прожИвший", "снятА", "сОгнутый", "углублЁнный"],
    "gerunds": ["закУпорив", "начАв", "начАвшись", "отдАв", "поднЯв", "понЯв", "прибЫв", "создАв"],
    "adverbs": ["вОвремя", "дОверху", "донЕльзя", "дОнизу", "дОсуха", "зАсветло", "зАтемно",
                "красИвее", "надОлго", "ненадОлго"]
}

app = Flask(__name__)
ml = asyncio.new_event_loop()

def sl():
    asyncio.set_event_loop(ml)
    ml.run_forever()

threading.Thread(target=sl, daemon=True).start()

DB_NAME = "ege_stats.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT,
        total_answers INTEGER DEFAULT 0, correct_answers INTEGER DEFAULT 0,
        current_streak INTEGER DEFAULT 0, best_streak INTEGER DEFAULT 0,
        mode TEXT DEFAULT 'all'
    )""")
    conn.commit()
    conn.close()

def get_user(uid):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT total_answers, correct_answers, current_streak, best_streak, mode FROM users WHERE user_id=?", (uid,))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO users (user_id) VALUES (?)", (uid,))
        conn.commit()
        return {'total_answers': 0, 'correct_answers': 0, 'current_streak': 0, 'best_streak': 0, 'mode': 'all'}
    conn.close()
    return {'total_answers': row[0], 'correct_answers': row[1], 'current_streak': row[2], 'best_streak': row[3], 'mode': row[4]}

def update_stats(uid, correct):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    if correct:
        cur.execute("""UPDATE users SET 
            total_answers = total_answers + 1,
            correct_answers = correct_answers + 1,
            current_streak = current_streak + 1,
            best_streak = MAX(best_streak, current_streak + 1)
            WHERE user_id=?""", (uid,))
    else:
        cur.execute("""UPDATE users SET 
            total_answers = total_answers + 1,
            current_streak = 0
            WHERE user_id=?""", (uid,))
    conn.commit()
    conn.close()

def set_mode(uid, mode):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE users SET mode=? WHERE user_id=?", (mode, uid))
    conn.commit()
    conn.close()

user_sessions = {}

def get_words_by_mode(uid):
    user = get_user(uid)
    mode = user.get('mode', 'all')
    if mode == 'all':
        return list(WORDS.keys())
    return WORDS_BY_CATEGORY.get(mode, list(WORDS.keys()))

def generate_ege_question(uid):
    words_pool = get_words_by_mode(uid)
    if len(words_pool) < 5:
        words_pool = list(WORDS.keys())
    
    selected = random.sample(words_pool, 5)
    variants = []
    
    for word in selected:
        correct_stress = WORDS[word].upper()
        if random.random() < 0.5:
            variants.append((correct_stress, True))
        else:
            w = list(word.lower())
            vowels = [j for j, c in enumerate(w) if c in 'аеёиоуыэюя']
            if vowels:
                wrong_vowel = random.choice(vowels)
                w[wrong_vowel] = w[wrong_vowel].upper()
                wrong = ''.join(w)
                if wrong == correct_stress:
                    wrong = word.lower()
                variants.append((wrong, False))
            else:
                variants.append((correct_stress, True))
    
    return selected, variants

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

mk = ReplyKeyboardMarkup([
    [KeyboardButton("🎯 Быстрый тест"), KeyboardButton("📝 Тест ЕГЭ")],
    [KeyboardButton("📊 Статистика"), KeyboardButton("⚙️ Режим")],
    [KeyboardButton("📚 Словарь"), KeyboardButton("❓ Помощь")]
], resize_keyboard=True)

@dp.message(Command("start"))
async def start_cmd(msg: types.Message):
    await msg.answer(
        "📚 <b>ЕГЭ Ударения — Тренажёр</b>\n\n"
        "🎯 Быстрый тест — одно слово, 4 варианта\n"
        "📝 Тест ЕГЭ — 5 слов, выбрать верные\n"
        "📊 Статистика — прогресс\n"
        "⚙️ Режим — выбрать часть речи\n"
        "📚 Словарь — все слова ФИПИ\n\n"
        "Выбери действие 👇",
        parse_mode="HTML", reply_markup=mk
    )

@dp.message(F.text == "⚙️ Режим")
async def mode_menu(msg: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Все слова", callback_data="mode_all")],
        [InlineKeyboardButton(text="📝 Существительные", callback_data="mode_nouns")],
        [InlineKeyboardButton(text="🎨 Прилагательные", callback_data="mode_adjectives")],
        [InlineKeyboardButton(text="⚡ Глаголы", callback_data="mode_verbs")],
        [InlineKeyboardButton(text="📋 Причастия", callback_data="mode_participles")],
        [InlineKeyboardButton(text="🔄 Деепричастия", callback_data="mode_gerunds")],
        [InlineKeyboardButton(text="💬 Наречия", callback_data="mode_adverbs")],
    ])
    await msg.answer("⚙️ Выбери категорию для тренировки:", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("mode_"))
async def set_mode_handler(cb: types.CallbackQuery):
    mode = cb.data.split("_")[1]
    set_mode(cb.from_user.id, mode)
    name = CATEGORIES.get(mode, mode)
    await cb.message.edit_text(f"✅ Режим изменён: <b>{name}</b>", parse_mode="HTML")
    await cb.answer(f"Режим: {name}")

@dp.message(F.text == "🎯 Быстрый тест")
async def quick_test(msg: types.Message):
    words_pool = get_words_by_mode(msg.from_user.id)
    if len(words_pool) < 1:
        words_pool = list(WORDS.keys())
    
    word = random.choice(words_pool)
    correct = WORDS[word].upper()
    
    wrongs = []
    for _ in range(3):
        w = list(word.lower())
        vowels = [i for i, c in enumerate(w) if c in 'аеёиоуыэюя']
        if vowels:
            v = random.choice(vowels)
            w[v] = w[v].upper()
            wrongs.append(''.join(w))
    
    variants = wrongs + [correct]
    random.shuffle(variants)
    
    user_sessions[msg.from_user.id] = {'word': word, 'correct': correct}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=v, callback_data=f"ans_{i}")]
        for i, v in enumerate(variants)
    ])
    await msg.answer(f"🎯 Какое ударение верное?\n\nСлово: <b>{word}</b>", parse_mode="HTML", reply_markup=kb)

@dp.message(F.text == "📝 Тест ЕГЭ")
async def ege_test(msg: types.Message):
    selected, variants = generate_ege_question(msg.from_user.id)
    
    correct_indices = []
    for i, (stress, is_correct) in enumerate(variants):
        if is_correct:
            correct_indices.append(i + 1)
    
    text = "📝 <b>Задание 4 (ЕГЭ)</b>\n\nУкажите варианты ответов, в которых <b>верно</b> выделена буква, обозначающая ударный гласный звук.\n\n"
    for i, (stress, _) in enumerate(variants):
        text += f"{i+1}) {stress}\n"
    
    user_sessions[msg.from_user.id] = {
        'type': 'ege',
        'correct': correct_indices,
        'selected': selected,
        'variants': variants
    }
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1", callback_data="ege_1"),
         InlineKeyboardButton(text="2", callback_data="ege_2"),
         InlineKeyboardButton(text="3", callback_data="ege_3"),
         InlineKeyboardButton(text="4", callback_data="ege_4"),
         InlineKeyboardButton(text="5", callback_data="ege_5")],
        [InlineKeyboardButton(text="✅ Проверить", callback_data="ege_check")],
        [InlineKeyboardButton(text="🔄 Сбросить", callback_data="ege_reset")]
    ])
    
    text += "\nВыбери номера верных ответов 👇"
    await msg.answer(text, parse_mode="HTML", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("ege_") and c.data not in ("ege_check", "ege_reset"))
async def toggle_ege(cb: types.CallbackQuery):
    uid = cb.from_user.id
    session = user_sessions.get(uid)
    if not session or session.get('type') != 'ege':
        await cb.answer("Начните новый тест!"); return
    
    num = int(cb.data.split("_")[1])
    if 'selected_nums' not in session:
        session['selected_nums'] = []
    
    if num in session['selected_nums']:
        session['selected_nums'].remove(num)
    else:
        session['selected_nums'].append(num)
    
    selected = sorted(session['selected_nums'])
    await cb.answer(f"Выбрано: {', '.join(map(str, selected)) if selected else 'ничего'}")

@dp.callback_query(lambda c: c.data == "ege_reset")
async def reset_ege(cb: types.CallbackQuery):
    uid = cb.from_user.id
    session = user_sessions.get(uid)
    if session:
        session['selected_nums'] = []
    await cb.answer("Выбор сброшен")

@dp.callback_query(lambda c: c.data == "ege_check")
async def check_ege(cb: types.CallbackQuery):
    uid = cb.from_user.id
    session = user_sessions.get(uid)
    if not session or session.get('type') != 'ege':
        await cb.answer("Начните новый тест!"); return
    
    correct = set(session.get('correct', []))
    user_answer = set(session.get('selected_nums', []))
    is_correct = user_answer == correct
    update_stats(uid, is_correct)
    
    text = ""
    if is_correct:
        text += "✅ <b>Правильно!</b>\n\n"
    else:
        text += "❌ <b>Неправильно!</b>\n\n"
    
    text += f"Твой ответ: {', '.join(map(str, sorted(user_answer))) if user_answer else 'нет'}\n"
    text += f"Верный ответ: {', '.join(map(str, sorted(correct)))}\n\n"
    text += "Разбор:\n"
    for i, (stress, is_correct_var) in enumerate(session['variants']):
        word = session['selected'][i]
        correct_stress = WORDS[word].upper()
        text += f"{i+1}) {word} — верно: <b>{correct_stress}</b>\n"
    
    await cb.message.edit_text(text, parse_mode="HTML")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("📝 Следующий тест", callback_data="next_ege")],
        [InlineKeyboardButton("📊 Статистика", callback_data="show_stats")]
    ])
    await cb.message.answer("Что дальше?", reply_markup=kb)
    await cb.answer()

@dp.callback_query(lambda c: c.data == "next_ege")
async def next_ege(cb: types.CallbackQuery):
    await ege_test(cb.message)
    await cb.answer()

@dp.callback_query(lambda c: c.data.startswith("ans_"))
async def check_quick(cb: types.CallbackQuery):
    uid = cb.from_user.id
    session = user_sessions.get(uid)
    if not session or 'correct' not in session:
        await cb.answer("Начните новый тест!"); return
    
    variant_idx = int(cb.data.split("_")[1])
    chosen = cb.message.reply_markup.inline_keyboard[variant_idx][0].text
    correct_text = session['correct']
    is_correct = (chosen == correct_text)
    update_stats(uid, is_correct)
    
    if is_correct:
        await cb.message.edit_text(f"✅ Правильно!\n\nСлово: {session['word']}\nУдарение: <b>{correct_text}</b>", parse_mode="HTML")
    else:
        await cb.message.edit_text(f"❌ Неправильно!\n\nСлово: {session['word']}\nВерно: <b>{correct_text}</b>\nТвой ответ: {chosen}", parse_mode="HTML")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🎯 Следующий", callback_data="next_q")],
        [InlineKeyboardButton("📊 Статистика", callback_data="show_stats")]
    ])
    await cb.message.answer("Что дальше?", reply_markup=kb)
    await cb.answer()

@dp.callback_query(lambda c: c.data == "next_q")
async def next_quick(cb: types.CallbackQuery):
    await quick_test(cb.message)
    await cb.answer()

@dp.callback_query(lambda c: c.data == "show_stats")
@dp.message(F.text == "📊 Статистика")
async def show_stats(msg: types.Message):
    if hasattr(msg, 'callback_query'):
        uid = msg.callback_query.from_user.id
        msg = msg.callback_query.message
    else:
        uid = msg.from_user.id
    
    stats = get_user(uid)
    accuracy = (stats['correct_answers'] / stats['total_answers'] * 100) if stats['total_answers'] > 0 else 0
    mode_name = CATEGORIES.get(stats['mode'], stats['mode'])
    
    await msg.answer(
        f"📊 <b>Твоя статистика:</b>\n\n"
        f"Всего ответов: {stats['total_answers']}\n"
        f"Правильных: {stats['correct_answers']}\n"
        f"Точность: {accuracy:.1f}%\n"
        f"Серия: {stats['current_streak']} 🔥\n"
        f"Рекорд: {stats['best_streak']} 👑\n"
        f"Режим: {mode_name}",
        parse_mode="HTML"
    )

@dp.message(F.text == "📚 Словарь")
async def show_dict(msg: types.Message):
    words = list(WORDS.items())[:20]
    text = "📚 <b>Словарь ударений:</b>\n\n" + "\n".join([f"• {w} → <b>{s}</b>" for w, s in words])
    await msg.answer(text, parse_mode="HTML")

@dp.message(F.text == "❓ Помощь")
async def help_cmd(msg: types.Message):
    await msg.answer(
        "📚 <b>ЕГЭ Ударения — Тренажёр</b>\n\n"
        "🎯 Быстрый тест — одно слово, 4 варианта\n"
        "📝 Тест ЕГЭ — 5 слов, выбрать верные\n"
        "⚙️ Режим — выбрать часть речи\n"
        "📊 Статистика — твой прогресс\n"
        "📚 Словарь — все слова ФИПИ\n\n"
        "Тренируйся каждый день!",
        parse_mode="HTML"
    )

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
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
