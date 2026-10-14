"""
Red Cube DEMO bot — с долгом, отработкой и «исправительными работами».
Без оскорблений. Всё нейтрально.
"""

import asyncio
import json
import os
import random
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "8564091056:AAFLHzPDJEHWoBTpg8oOPw7CH1Uwv6cMqKE"
ADMIN_SECRET = "nvrjf9ur3rnfemdd9enf8y3fen8u3rb8u3nvu3rf83"
DB_FILE = "rc_users.json"
PROMOS_FILE = "rc_promos.json"
RESERVE_FILE = "rc_reserve.json"

MIN_BET = 0.1
START_BALANCE = 0.5
RAKE_PERCENT = 0.03
RAKE_UNLOCK_THRESHOLD = 0.3
RAKE_CLAIM_MIN = 0.1
RAKE_MAX = 1000.0

DEBT_WORK_REWARD = 10.0       # сколько отбивается за 2 угадывания подряд
WORK_WORD = "админ лучший"    # что должен писать игрок в наказании

VPN_PROXY = None

# ==================== ТЕКСТЫ ====================
TEXT_START = (
    "👋 Привет, <b>{name}</b>!\n\n"
    "Это <b>демо-бот</b> в стиле Red Cube.\n"
    "Реальных денег нет — баланс виртуальный.\n\n"
    "💵 Баланс: <b>{balance:.2f}$</b>\n"
    "💎 Рейк: <b>{rake:.2f}$</b>\n\n"
    "<i>Напиши</i> <b>команды</b> <i>— увидишь список.</i>"
)

TEXT_HELP = (
    "📋 <b>Команды бота</b>\n\n"
    "<b>Основные:</b>\n"
    "• <b>меню</b> — главное меню\n"
    "• <b>играть</b> — меню игр\n"
    "• <b>вб</b> — поставить весь баланс\n"
    "• <b>профиль</b> — твой профиль\n"
    "• <b>баланс</b> — текущий баланс\n"
    "• <b>рейк</b> — подарочный баланс\n"
    "• <b>забрать рейк</b> — вывести рейк\n"
    "• <b>резерв</b> — общий резерв\n"
    "• <b>промо</b> — ввести промокод\n"
    "• <b>топ</b> — топ игроков\n"
    "• <b>команды</b> — этот список\n\n"
    "<b>Переводы:</b>\n"
    "• <b>нк @юзер 0.5</b> — перевести баланс\n\n"
    "<b>Игры:</b> используй кнопки в меню 👇"
)

TEXT_GAMES = "🎮 <b>Выберите игру, на которую хотите сделать ставку!</b>"
TEXT_WORK = "🛠 <b>Режим отработки</b>\n\nТы в долгу. Угадай 2 раза подряд — отобьёшь 10$."

TEXT_PROMO_ENTER = (
    "🎁 <b>Введи промокод</b>\n\n"
    "Отправь название в чат.\n"
    "<i>Для отмены — напиши</i> <b>отмена</b>"
)

logging.basicConfig(level=logging.INFO)
router = Router()


# ==================== ОПИСАНИЕ ИСХОДА ====================
def describe_result(game_key: str, value: int) -> str:
    if game_key == "dice":
        return {
            1: "1️⃣ Единица", 2: "2️⃣ Двойка", 3: "3️⃣ Тройка",
            4: "4️⃣ Четвёрка", 5: "5️⃣ Пятёрка", 6: "6️⃣ Шестёрка",
        }.get(value, str(value))
    if game_key == "football":
        return {
            1: "🚫 Промах", 2: "🥅 Удар об штангу",
            3: "⚽ Гол в центр", 4: "⚽ Гол от штанги", 5: "⚽ Гол в угол",
        }.get(value, str(value))
    if game_key == "basketball":
        return {
            1: "🚫 Промах", 2: "🏀 Отскок", 3: "🏀 Застрял мяч",
            4: "🏀 Прокрут", 5: "🏀 Чистый гол",
        }.get(value, str(value))
    if game_key == "darts":
        return {
            1: "🚫 Промах", 2: "🎯 Красный сектор",
            3: "🎯 Белый сектор", 4: "🎯 Белый сектор",
            5: "🎯 Отскок", 6: "🎯 В яблочко (центр)",
        }.get(value, str(value))
    if game_key == "bowling":
        return {
            1: "🚫 Промах", 2: "🎳 Сбита 1 кегля",
            3: "🎳 Сбито 3 кегли", 4: "🎳 Сбито 4 кегли",
            5: "🎳 Сбито 5 кеглей", 6: "🎳 Страйк!",
        }.get(value, str(value))
    if game_key == "slots":
        def decode_slot(v):
            v -= 1
            return ((v >> 4) & 0x03, (v >> 2) & 0x03, v & 0x03)
        SYMBOLS = ["BAR", "🍇", "🍋", "7️⃣"]
        parts = decode_slot(value)
        names = [SYMBOLS[p] for p in parts]
        if parts[0] == parts[1] == parts[2]:
            return f"🎰 {names[0]}-{names[1]}-{names[2]} (все одинаковые)"
        if parts[0] != parts[1] and parts[1] != parts[2] and parts[0] != parts[2]:
            return f"🎰 {names[0]}-{names[1]}-{names[2]} (все разные)"
        return f"🎰 {names[0]}-{names[1]}-{names[2]}"
    return f"Значение: {value}"


# ==================== БАЗА ====================
def load(file: str, default=None) -> dict:
    if not os.path.exists(file):
        return default if default is not None else {}
    with open(file, 'r', encoding='utf-8') as f:
        return json.load(f)

def save(file: str, data: dict):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(uid: int, name: str = "") -> dict:
    db = load(DB_FILE)
    key = str(uid)
    if key not in db:
        db[key] = {
            "name": name,
            "balance": START_BALANCE,
            "rake_balance": 0.0,
            "turnover": 0.0,
            "wins": 0,
            "games": 0,
            "rake_earned": 0.0,
            "reserve_claimed": 0.0,
            "is_admin": False,
            "bet": MIN_BET,
            "work_streak": 0,        # сколько раз подряд угадал в отработке
            "work_last_value": 0,    # прошлое значение кубика
            "punish_remaining": 0,   # сколько раз осталось написать WORK_WORD
            "registered": datetime.now().isoformat(),
        }
        save(DB_FILE, db)
    else:
        # дописываем недостающие поля
        defaults = {"bet": MIN_BET, "work_streak": 0, "work_last_value": 0, "punish_remaining": 0}
        changed = False
        for k, v in defaults.items():
            if k not in db[key]:
                db[key][k] = v
                changed = True
        if changed:
            save(DB_FILE, db)
    return db[key]

def update_user(uid: int, **kwargs):
    db = load(DB_FILE)
    key = str(uid)
    if key not in db:
        db[key] = {"balance": START_BALANCE, "rake_balance": 0.0, "turnover": 0.0,
                   "wins": 0, "games": 0, "rake_earned": 0.0, "reserve_claimed": 0.0,
                   "is_admin": False, "bet": MIN_BET, "work_streak": 0,
                   "work_last_value": 0, "punish_remaining": 0}
    db[key].update(kwargs)
    save(DB_FILE, db)

def find_user_by_username(username: str):
    db = load(DB_FILE)
    uname = username.lstrip('@').lower()
    for uid, data in db.items():
        if data.get("name", "").lstrip('@').lower() == uname:
            return int(uid), data
    return None, None

def is_admin(msg_or_call) -> bool:
    db = load(DB_FILE)
    key = str(msg_or_call.from_user.id)
    return db.get(key, {}).get("is_admin", False)

def get_reserve() -> float:
    return float(load(RESERVE_FILE, {"amount": 1000.0}).get("amount", 1000.0))

def set_reserve(v: float):
    save(RESERVE_FILE, {"amount": max(0.0, float(v))})

def add_reserve(v: float):
    set_reserve(get_reserve() + v)


# ==================== СОСТОЯНИЯ ====================
class States(StatesGroup):
    enter_bet = State()
    enter_new_bet = State()
    enter_promo = State()
    enter_admin_code = State()
    admin_promo_name = State()
    admin_promo_amount = State()
    admin_promo_limit = State()
    admin_give_user = State()
    admin_give_amount = State()
    admin_take_user = State()
    admin_take_amount = State()
    admin_reserve_amount = State()
    admin_broadcast = State()
    admin_punish_user = State()
    admin_punish_count = State()
    work_guess = State()


# ==================== ИГРЫ ====================
GAMES = {
    "dice": {
        "emoji": "🎲", "name": "Кубик",
        "outcomes_1": [
            ("Чёт (x2)", "even", 2.0), ("Нечет (x2)", "odd", 2.0),
            ("Меньше (x2)", "lt", 2.0), ("Больше (x2)", "gt", 2.0),
            ("1 (x6)", "eq1", 6.0), ("2 (x6)", "eq2", 6.0), ("3 (x6)", "eq3", 6.0),
            ("4 (x6)", "eq4", 6.0), ("5 (x6)", "eq5", 6.0), ("6 (x6)", "eq6", 6.0),
            ("Лесенка (x2.2)", "ladder", 2.2),
        ],
    },
    "football": {
        "emoji": "⚽", "name": "Футбол",
        "outcomes_1": [
            ("Гол в центр (x5)", "center", 5.0),
            ("Гол в угол (x5)", "corner", 5.0),
            ("Гол от штанги (x5)", "post", 5.0),
            ("Любой гол (x1.66)", "any", 1.66),
            ("Удар об штангу (x2.5)", "hit", 2.5),
            ("Промах (x2.5)", "miss", 2.5),
        ],
    },
    "basketball": {
        "emoji": "🏀", "name": "Баскетбол",
        "outcomes_1": [
            ("Чистый гол (x5)", "clean", 5.0),
            ("Прокрут (x2.5)", "spin", 2.5),
            ("Застрял мяч (x5)", "stuck", 5.0),
            ("Любой гол (x2.5)", "any", 2.5),
            ("Отскок (x5)", "bounce", 5.0),
            ("Промах (x1.66)", "miss", 1.66),
        ],
    },
    "darts": {
        "emoji": "🎯", "name": "Дартс",
        "outcomes_1": [
            ("Центр (x6)", "center", 6.0),
            ("Отскок (x6)", "bounce", 6.0),
            ("Красный сектор (x3)", "red", 3.0),
            ("Белый сектор (x3)", "white", 3.0),
            ("Любой сектор (x1.5)", "any", 1.5),
        ],
    },
    "bowling": {
        "emoji": "🎳", "name": "Боулинг",
        "outcomes_1": [
            ("Страйк (x6)", "strike", 6.0),
            ("Промах (x6)", "miss", 6.0),
            ("Сбита 1/6 (x6)", "one", 6.0),
            ("Сбито 3/6 (x6)", "three", 6.0),
            ("Сбито 4/6 (x6)", "four", 6.0),
            ("Сбито 5/6 (x6)", "five", 6.0),
            ("Без страйка (x1.44)", "ns", 1.44),
            ("Без промаха (x1.44)", "nm", 1.44),
        ],
    },
    "slots": {
        "emoji": "🎰", "name": "Слоты",
        "outcomes_1": [
            ("3 Семёрки (x64)", "s777", 64.0),
            ("3 Лимона (x64)", "slll", 64.0),
            ("3 Винограда (x64)", "sggg", 64.0),
            ("3 Бара (x64)", "sbbb", 64.0),
            ("Любая комбинация (x16)", "any3", 16.0),
            ("Уникальные символы (x2.66)", "uniq", 2.66),
        ],
    },
}


# ==================== КЛАВИАТУРЫ ====================
def menu_main(user: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="👛 Кошелёк", callback_data="wallet")
    if user["balance"] < 0:
        kb.button(text="🛠 Отработать", callback_data="work")
    else:
        kb.button(text="🎮 Игры", callback_data="games")
    kb.button(text="≡ Меню", callback_data="moremenu")
    kb.adjust(3)
    return kb.as_markup()

def menu_games() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, g in GAMES.items():
        kb.button(text=f"{g['emoji']} {g['name']}", callback_data=f"g_{key}")
    kb.button(text="✏️ Изменить ставку", callback_data="change_bet")
    kb.adjust(3, 3, 1)
    return kb.as_markup()

def menu_outcomes(game_key: str) -> InlineKeyboardMarkup:
    g = GAMES[game_key]
    kb = InlineKeyboardBuilder()
    for label, code, mult in g["outcomes_1"]:
        kb.button(text=label, callback_data=f"o_{game_key}_{code}")
    kb.button(text="✏️ Изменить ставку", callback_data="change_bet")
    kb.button(text="⬅️ Назад", callback_data="games")
    kb.adjust(2, 2, 2, 2, 2, 2, 1, 1)
    return kb.as_markup()

def menu_more() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Профиль",  callback_data="profile")
    kb.button(text="💎 Рейк",     callback_data="rake")
    kb.button(text="🏦 Резерв",   callback_data="reserve")
    kb.button(text="🎁 Промокод", callback_data="promo")
    kb.button(text="🏆 Топ",      callback_data="top")
    kb.button(text="⬅️ Назад",    callback_data="main")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()

def menu_admin() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎁 Создать промо",   callback_data="adm_promo_new")
    kb.button(text="📋 Список промо",    callback_data="adm_promo_list")
    kb.button(text="💵 Выдать баланс",   callback_data="adm_give")
    kb.button(text="💸 Забрать баланс",  callback_data="adm_take")
    kb.button(text="🏦 Резерв",          callback_data="adm_reserve")
    kb.button(text="📢 Рассылка",         callback_data="adm_broadcast")
    kb.button(text="⚖️ Наказать",        callback_data="adm_punish")
    kb.button(text="❌ Закрыть",         callback_data="adm_close")
    kb.adjust(1, 1, 2, 1, 1, 1, 1)
    return kb.as_markup()

def menu_admin_reserve() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить в резерв", callback_data="adm_res_add")
    kb.button(text="➖ Убрать из резерва", callback_data="adm_res_take")
    kb.button(text="⬅️ Назад",            callback_data="adm_back")
    kb.adjust(1)
    return kb.as_markup()

def back(target="main") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data=target)
    return kb.as_markup()


# ==================== START ====================
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    u = get_user(message.from_user.id, message.from_user.username or message.from_user.first_name)
    await message.answer(
        TEXT_START.format(name=message.from_user.first_name,
                          balance=u["balance"], rake=u["rake_balance"]),
        parse_mode="HTML",
        reply_markup=menu_main(u),
    )


# ==================== ТЕКСТОВЫЕ КОМАНДЫ ====================
@router.message(F.text.lower() == "команды")
async def cmd_help(message: Message):
    await message.answer(TEXT_HELP, parse_mode="HTML")

@router.message(F.text.lower() == "меню")
async def cmd_menu_text(message: Message, state: FSMContext):
    await state.clear()
    u = get_user(message.from_user.id)
    await message.answer(
        f"🎰 <b>Главное меню</b>\n\n💵 Баланс: <b>{u['balance']:.2f}$</b>",
        parse_mode="HTML", reply_markup=menu_main(u),
    )

@router.message(F.text.lower() == "играть")
async def cmd_play_text(message: Message, state: FSMContext):
    await state.clear()
    u = get_user(message.from_user.id)
    if u["balance"] < 0:
        await message.answer(TEXT_WORK, parse_mode="HTML",
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                 [InlineKeyboardButton(text="🛠 Отработать", callback_data="work")]
                             ]))
        return
    await message.answer(TEXT_GAMES, parse_mode="HTML", reply_markup=menu_games())

@router.message(F.text.lower() == "вб")
async def cmd_all_in(message: Message, state: FSMContext):
    await state.clear()
    u = get_user(message.from_user.id)
    if u["balance"] < 0:
        await message.answer("❌ Ты в долгу. Сначала отработай.", reply_markup=back("main"))
        return
    if u["balance"] < MIN_BET:
        await message.answer(f"❌ Баланс слишком маленький: <b>{u['balance']:.2f}$</b>", parse_mode="HTML")
        return
    update_user(message.from_user.id, bet=u["balance"])
    await message.answer(f"✅ Ставка на весь баланс: <b>{u['balance']:.2f}$</b>",
                         parse_mode="HTML", reply_markup=menu_games())

@router.message(F.text.lower() == "профиль")
async def cmd_profile_text(message: Message):
    u = get_user(message.from_user.id)
    debt = ""
    if u["balance"] < 0:
        debt = f"\n⚠️ <b>Ты в долгу: {abs(u['balance']):.2f}$</b>"
    punish = ""
    if u.get("punish_remaining", 0) > 0:
        punish = f"\n⚖️ Исправительных работ осталось: <b>{u['punish_remaining']}</b>"
    await message.answer(
        f"👤 <b>Профиль</b>\n\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"📛 Ник: @{message.from_user.username or '—'}\n\n"
        f"💵 Баланс: <b>{u['balance']:.2f}$</b>{debt}\n"
        f"📊 Оборот: <b>{u['turnover']:.2f}$</b>\n"
        f"💎 Рейк: <b>{u['rake_balance']:.2f}$</b>\n"
        f"💵 Ставка: <b>{u['bet']:.2f}$</b>\n"
        f"🎮 Игр: <b>{u['games']}</b>\n"
        f"🏆 Побед: <b>{u['wins']}</b>{punish}\n"
        f"📅 С нами с: {u['registered'][:10]}",
        parse_mode="HTML", reply_markup=back("main"),
    )

@router.message(F.text.lower() == "баланс")
async def cmd_balance_text(message: Message):
    u = get_user(message.from_user.id)
    debt = ""
    if u["balance"] < 0:
        debt = f"\n⚠️ Долг: <b>{abs(u['balance']):.2f}$</b> — отработай кубиком."
    await message.answer(
        f"💵 Баланс: <b>{u['balance']:.2f}$</b>\n"
        f"💎 Рейк: <b>{u['rake_balance']:.2f}$</b>{debt}",
        parse_mode="HTML", reply_markup=back("main"),
    )

@router.message(F.text.lower() == "рейк")
async def cmd_rake_text(message: Message):
    u = get_user(message.from_user.id)
    can = u["turnover"] >= RAKE_UNLOCK_THRESHOLD and u["rake_balance"] >= RAKE_CLAIM_MIN
    kb = InlineKeyboardBuilder()
    if can:
        kb.button(text=f"💸 Забрать {u['rake_balance']:.2f}$", callback_data="rake_claim")
    else:
        kb.button(text="🔒 Недоступно", callback_data="noop")
    kb.button(text="⬅️ Назад", callback_data="moremenu")
    kb.adjust(1)
    await message.answer(
        f"💎 <b>Рейк</b>\n\n"
        f"📊 Оборот: <b>{u['turnover']:.2f}$</b>\n"
        f"💎 Доступно: <b>{u['rake_balance']:.2f}$</b>\n"
        f"📈 Максимум: <b>{RAKE_MAX:.0f}$</b>\n\n"
        f"<i>Условия:</i>\n"
        f"• Отыграно минимум <b>{RAKE_UNLOCK_THRESHOLD}$</b>\n"
        f"• Мин. вывод — <b>{RAKE_CLAIM_MIN}$</b>",
        parse_mode="HTML", reply_markup=kb.as_markup(),
    )

@router.message(F.text.lower() == "забрать рейк")
async def cmd_rake_claim_text(message: Message):
    u = get_user(message.from_user.id)
    if u["turnover"] < RAKE_UNLOCK_THRESHOLD:
        await message.answer(
            f"❌ Сначала отыграй <b>{RAKE_UNLOCK_THRESHOLD}$</b>\n"
            f"📊 Твой оборот: <b>{u['turnover']:.2f}$</b>",
            parse_mode="HTML", reply_markup=back("moremenu"),
        )
        return
    if u["rake_balance"] < RAKE_CLAIM_MIN:
        await message.answer(
            f"❌ Минимум для вывода — <b>{RAKE_CLAIM_MIN}$</b>\n"
            f"💎 Накоплено: <b>{u['rake_balance']:.2f}$</b>",
            parse_mode="HTML", reply_markup=back("moremenu"),
        )
        return
    amount = u["rake_balance"]
    update_user(message.from_user.id,
                balance=u["balance"] + amount, rake_balance=0.0)
    await message.answer(
        f"✅ <b>Рейк забран</b>\n\n"
        f"💰 Получено: <b>+{amount:.2f}$</b>\n"
        f"💵 Баланс: <b>{u['balance'] + amount:.2f}$</b>",
        parse_mode="HTML", reply_markup=back("moremenu"),
    )

@router.message(F.text.lower() == "резерв")
async def cmd_reserve_text(message: Message):
    u = get_user(message.from_user.id)
    can = u["turnover"] >= RAKE_UNLOCK_THRESHOLD
    kb = InlineKeyboardBuilder()
    if can:
        kb.button(text="🏦 Забрать из резерва", callback_data="reserve_claim")
    else:
        kb.button(text="🔒 Недоступно", callback_data="noop")
    kb.button(text="⬅️ Назад", callback_data="moremenu")
    kb.adjust(1)
    await message.answer(
        f"🏦 <b>Резерв</b>\n\nВ резерве бота: <b>{get_reserve():.2f}$</b>",
        parse_mode="HTML", reply_markup=kb.as_markup(),
    )

@router.message(F.text.lower() == "промо")
async def cmd_promo_text(message: Message, state: FSMContext):
    await state.set_state(States.enter_promo)
    await message.answer(TEXT_PROMO_ENTER, parse_mode="HTML")

@router.message(F.text.lower() == "топ")
async def cmd_top_text(message: Message):
    await send_top(message)

@router.message(F.text.lower() == "отмена")
async def cmd_cancel_text(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=menu_main(get_user(message.from_user.id)))


# ==================== ИСПРАВИТЕЛЬНЫЕ РАБОТЫ ====================
@router.message(F.text.lower() == WORK_WORD)
async def work_word_message(message: Message):
    u = get_user(message.from_user.id)
    remaining = u.get("punish_remaining", 0)
    if remaining <= 0:
        await message.answer("✅ У тебя нет исправительных работ.")
        return
    remaining -= 1
    update_user(message.from_user.id, punish_remaining=remaining)
    if remaining <= 0:
        await message.answer(
            f"✅ <b>Исправительные работы выполнены!</b>\n\n"
            f"Ты свободен. Работ осталось: 0",
            parse_mode="HTML", reply_markup=back("main"),
        )
    else:
        total = u.get("punish_total", remaining + 1)
        done = total - remaining
        await message.answer(
            f"📝 <b>Работы</b>: {done} из {total}\n"
            f"Осталось написать: <b>{remaining}</b> раз"
        )

@router.message(F.text.lower() == "отработка")
async def work_status(message: Message):
    u = get_user(message.from_user.id)
    remaining = u.get("punish_remaining", 0)
    if remaining <= 0:
        await message.answer("✅ У тебя нет исправительных работ.")
        return
    total = u.get("punish_total", remaining)
    done = total - remaining
    await message.answer(
        f"⚖️ <b>Исправительные работы</b>\n\n"
        f"Прогресс: <b>{done} из {total}</b>\n"
        f"Осталось написать: <b>{remaining}</b> раз\n\n"
        f"Напиши: <b>{WORK_WORD}</b>"
    )


# ==================== РЕЖИМ «ОТРАБОТАТЬ» ====================
@router.callback_query(F.data == "work")
async def cb_work(call: CallbackQuery, state: FSMContext):
    u = get_user(call.from_user.id)
    if u["balance"] >= 0:
        await call.answer("✅ У тебя нет долга.")
        return
    await state.set_state(States.work_guess)
    await call.answer()
    await call.message.edit_text(
        f"🛠 <b>Отработка долга</b>\n\n"
        f"⚠️ Долг: <b>{abs(u['balance']):.2f}$</b>\n"
        f"💰 За 2 угадывания подряд: <b>+{DEBT_WORK_REWARD:.0f}$</b>\n\n"
        f"🎲 Угадай число от 1 до 6 (напиши цифру):",
        parse_mode="HTML",
    )

@router.message(States.work_guess)
async def process_work_guess(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text.lower() == "отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=menu_main(get_user(message.from_user.id)))
        return
    if not text.isdigit() or int(text) < 1 or int(text) > 6:
        await message.answer("❌ Введи число от 1 до 6.")
        return

    guess = int(text)
    u = get_user(message.from_user.id)

    # Бросаем кубик
    msg = await message.answer_dice(emoji="🎲")
    await asyncio.sleep(4)
    value = msg.dice.value

    if value == guess:
        # угадал
        streak = u.get("work_streak", 0) + 1
        update_user(message.from_user.id, work_streak=streak, work_last_value=value)

        if streak >= 2:
            new_balance = u["balance"] + DEBT_WORK_REWARD
            update_user(message.from_user.id, balance=new_balance, work_streak=0)
            if new_balance >= 0:
                await message.answer(
                    f"🎲 Выпало: <b>{describe_result('dice', value)}</b>\n"
                    f"✅ Угадал 2 раза подряд!\n\n"
                    f"💰 <b>+{DEBT_WORK_REWARD:.0f}$</b>\n"
                    f"💵 Баланс: <b>{new_balance:.2f}$</b>\n\n"
                    f"🎉 Долг закрыт! Снова доступны игры.",
                    parse_mode="HTML", reply_markup=menu_games(),
                )
                await state.clear()
            else:
                await message.answer(
                    f"🎲 Выпало: <b>{describe_result('dice', value)}</b>\n"
                    f"✅ Угадал 2 раза подряд!\n\n"
                    f"💰 <b>+{DEBT_WORK_REWARD:.0f}$</b>\n"
                    f"💵 Баланс: <b>{new_balance:.2f}$</b>\n"
                    f"⚠️ Всё ещё в долгу. Отрабатывай дальше.",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🛠 Отработать", callback_data="work")]
                    ]),
                )
        else:
            await message.answer(
                f"🎲 Выпало: <b>{describe_result('dice', value)}</b>\n"
                f"✅ Угадал! (1/2)\n\n"
                f"Угадай ещё раз, чтобы получить +{DEBT_WORK_REWARD:.0f}$",
                parse_mode="HTML",
            )
    else:
        # не угадал
        update_user(message.from_user.id, work_streak=0, work_last_value=value)
        await message.answer(
            f"🎲 Выпало: <b>{describe_result('dice', value)}</b>\n"
            f"❌ Не угадал. Попробуй снова.",
            parse_mode="HTML",
        )


# ==================== АДМИНКА ====================
@router.message(F.text.lower() == "админка")
async def cmd_admin_request(message: Message, state: FSMContext):
    if is_admin(message):
        await message.answer(
            f"👑 <b>Админ-панель</b>\n\n🏦 Резерв: <b>{get_reserve():.2f}$</b>",
            parse_mode="HTML", reply_markup=menu_admin(),
        )
        return
    await state.set_state(States.enter_admin_code)
    await message.answer("🔐 <b>Введи секретный код</b>\n\n<i>Для отмены — напиши</i> <b>отмена</b>",
                         parse_mode="HTML")

@router.message(States.enter_admin_code)
async def process_admin_code(message: Message, state: FSMContext):
    code = (message.text or "").strip()
    if code.lower() == "отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=menu_main(get_user(message.from_user.id)))
        return
    if code == ADMIN_SECRET:
        update_user(message.from_user.id, is_admin=True)
        await state.clear()
        await message.answer("✅ <b>Теперь ты админ!</b>\n\n👑 Админка: <b>админка</b>",
                             parse_mode="HTML")
    else:
        await message.answer("❌ Неверный код.")


# ==================== НК ====================
@router.message(F.text.lower().startswith("нк "))
async def cmd_nk(message: Message):
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("❌ Формат: <code>нк @юзер 0.5</code>", parse_mode="HTML"); return
    target_uname = parts[1].lstrip('@')
    try:
        amount = float(parts[2].replace(",", "."))
    except ValueError:
        await message.answer("❌ Сумма должна быть числом."); return
    if amount <= 0:
        await message.answer("❌ Сумма должна быть больше нуля."); return
    target_id, target_data = find_user_by_username(target_uname)
    if target_id is None:
        await message.answer(f"❌ Игрок @{target_uname} не найден."); return
    if target_id == message.from_user.id:
        await message.answer("❌ Нельзя переводить самому себе."); return
    sender = get_user(message.from_user.id)
    if sender["balance"] < amount:
        await message.answer(f"❌ Недостаточно. Баланс: <b>{sender['balance']:.2f}$</b>",
                             parse_mode="HTML"); return
    update_user(message.from_user.id, balance=sender["balance"] - amount)
    update_user(target_id, balance=target_data["balance"] + amount)
    await message.answer(f"✅ Переведено @{target_uname}: <b>{amount:.2f}$</b>", parse_mode="HTML")
    try:
        await message.bot.send_message(target_id,
            f"💰 <b>Входящий перевод</b>\n\nОт: @{message.from_user.username or message.from_user.id}\nСумма: <b>+{amount:.2f}$</b>",
            parse_mode="HTML")
    except Exception:
        pass


# ==================== CALLBACK МЕНЮ ====================
@router.callback_query(F.data == "main")
async def cb_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    u = get_user(call.from_user.id)
    await call.message.edit_text(
        f"🎰 <b>Главное меню</b>\n\n💵 Баланс: <b>{u['balance']:.2f}$</b>",
        parse_mode="HTML", reply_markup=menu_main(u),
    )
    await call.answer()

@router.callback_query(F.data == "wallet")
async def cb_wallet(call: CallbackQuery):
    u = get_user(call.from_user.id)
    debt = ""
    if u["balance"] < 0:
        debt = f"\n⚠️ Долг: <b>{abs(u['balance']):.2f}$</b> — отработай кубиком."
    await call.message.edit_text(
        f"👛 <b>Кошелёк</b>\n\n"
        f"💵 Игровой: <b>{u['balance']:.2f}$</b>{debt}\n"
        f"💎 Рейк: <b>{u['rake_balance']:.2f}$</b>\n"
        f"📊 Оборот: <b>{u['turnover']:.2f}$</b>",
        parse_mode="HTML", reply_markup=back(),
    )
    await call.answer()

@router.callback_query(F.data == "games")
async def cb_games(call: CallbackQuery):
    u = get_user(call.from_user.id)
    if u["balance"] < 0:
        await call.answer("❌ Ты в долгу. Отработай сначала.", show_alert=True); return
    await call.message.edit_text(TEXT_GAMES, parse_mode="HTML", reply_markup=menu_games())
    await call.answer()

@router.callback_query(F.data == "moremenu")
async def cb_moremenu(call: CallbackQuery):
    await call.message.edit_text("≡ <b>Меню</b>", parse_mode="HTML", reply_markup=menu_more())
    await call.answer()


# ==================== ИГРЫ ====================
@router.callback_query(F.data.startswith("g_"))
async def cb_game(call: CallbackQuery, state: FSMContext):
    await state.clear()
    u = get_user(call.from_user.id)
    if u["balance"] < 0:
        await call.answer("❌ Ты в долгу. Отработай сначала.", show_alert=True); return
    key = call.data.split("_", 1)[1]
    if key not in GAMES:
        await call.answer("Игра не найдена", show_alert=True); return
    g = GAMES[key]
    await call.message.edit_text(
        f"{g['emoji']} <b>{g['name']}</b>\n💵 Ставка: <b>{u['bet']:.2f}$</b>\n\n🎯 <b>Выберите исход игры!</b>",
        parse_mode="HTML", reply_markup=menu_outcomes(key),
    )
    await call.answer()

@router.callback_query(F.data.startswith("o_"))
async def cb_outcome(call: CallbackQuery, state: FSMContext):
    parts = call.data.split("_", 2)
    if len(parts) != 3:
        await call.answer("Ошибка", show_alert=True); return
    _, game_key, code = parts
    if game_key not in GAMES:
        await call.answer("Игра не найдена", show_alert=True); return
    g = GAMES[game_key]
    outcome = next((o for o in g["outcomes_1"] if o[1] == code), None)
    if not outcome:
        await call.answer("Неизвестный исход", show_alert=True); return

    label, _, mult = outcome
    u = get_user(call.from_user.id)

    if u["balance"] < 0:
        await call.answer("❌ Ты в долгу.", show_alert=True); return
    bet = u["bet"]
    if u["balance"] < bet:
        await call.answer(f"❌ Недостаточно. Баланс: {u['balance']:.2f}$, ставка: {bet:.2f}$",
                          show_alert=True); return

    await call.answer(f"Ставка {bet:.2f}$")
    await call.message.edit_text(
        f"{g['emoji']} <b>{g['name']}</b>\n🎯 Исход: <b>{label}</b>\n💵 Ставка: <b>{bet:.2f}$</b>\n\n<i>Бросаем...</i>",
        parse_mode="HTML",
    )

    update_user(call.from_user.id,
                balance=u["balance"] - bet,
                turnover=u["turnover"] + bet,
                games=u["games"] + 1)

    msg = await call.message.answer_dice(emoji=g["emoji"])
    await asyncio.sleep(4)
    value = msg.dice.value
    win = check_win(game_key, code, value)
    rake_add = bet * RAKE_PERCENT
    description = describe_result(game_key, value)

    u = get_user(call.from_user.id)
    new_rake = min(u["rake_balance"] + rake_add, RAKE_MAX)

    if win:
        profit = bet * mult
        update_user(call.from_user.id,
                    balance=u["balance"] + profit,
                    wins=u["wins"] + 1,
                    rake_balance=new_rake,
                    rake_earned=u["rake_earned"] + rake_add)
        add_reserve(-profit)
        new_u = get_user(call.from_user.id)
        await call.message.answer(
            f"🎉 <b>ВЫИГРЫШ!</b>\n\n"
            f"{g['emoji']} {g['name']}\n"
            f"🎲 Выпало: <b>{description}</b>\n"
            f"🎯 Исход: x{mult}\n"
            f"💵 Ставка: <b>{bet:.2f}$</b>\n\n"
            f"💰 Получено: <b>+{profit:.2f}$</b>\n"
            f"💵 Баланс: <b>{new_u['balance']:.2f}$</b>",
            parse_mode="HTML",
        )
    else:
        update_user(call.from_user.id,
                    rake_balance=new_rake,
                    rake_earned=u["rake_earned"] + rake_add)
        add_reserve(bet)
        new_u = get_user(call.from_user.id)
        await call.message.answer(
            f"💀 <b>ПРОИГРЫШ</b>\n\n"
            f"{g['emoji']} {g['name']}\n"
            f"🎲 Выпало: <b>{description}</b>\n"
            f"🎯 Исход: x{mult}\n"
            f"💵 Ставка: <b>{bet:.2f}$</b>\n\n"
            f"📉 Потеряно: <b>-{bet:.2f}$</b>\n"
            f"💵 Баланс: <b>{new_u['balance']:.2f}$</b>",
            parse_mode="HTML",
        )

    # Кнопки: если в долгу — «Отработать», иначе меню игр
    new_u = get_user(call.from_user.id)
    if new_u["balance"] < 0:
        await call.message.answer(
            "⚠️ Ты ушёл в минус. Теперь нужно отработать.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛠 Отработать", callback_data="work")]
            ]),
        )
    else:
        await call.message.answer(TEXT_GAMES, parse_mode="HTML", reply_markup=menu_games())


@router.callback_query(F.data == "change_bet")
async def cb_change_bet(call: CallbackQuery, state: FSMContext):
    u = get_user(call.from_user.id)
    if u["balance"] < 0:
        await call.answer("❌ Ты в долгу.", show_alert=True); return
    await state.set_state(States.enter_new_bet)
    await call.message.edit_text(
        f"✏️ <b>Изменить ставку</b>\n\nТекущая: <b>{u['bet']:.2f}$</b>\n"
        f"💵 Баланс: <b>{u['balance']:.2f}$</b>\n\n"
        f"Напиши новую сумму (мин. <b>{MIN_BET}$</b>) или <b>отмена</b>.",
        parse_mode="HTML",
    )
    await call.answer()

@router.message(States.enter_new_bet)
async def process_new_bet(message: Message, state: FSMContext):
    text = (message.text or "").strip().lower()
    if text == "отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=menu_games()); return
    try:
        new_bet = float(text.replace(",", "."))
    except ValueError:
        await message.answer("❌ Введи число."); return
    if new_bet < MIN_BET:
        await message.answer(f"❌ Минимальная ставка — <b>{MIN_BET}$</b>", parse_mode="HTML"); return
    u = get_user(message.from_user.id)
    if new_bet > u["balance"]:
        await message.answer(
            f"❌ Ставка не может быть больше баланса.\n"
            f"💵 Баланс: <b>{u['balance']:.2f}$</b>", parse_mode="HTML"); return
    update_user(message.from_user.id, bet=new_bet)
    await state.clear()
    await message.answer(f"✅ Новая ставка сохранена: <b>{new_bet:.2f}$</b>",
                         parse_mode="HTML", reply_markup=menu_games())

@router.message(States.enter_bet)
async def process_bet_dummy(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Выбери игру заново.",
                         reply_markup=menu_main(get_user(message.from_user.id)))


def check_win(game_key: str, code: str, value: int) -> bool:
    if game_key == "dice":
        if code == "even":  return value % 2 == 0
        if code == "odd":   return value % 2 == 1
        if code == "lt":    return value < 3.5
        if code == "gt":    return value > 3.5
        if code in ("eq1","eq2","eq3","eq4","eq5","eq6"):
            return value == int(code[-1])
        if code == "ladder": return value in (2,3,4,5)
    if game_key == "football":
        if code == "center": return value == 3
        if code == "corner": return value == 5
        if code == "post":   return value == 4
        if code == "any":    return value in (3, 4, 5)
        if code == "hit":    return value == 2
        if code == "miss":   return value == 1
    if game_key == "basketball":
        if code == "clean":  return value == 5
        if code == "spin":   return value == 4
        if code == "stuck":  return value == 3
        if code == "any":    return value >= 4
        if code == "bounce": return value == 2
        if code == "miss":   return value == 1
    if game_key == "darts":
        if code == "center": return value == 6
        if code == "bounce": return value == 5
        if code == "red":    return value == 2
        if code == "white":  return value in (3, 4)
        if code == "any":    return value in (2, 3, 4)
    if game_key == "bowling":
        if code == "strike": return value == 6
        if code == "miss":   return value == 1
        if code == "one":    return value == 2
        if code == "three":  return value == 3
        if code == "four":   return value == 4
        if code == "five":   return value == 5
        if code == "ns":     return value in (2, 3, 4, 5)
        if code == "nm":     return value in (2, 3, 4, 5, 6)
    if game_key == "slots":
        def decode_slot(v):
            v -= 1
            return ((v >> 4) & 0x03, (v >> 2) & 0x03, v & 0x03)
        parts = decode_slot(value)
        all_same = parts[0] == parts[1] == parts[2]
        all_diff = parts[0] != parts[1] and parts[1] != parts[2] and parts[0] != parts[2]
        if code == "s777":  return value == 64
        if code == "sbbb":  return value == 1
        if code == "slll":  return value == 43
        if code == "sggg":  return value == 22
        if code == "any3":  return all_same
        if code == "uniq":  return all_diff
    return False


# ==================== ПРОФИЛЬ / РЕЙК / РЕЗЕРВ ====================
@router.callback_query(F.data == "profile")
async def cb_profile(call: CallbackQuery):
    u = get_user(call.from_user.id)
    debt = ""
    if u["balance"] < 0:
        debt = f"\n⚠️ <b>В долгу: {abs(u['balance']):.2f}$</b>"
    await call.message.edit_text(
        f"👤 <b>Профиль</b>\n\n"
        f"🆔 ID: <code>{call.from_user.id}</code>\n"
        f"📛 Ник: @{call.from_user.username or '—'}\n\n"
        f"💵 Баланс: <b>{u['balance']:.2f}$</b>{debt}\n"
        f"📊 Оборот: <b>{u['turnover']:.2f}$</b>\n"
        f"💎 Рейк: <b>{u['rake_balance']:.2f}$</b>\n"
        f"💵 Ставка: <b>{u['bet']:.2f}$</b>\n"
        f"🎮 Игр: <b>{u['games']}</b>\n"
        f"🏆 Побед: <b>{u['wins']}</b>\n"
        f"📅 С нами с: {u['registered'][:10]}",
        parse_mode="HTML", reply_markup=back("moremenu"),
    )
    await call.answer()

@router.callback_query(F.data == "rake")
async def cb_rake(call: CallbackQuery):
    u = get_user(call.from_user.id)
    can = u["turnover"] >= RAKE_UNLOCK_THRESHOLD and u["rake_balance"] >= RAKE_CLAIM_MIN
    kb = InlineKeyboardBuilder()
    if can:
        kb.button(text=f"💸 Забрать {u['rake_balance']:.2f}$", callback_data="rake_claim")
    else:
        kb.button(text="🔒 Недоступно", callback_data="noop")
    kb.button(text="⬅️ Назад", callback_data="moremenu")
    kb.adjust(1)
    await call.message.edit_text(
        f"💎 <b>Рейк</b>\n\n"
        f"📊 Оборот: <b>{u['turnover']:.2f}$</b>\n"
        f"💎 Доступно: <b>{u['rake_balance']:.2f}$</b>\n"
        f"📈 Максимум: <b>{RAKE_MAX:.0f}$</b>\n\n"
        f"<i>Условия:</i>\n"
        f"• Отыграно минимум <b>{RAKE_UNLOCK_THRESHOLD}$</b>\n"
        f"• Мин. вывод — <b>{RAKE_CLAIM_MIN}$</b>",
        parse_mode="HTML", reply_markup=kb.as_markup(),
    )
    await call.answer()

@router.callback_query(F.data == "rake_claim")
async def cb_rake_claim(call: CallbackQuery):
    u = get_user(call.from_user.id)
    if u["turnover"] < RAKE_UNLOCK_THRESHOLD:
        await call.answer(f"❌ Сначала отыграй {RAKE_UNLOCK_THRESHOLD}$", show_alert=True); return
    if u["rake_balance"] < RAKE_CLAIM_MIN:
        await call.answer(f"❌ Минимум {RAKE_CLAIM_MIN}$", show_alert=True); return
    amount = u["rake_balance"]
    update_user(call.from_user.id, balance=u["balance"] + amount, rake_balance=0.0)
    await call.answer(f"✅ Забрано {amount:.2f}$", show_alert=True)
    await cb_rake(call)

@router.callback_query(F.data == "reserve")
async def cb_reserve(call: CallbackQuery):
    u = get_user(call.from_user.id)
    can = u["turnover"] >= RAKE_UNLOCK_THRESHOLD
    kb = InlineKeyboardBuilder()
    if can:
        kb.button(text="🏦 Забрать из резерва", callback_data="reserve_claim")
    else:
        kb.button(text="🔒 Недоступно", callback_data="noop")
    kb.button(text="⬅️ Назад", callback_data="moremenu")
    kb.adjust(1)
    await call.message.edit_text(
        f"🏦 <b>Резерв</b>\n\nВ резерве бота: <b>{get_reserve():.2f}$</b>\n\n"
        f"Забрать можно при обороте от {RAKE_UNLOCK_THRESHOLD}$.",
        parse_mode="HTML", reply_markup=kb.as_markup(),
    )
    await call.answer()

@router.callback_query(F.data == "reserve_claim")
async def cb_reserve_claim(call: CallbackQuery):
    u = get_user(call.from_user.id)
    if u["turnover"] < RAKE_UNLOCK_THRESHOLD:
        await call.answer(f"❌ Нужен оборот от {RAKE_UNLOCK_THRESHOLD}$", show_alert=True); return
    reserve = get_reserve()
    if reserve <= 0:
        await call.answer("❌ Резерв пуст.", show_alert=True); return
    amount = round(reserve * 0.1, 2)
    if amount < 0.01:
        amount = reserve
    set_reserve(reserve - amount)
    update_user(call.from_user.id,
                balance=u["balance"] + amount,
                reserve_claimed=u["reserve_claimed"] + amount)
    await call.answer(f"🏦 Получено {amount:.2f}$", show_alert=True)
    await cb_reserve(call)


# ==================== ПРОМО ====================
@router.callback_query(F.data == "promo")
async def cb_promo(call: CallbackQuery, state: FSMContext):
    await state.set_state(States.enter_promo)
    await call.message.edit_text(TEXT_PROMO_ENTER, parse_mode="HTML")
    await call.answer()

@router.message(States.enter_promo)
async def process_promo(message: Message, state: FSMContext):
    code = (message.text or "").strip().upper()
    if code.lower() == "отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=menu_main(get_user(message.from_user.id))); return
    promos = load(PROMOS_FILE)
    if code not in promos:
        await message.answer("❌ Такого промокода нет.", reply_markup=back("moremenu"))
        await state.clear(); return
    p = promos[code]
    if p.get("used_by") and message.from_user.id in p["used_by"]:
        await message.answer("❌ Ты уже активировал этот промокод."); await state.clear(); return
    if p.get("limit", 0) > 0 and len(p.get("used_by", [])) >= p["limit"]:
        await message.answer("❌ Лимит активаций исчерпан."); await state.clear(); return
    amount = float(p["amount"])
    u = get_user(message.from_user.id)
    update_user(message.from_user.id, balance=u["balance"] + amount)
    p.setdefault("used_by", []).append(message.from_user.id)
    promos[code] = p
    save(PROMOS_FILE, promos)
    await message.answer(f"✅ <b>Промокод активирован!</b>\n\n💰 Начислено: <b>+{amount:.2f}$</b>",
                         parse_mode="HTML", reply_markup=back("main"))
    await state.clear()


# ==================== АДМИН-ПАНЕЛЬ ====================
@router.callback_query(F.data == "adm_close")
async def cb_adm_close(call: CallbackQuery):
    if not is_admin(call):
        await call.answer("Нет доступа", show_alert=True); return
    await call.message.edit_text("Админ-панель закрыта.", reply_markup=menu_main(get_user(call.from_user.id)))
    await call.answer()

@router.callback_query(F.data == "adm_back")
async def cb_adm_back(call: CallbackQuery, state: FSMContext):
    if not is_admin(call):
        await call.answer("Нет доступа", show_alert=True); return
    await state.clear()
    await call.message.edit_text(
        f"👑 <b>Админ-панель</b>\n\n🏦 Резерв: <b>{get_reserve():.2f}$</b>",
        parse_mode="HTML", reply_markup=menu_admin())
    await call.answer()

@router.callback_query(F.data == "adm_promo_new")
async def cb_adm_promo_new(call: CallbackQuery, state: FSMContext):
    if not is_admin(call):
        await call.answer("Нет доступа", show_alert=True); return
    await state.set_state(States.admin_promo_name)
    await call.message.edit_text("🎁 <b>Создание промокода</b>\n\nШаг 1/3. Отправь <b>название</b>.\n\n<i>Отмена — напиши</i> <b>отмена</b>",
                                 parse_mode="HTML")
    await call.answer()

@router.message(States.admin_promo_name)
async def adm_promo_name(message: Message, state: FSMContext):
    if not is_admin(message):
        await state.clear(); return
    if (message.text or "").strip().lower() == "отмена":
        await state.clear(); await message.answer("Отменено.", reply_markup=menu_admin()); return
    name = (message.text or "").strip().upper()
    if not name or " " in name:
        await message.answer("❌ Название без пробелов, одно слово."); return
    await state.update_data(promo_name=name)
    await state.set_state(States.admin_promo_amount)
    await message.answer(f"🎁 Промокод: <b>{name}</b>\n\nШаг 2/3. Сколько <b>$</b> он будет давать?",
                         parse_mode="HTML")

@router.message(States.admin_promo_amount)
async def adm_promo_amount(message: Message, state: FSMContext):
    if not is_admin(message):
        await state.clear(); return
    if (message.text or "").strip().lower() == "отмена":
        await state.clear(); await message.answer("Отменено.", reply_markup=menu_admin()); return
    try:
        amount = float((message.text or "").replace(",", "."))
    except ValueError:
        await message.answer("❌ Введи число."); return
    if amount <= 0:
        await message.answer("❌ Сумма > 0."); return
    await state.update_data(promo_amount=amount)
    await state.set_state(States.admin_promo_limit)
    await message.answer(f"💰 Сумма: <b>{amount}$</b>\n\nШаг 3/3. Сколько <b>активаций</b>? (0 = без лимита)",
                         parse_mode="HTML")

@router.message(States.admin_promo_limit)
async def adm_promo_limit(message: Message, state: FSMContext):
    if not is_admin(message):
        await state.clear(); return
    if (message.text or "").strip().lower() == "отмена":
        await state.clear(); await message.answer("Отменено.", reply_markup=menu_admin()); return
    try:
        limit = int((message.text or "").strip())
    except ValueError:
        await message.answer("❌ Введи целое число."); return
    data = await state.get_data()
    code = data["promo_name"]; amount = data["promo_amount"]
    promos = load(PROMOS_FILE)
    if code in promos:
        await message.answer(f"⚠️ Промокод <b>{code}</b> уже есть.", parse_mode="HTML")
        await state.set_state(States.admin_promo_name); return
    promos[code] = {"amount": amount, "limit": limit, "used_by": [], "created": datetime.now().isoformat()}
    save(PROMOS_FILE, promos)
    await state.clear()
    await message.answer(f"✅ Промокод <b>{code}</b> создан.\n💰 {amount}$ · 🔢 {limit if limit else '∞'}",
                         parse_mode="HTML", reply_markup=menu_admin())

@router.callback_query(F.data == "adm_promo_list")
async def cb_adm_promo_list(call: CallbackQuery):
    if not is_admin(call):
        await call.answer("Нет доступа", show_alert=True); return
    promos = load(PROMOS_FILE)
    if not promos:
        text = "📋 <b>Промокоды</b>\n\n<i>Пока нет.</i>"
    else:
        lines = ["📋 <b>Промокоды</b>\n"]
        for code, p in promos.items():
            used = len(p.get("used_by", []))
            limit = p.get("limit", 0)
            lim_str = f"{used}/{limit}" if limit else f"{used}/∞"
            lines.append(f"• <b>{code}</b> — {p['amount']}$ · {lim_str}")
        text = "\n".join(lines)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=menu_admin())
    await call.answer()

@router.callback_query(F.data == "adm_give")
async def cb_adm_give(call: CallbackQuery, state: FSMContext):
    if not is_admin(call):
        await call.answer("Нет доступа", show_alert=True); return
    await state.set_state(States.admin_give_user)
    await call.message.edit_text("💵 <b>Выдать баланс</b>\n\nЮзернейм игрока (без @):", parse_mode="HTML")
    await call.answer()

@router.message(States.admin_give_user)
async def adm_give_user(message: Message, state: FSMContext):
    if not is_admin(message):
        await state.clear(); return
    if (message.text or "").strip().lower() == "отмена":
        await state.clear(); await message.answer("Отменено.", reply_markup=menu_admin()); return
    uname = (message.text or "").strip().lstrip('@')
    uid, data = find_user_by_username(uname)
    if uid is None:
        await message.answer(f"❌ @{uname} не найден."); return
    await state.update_data(target_uid=uid, target_uname=uname)
    await state.set_state(States.admin_give_amount)
    await message.answer(f"👤 @{uname}\n💵 Баланс: <b>{data['balance']:.2f}$</b>\n\nСколько начислить?",
                         parse_mode="HTML")

@router.message(States.admin_give_amount)
async def adm_give_amount(message: Message, state: FSMContext):
    if not is_admin(message):
        await state.clear(); return
    if (message.text or "").strip().lower() == "отмена":
        await state.clear(); await message.answer("Отменено.", reply_markup=menu_admin()); return
    try:
        amount = float((message.text or "").replace(",", "."))
    except ValueError:
        await message.answer("❌ Введи число."); return
    if amount <= 0:
        await message.answer("❌ Сумма > 0."); return
    data = await state.get_data()
    uid = data["target_uid"]; uname = data["target_uname"]
    u = get_user(uid)
    update_user(uid, balance=u["balance"] + amount)
    await state.clear()
    await message.answer(f"✅ @{uname}: <b>+{amount:.2f}$</b>\nНовый баланс: <b>{u['balance'] + amount:.2f}$</b>",
                         parse_mode="HTML", reply_markup=menu_admin())
    try:
        await message.bot.send_message(uid, f"💰 <b>Пополнение</b>\n\n+{amount:.2f}$", parse_mode="HTML")
    except Exception:
        pass

@router.callback_query(F.data == "adm_take")
async def cb_adm_take(call: CallbackQuery, state: FSMContext):
    if not is_admin(call):
        await call.answer("Нет доступа", show_alert=True); return
    await state.set_state(States.admin_take_user)
    await call.message.edit_text(
        "💸 <b>Забрать баланс</b>\n\n"
        "Юзернейм игрока (без @).\n"
        "<i>Если заберёшь больше, чем есть — баланс уйдёт в минус, игрок будет отбивать.</i>",
        parse_mode="HTML")
    await call.answer()

@router.message(States.admin_take_user)
async def adm_take_user(message: Message, state: FSMContext):
    if not is_admin(message):
        await state.clear(); return
    if (message.text or "").strip().lower() == "отмена":
        await state.clear(); await message.answer("Отменено.", reply_markup=menu_admin()); return
    uname = (message.text or "").strip().lstrip('@')
    uid, data = find_user_by_username(uname)
    if uid is None:
        await message.answer(f"❌ @{uname} не найден."); return
    await state.update_data(target_uid=uid, target_uname=uname)
    await state.set_state(States.admin_take_amount)
    await message.answer(f"👤 @{uname}\n💵 Баланс: <b>{data['balance']:.2f}$</b>\n\nСколько списать?",
                         parse_mode="HTML")

@router.message(States.admin_take_amount)
async def adm_take_amount(message: Message, state: FSMContext):
    if not is_admin(message):
        await state.clear(); return
    if (message.text or "").strip().lower() == "отмена":
        await state.clear(); await message.answer("Отменено.", reply_markup=menu_admin()); return
    try:
        amount = float((message.text or "").replace(",", "."))
    except ValueError:
        await message.answer("❌ Введи число."); return
    if amount <= 0:
        await message.answer("❌ Сумма > 0."); return
    data = await state.get_data()
    uid = data["target_uid"]; uname = data["target_uname"]
    u = get_user(uid)
    new_balance = u["balance"] - amount  # может уйти в минус
    update_user(uid, balance=new_balance)
    await state.clear()
    await message.answer(
        f"✅ @{uname}: <b>-{amount:.2f}$</b>\n"
        f"Новый баланс: <b>{new_balance:.2f}$</b>"
        + ("\n⚠️ Игрок в минусе — будет отбивать." if new_balance < 0 else ""),
        parse_mode="HTML", reply_markup=menu_admin())

@router.callback_query(F.data == "adm_reserve")
async def cb_adm_reserve(call: CallbackQuery):
    if not is_admin(call):
        await call.answer("Нет доступа", show_alert=True); return
    await call.message.edit_text(f"🏦 <b>Резерв</b>\n\nТекущий: <b>{get_reserve():.2f}$</b>",
                                 parse_mode="HTML", reply_markup=menu_admin_reserve())
    await call.answer()

@router.callback_query(F.data == "adm_res_add")
async def cb_adm_res_add(call: CallbackQuery, state: FSMContext):
    if not is_admin(call):
        await call.answer("Нет доступа", show_alert=True); return
    await state.update_data(reserve_action="add")
    await state.set_state(States.admin_reserve_amount)
    await call.message.edit_text("➕ <b>Добавить в резерв</b>\n\nНапиши сумму.", parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "adm_res_take")
async def cb_adm_res_take(call: CallbackQuery, state: FSMContext):
    if not is_admin(call):
        await call.answer("Нет доступа", show_alert=True); return
    await state.update_data(reserve_action="take")
    await state.set_state(States.admin_reserve_amount)
    await call.message.edit_text("➖ <b>Убрать из резерва</b>\n\nНапиши сумму.", parse_mode="HTML")
    await call.answer()

@router.message(States.admin_reserve_amount)
async def adm_reserve_amount(message: Message, state: FSMContext):
    if not is_admin(message):
        await state.clear(); return
    if (message.text or "").strip().lower() == "отмена":
        await state.clear(); await message.answer("Отменено.", reply_markup=menu_admin()); return
    try:
        amount = float((message.text or "").replace(",", "."))
    except ValueError:
        await message.answer("❌ Введи число."); return
    if amount <= 0:
        await message.answer("❌ Сумма > 0."); return
    data = await state.get_data()
    action = data.get("reserve_action")
    reserve = get_reserve()
    if action == "add":
        set_reserve(reserve + amount)
        await message.answer(f"🏦 +{amount:.2f}$\nРезерв: <b>{reserve + amount:.2f}$</b>",
                             parse_mode="HTML", reply_markup=menu_admin())
    else:
        set_reserve(reserve - amount)
        await message.answer(f"🏦 -{amount:.2f}$\nРезерв: <b>{max(0, reserve - amount):.2f}$</b>",
                             parse_mode="HTML", reply_markup=menu_admin())
    await state.clear()

# --- Рассылка ---
@router.callback_query(F.data == "adm_broadcast")
async def cb_adm_broadcast(call: CallbackQuery, state: FSMContext):
    if not is_admin(call):
        await call.answer("Нет доступа", show_alert=True); return
    await state.set_state(States.admin_broadcast)
    await call.message.edit_text(
        "📢 <b>Рассылка</b>\n\nОтправь сообщение для всех игроков.\nМожно с HTML: <b>жирный</b>, <i>курсив</i>.\n\n"
        "<i>Отмена — напиши</i> <b>отмена</b>",
        parse_mode="HTML")
    await call.answer()

@router.message(States.admin_broadcast)
async def adm_broadcast_send(message: Message, state: FSMContext):
    if not is_admin(message):
        await state.clear(); return
    text = (message.text or "").strip()
    if text.lower() == "отмена":
        await state.clear(); await message.answer("Отменено.", reply_markup=menu_admin()); return
    if not text:
        await message.answer("❌ Пустое сообщение."); return
    db = load(DB_FILE)
    total = len(db); sent = 0; failed = 0
    wait = await message.answer(f"📢 Отправляю... 0/{total}")
    for i, uid_str in enumerate(db.keys(), 1):
        try:
            await message.bot.send_message(int(uid_str), text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
        if i % 10 == 0 or i == total:
            try:
                await wait.edit_text(f"📢 Отправляю... {i}/{total}")
            except Exception:
                pass
        await asyncio.sleep(0.05)
    await state.clear()
    await message.answer(
        f"✅ <b>Рассылка завершена</b>\n\n"
        f"📬 Отправлено: <b>{sent}</b>\n❌ Ошибок: <b>{failed}</b>\n👥 Всего: <b>{total}</b>",
        parse_mode="HTML", reply_markup=menu_admin())

# --- Наказать ---
@router.callback_query(F.data == "adm_punish")
async def cb_adm_punish(call: CallbackQuery, state: FSMContext):
    if not is_admin(call):
        await call.answer("Нет доступа", show_alert=True); return
    await state.set_state(States.admin_punish_user)
    await call.message.edit_text(
        "⚖️ <b>Наказать игрока</b>\n\n"
        "Шаг 1/2. Юзернейм игрока (без @):",
        parse_mode="HTML")
    await call.answer()

@router.message(States.admin_punish_user)
async def adm_punish_user(message: Message, state: FSMContext):
    if not is_admin(message):
        await state.clear(); return
    if (message.text or "").strip().lower() == "отмена":
        await state.clear(); await message.answer("Отменено.", reply_markup=menu_admin()); return
    uname = (message.text or "").strip().lstrip('@')
    uid, data = find_user_by_username(uname)
    if uid is None:
        await message.answer(f"❌ @{uname} не найден."); return
    await state.update_data(target_uid=uid, target_uname=uname)
    await state.set_state(States.admin_punish_count)
    await message.answer(
        f"👤 @{uname}\n\n"
        f"Шаг 2/2. Сколько <b>исправительных работ</b> дать?\n"
        f"<i>Игрок должен будет написать</i> <b>{WORK_WORD}</b> <i>столько раз.</i>\n\n"
        f"Напиши число:",
        parse_mode="HTML")

@router.message(States.admin_punish_count)
async def adm_punish_count(message: Message, state: FSMContext):
    if not is_admin(message):
        await state.clear(); return
    if (message.text or "").strip().lower() == "отмена":
        await state.clear(); await message.answer("Отменено.", reply_markup=menu_admin()); return
    try:
        count = int((message.text or "").strip())
    except ValueError:
        await message.answer("❌ Введи целое число."); return
    if count <= 0:
        await message.answer("❌ Число > 0."); return
    data = await state.get_data()
    uid = data["target_uid"]; uname = data["target_uname"]
    update_user(uid, punish_remaining=count, punish_total=count)
    await state.clear()
    await message.answer(
        f"✅ @{uname}: назначено <b>{count}</b> исправительных работ.",
        parse_mode="HTML", reply_markup=menu_admin())
    # Уведомление игроку — без публикации другим
    try:
        await message.bot.send_message(
            uid,
            f"⚖️ <b>Тебе назначены исправительные работы</b>\n\n"
            f"Нужно написать: <b>{WORK_WORD}</b>\n"
            f"Количество раз: <b>{count}</b>\n\n"
            f"После каждой правильной фразы будет счётчик.",
            parse_mode="HTML")
    except Exception:
        pass


# ==================== ОТРАБОТКА НАКАЗАНИЯ ====================
# Хендлер WORK_WORD уже выше — он сработает для любого игрока,
# у которого punish_remaining > 0.
# Если игрок пишет НЕ WORK_WORD, а у него есть punish_remaining —
# ловим это отдельным хендлером ниже.

# Заглушка-обработчик на «не то слово при наказании»
# (нужно поставить ПОСЛЕ всех остальных текстовых хендлеров)
async def handle_wrong_punish_word(message: Message):
    u = get_user(message.from_user.id)
    if u.get("punish_remaining", 0) <= 0:
        return False
    # Игрок в наказании, но написал не то слово
    code = f"0x{random.randint(0x1000, 0xFFFF):X}"
    lines = random.choice([
        f"⚠️ SYNTAX ERROR {code}\n",
        f"⚠️ SEGMENTATION FAULT {code}\n",
        f"⚠️ RUNTIME ERROR {code}\n",
        f"⚠️ UNKNOWN EXCEPTION {code}\n",
        f"⚠️ SYSTEM FAILURE {code}\n",
    ])
    garbage = "".join(random.choices("!@#$%^&*()_+-=[]{}|;:,.<>?/\\~`0123456789ABCDEFabcdef", k=20))
    await message.answer(
        f"<code>{lines}\n{garbage}\n{garbage}</code>\n\n"
        f"👉 Напиши: <b>{WORK_WORD}</b>",
        parse_mode="HTML",
    )
    return True


# ==================== ТОП ====================
async def send_top(message: Message):
    db = load(DB_FILE)
    players = [(uid, d) for uid, d in db.items() if d.get("turnover", 0) > 0]
    players.sort(key=lambda x: x[1].get("turnover", 0), reverse=True)
    lines = ["🏆 <b>Топ по обороту</b>\n"]
    for i, (uid, d) in enumerate(players[:10], 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        lines.append(f"{medal} @{d.get('name', '—')} — <b>{d.get('turnover', 0):.2f}$</b>")
    if len(lines) == 1:
        lines.append("<i>Пока никого нет.</i>")
    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=back("moremenu"))

@router.callback_query(F.data == "top")
async def cb_top(call: CallbackQuery):
    await send_top(call.message)
    await call.answer()

@router.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery):
    await call.answer()


# ==================== ПЕРЕХВАТ «НЕ ТО СЛОВО» ПРИ НАКАЗАНИИ ====================
@router.message(F.text)
async def catch_all_text(message: Message, state: FSMContext):
    # Не трогаем команды в состояниях
    current = await state.get_state()
    if current is not None:
        return
    u = get_user(message.from_user.id)
    if u.get("punish_remaining", 0) > 0:
        # проверяем, что не WORK_WORD (его уже перехватил хендлер выше)
        if message.text.strip().lower() != WORK_WORD:
            await handle_wrong_punish_word(message)


# ==================== ЗАПУСК ====================
async def main():
    if VPN_PROXY:
        from aiogram.client.session.aiohttp import AiohttpSession
        session = AiohttpSession(proxy=VPN_PROXY)
        bot = Bot(token=BOT_TOKEN, session=session)
    else:
        bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    print("Red Cube DEMO запущен.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())