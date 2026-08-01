import random
from aiogram import types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from words import WORDS
from config import CATEGORIES, WORDS_BY_CATEGORY, OWNER_ID
from database import *

user_sessions = {}
user_modes = {}

mk = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🎯 Быстрый тест"), KeyboardButton(text="📝 Тест ЕГЭ")],
    [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="⚙️ Режим")],
    [KeyboardButton(text="💎 VIP"), KeyboardButton(text="📞 Поддержка")],
    [KeyboardButton(text="👥 Рефералы"), KeyboardButton(text="📄 Вариант ЕГЭ")]
], resize_keyboard=True)

admin_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📊 Статистика бота"), KeyboardButton(text="📩 Тикеты")],
    [KeyboardButton(text="👥 Пользователи"), KeyboardButton(text="💎 Выдать VIP")],
    [KeyboardButton(text="➕ Админ"), KeyboardButton(text="➖ Админ")],
    [KeyboardButton(text="🔙 Выход")]
], resize_keyboard=True)

def get_words_by_mode(uid):
    user = get_user(uid)
    mode = user.get('mode', 'all')
    if mode == 'all': return list(WORDS.keys())
    return WORDS_BY_CATEGORY.get(mode, list(WORDS.keys()))

def generate_ege_question(uid):
    words_pool = get_words_by_mode(uid)
    if len(words_pool) < 5: words_pool = list(WORDS.keys())
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
                variants.append((wrong if wrong != correct_stress else word.lower(), False))
            else:
                variants.append((correct_stress, True))
    return selected, variants

async def start_cmd(msg: types.Message, bot):
    uid = msg.from_user.id
    check_vip(uid)
    args = msg.text.split()
    if len(args) > 1 and args[1].startswith("ref"):
        try:
            rid = int(args[1][3:])
            if rid != uid and activate_referral(uid, rid):
                try: await bot.send_message(rid, "🎉 +1 реферал!")
                except: pass
                await msg.answer("🎁 Вы получили 2 дня VIP за регистрацию по реферальной ссылке!")
        except: pass
    await msg.answer("📚 <b>ЕГЭ Ударения — Тренажёр</b>\n\nВыбери действие 👇", parse_mode="HTML", reply_markup=mk)

async def ref_menu(msg: types.Message, bot):
    u = get_user(msg.from_user.id)
    link = f"https://t.me/{(await bot.me()).username}?start=ref{msg.from_user.id}"
    await msg.answer(f"👥 Ссылка:\n<code>{link}</code>\nПриглашено: {u['referrals_count']}", parse_mode="HTML")

async def vip_menu(msg: types.Message):
    if check_vip(msg.from_user.id):
        await msg.answer(f"💎 VIP до {get_user(msg.from_user.id)['vip_until']}")
        return
    await msg.answer("💎 VIP — 49 ⭐/мес", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Оплатить 49 Stars", pay=True)],
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data="confirm_vip")]
    ]))

async def quick_test(msg: types.Message):
    words_pool = get_words_by_mode(msg.from_user.id) or list(WORDS.keys())
    word = random.choice(words_pool)
    correct = WORDS[word].upper()
    wrongs = []
    for _ in range(3):
        w = list(word.lower())
        vowels = [i for i, c in enumerate(w) if c in 'аеёиоуыэюя']
        if vowels:
            v = random.choice(vowels); w[v] = w[v].upper()
            wrongs.append(''.join(w))
    variants = wrongs + [correct]; random.shuffle(variants)
    user_sessions[msg.from_user.id] = {'word': word, 'correct': correct}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=v, callback_data=f"ans_{i}")] for i, v in enumerate(variants)
    ])
    await msg.answer(f"🎯 Слово: <b>{word}</b>", parse_mode="HTML", reply_markup=kb)

async def ege_test(msg: types.Message):
    selected, variants = generate_ege_question(msg.from_user.id)
    correct_indices = [i+1 for i, (_, is_correct) in enumerate(variants) if is_correct]
    text = "📝 <b>Задание 4 (ЕГЭ)</b>\n\n"
    for i, (stress, _) in enumerate(variants): text += f"{i+1}) {stress}\n"
    user_sessions[msg.from_user.id] = {'type': 'ege', 'correct': correct_indices, 'selected': selected, 'variants': variants}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=str(i), callback_data=f"ege_{i}") for i in range(1, 6)],
        [InlineKeyboardButton(text="✅ Проверить", callback_data="ege_check")],
        [InlineKeyboardButton(text="🔄 Сбросить", callback_data="ege_reset")]
    ])
    await msg.answer(text, parse_mode="HTML", reply_markup=kb)

async def check_quick_cb(cb: types.CallbackQuery):
    session = user_sessions.get(cb.from_user.id)
    if not session: await cb.answer("Начните новый тест!"); return
    idx = int(cb.data.split("_")[1])
    chosen = cb.message.reply_markup.inline_keyboard[idx][0].text
    is_correct = (chosen == session['correct'])
    update_stats(cb.from_user.id, is_correct)
    text = f"{'✅' if is_correct else '❌'} Слово: {session['word']}\nВерно: <b>{session['correct']}</b>"
    await cb.message.edit_text(text, parse_mode="HTML")
    await cb.answer()

async def toggle_ege_cb(cb: types.CallbackQuery):
    session = user_sessions.get(cb.from_user.id)
    if not session: await cb.answer("Начните новый тест!"); return
    num = int(cb.data.split("_")[1])
    session.setdefault('selected_nums', [])
    if num in session['selected_nums']: session['selected_nums'].remove(num)
    else: session['selected_nums'].append(num)
    await cb.answer(f"Выбрано: {', '.join(map(str, sorted(session['selected_nums']))) if session['selected_nums'] else 'ничего'}")

async def check_ege_cb(cb: types.CallbackQuery):
    session = user_sessions.get(cb.from_user.id)
    if not session: await cb.answer("Начните новый тест!"); return
    correct = set(session.get('correct', []))
    user_answer = set(session.get('selected_nums', []))
    update_stats(cb.from_user.id, user_answer == correct)
    text = f"{'✅' if user_answer == correct else '❌'} Ответ: {', '.join(map(str, sorted(correct)))}\n"
    for i, (_, _) in enumerate(session['variants']):
        text += f"{i+1}) {session['selected'][i]} — <b>{WORDS[session['selected'][i]]}</b>\n"
    await cb.message.edit_text(text, parse_mode="HTML")
    await cb.answer()

async def show_stats_handler(msg):
    uid = msg.from_user.id if hasattr(msg, 'from_user') else msg.callback_query.from_user.id
    s = get_user(uid)
    accuracy = (s['correct_answers'] / s['total_answers'] * 100) if s['total_answers'] > 0 else 0
    await msg.answer(f"📊 Всего: {s['total_answers']}\nПравильно: {s['correct_answers']}\nТочность: {accuracy:.1f}%\nVIP: {'💎' if s['status']=='vip' else '🆓'}", parse_mode="HTML")
