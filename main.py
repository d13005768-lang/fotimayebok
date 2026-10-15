"""
Red Cube DEMO bot — финальная сборка.
"""

import asyncio, json, os, random, logging
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
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

DEBT_WORK_REWARD = 10.0
WORK_WORD = "админ лучший"
VPN_PROXY = None

SLOT_SYMBOLS = ["🍒","🍋","🍊","🍇","💎","7️⃣"]
SLOT_MULT = {"🍒":3.0,"🍋":5.0,"🍊":7.0,"🍇":10.0,"💎":25.0,"7️⃣":50.0}
SLOT_PAIR_MULT = 1.2

WHEEL_SEGMENTS = [("Пусто",0.0,63.0),("x1.5",1.5,18.0),("x2",2.0,10.0),("x3",3.0,5.0),
                  ("x5",5.0,2.0),("x8",8.0,1.5),("x20",20.0,0.4),("x50",50.0,0.1)]
COIN_MULT = 1.9

MINES_GRID = 5
MINES_COUNT = 3
MINES_MULTS = [1.0,1.3,1.7,2.3,3.2,4.5,6.5,9.5,14.0,21.0,32.0,48.0,72.0,108.0,162.0,243.0,365.0,550.0,820.0,1230.0,1850.0,2770.0]

DOORS_COUNT = 4
DOORS_WIN_CHANCE = 0.96
DOORS_WIN_MULT = 3.9

TOWER_MAX_FLOOR = 10
TOWER_MULTS = [1.5,2.2,3.3,5.0,7.5,11.0,17.0,25.0,38.0,57.0]
TOWER_CRASH_CHANCE = 0.15

BALL_BETS = [
    ("x2",2.0,0.475,"🎈"),("x5",5.0,0.190,"🐟"),("x7",7.0,0.135,"🐬"),
    ("x10",10.0,0.095,"🐋"),("x15",15.0,0.063,"💸"),("x17",17.0,0.056,"💰"),
    ("x20",20.0,0.0475,"🎩"),("x30",30.0,0.032,"💼"),("x50",50.0,0.019,"💎"),
    ("x70",70.0,0.0135,"👑"),("x100",100.0,0.0095,"🚀"),
]

TEXT_START = ("👋 Привет, <b>{name}</b>!\n\nЭто <b>демо-бот</b>.\n"
              "💵 Баланс: <b>{balance:.2f}$</b>\n💎 Рейк: <b>{rake:.2f}$</b>\n\n"
              "<i>Напиши</i> <b>команды</b>")
TEXT_HELP = ("📋 <b>Команды</b>\n\n• <b>меню</b> • <b>играть</b> • <b>вб</b>\n"
             "• <b>профиль</b> • <b>баланс</b> • <b>рейк</b> • <b>забрать рейк</b>\n"
             "• <b>резерв</b> • <b>промо</b> • <b>топ</b> • <b>команды</b>\n\n"
             "• <b>нк @юзер 0.5</b> — перевод")
TEXT_GAMES = "🎮 <b>Выберите игру!</b>"
TEXT_WORK = "🛠 <b>Режим отработки</b>"
TEXT_PROMO_ENTER = "🎁 <b>Введи промокод</b>\n\n<i>Отмена — отмена</i>"

logging.basicConfig(level=logging.INFO)
router = Router()

def describe_result(game_key, value):
    if game_key == "dice":
        return {1:"1️⃣ Единица",2:"2️⃣ Двойка",3:"3️⃣ Тройка",4:"4️⃣ Четвёрка",5:"5️⃣ Пятёрка",6:"6️⃣ Шестёрка"}.get(value,str(value))
    if game_key == "football":
        return {1:"🚫 Промах",2:"🥅 Удар об штангу (не гол)",3:"⚽ Гол в центр",4:"⚽ Гол от штанги",5:"⚽ Гол в угол"}.get(value,str(value))
    if game_key == "basketball":
        return {1:"🚫 Промах",2:"🏀 Отскок",3:"🏀 Застрял (не залетел)",4:"🏀 Прокрут (залетел)",5:"🏀 Чистый гол"}.get(value,str(value))
    if game_key == "darts":
        return {1:"⚪ Белый",2:"🔴 Красный",3:"⚪ Белый",4:"🔴 Красный",5:"🎯 Отскок",6:"🎯 В яблочко"}.get(value,str(value))
    if game_key == "bowling":
        return {1:"🚫 Промах",2:"🎳 Сбита 1",3:"🎳 Сбито 3",4:"🎳 Сбито 4",5:"🎳 Сбито 5",6:"🎳 Страйк!"}.get(value,str(value))
    if game_key == "slots":
        def dec(v):
            v-=1
            return ((v>>4)&3,(v>>2)&3,v&3)
        S=["BAR","🍇","🍋","7️⃣"]
        p=dec(value); n=[S[x] for x in p]
        if p[0]==p[1]==p[2]: return f"🎰 {n[0]}-{n[1]}-{n[2]} (все одинаковые)"
        if len(set(p))==3: return f"🎰 {n[0]}-{n[1]}-{n[2]} (все разные)"
        return f"🎰 {n[0]}-{n[1]}-{n[2]}"
    return f"{value}"

def load(file, default=None):
    if not os.path.exists(file): return default if default is not None else {}
    with open(file,'r',encoding='utf-8') as f: return json.load(f)
def save(file, data):
    with open(file,'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)

def get_user(uid, username="", first_name=""):
    db = load(DB_FILE); k = str(uid)
    if k not in db:
        db[k] = {"username":username.lstrip('@') if username else "","first_name":first_name or "",
                 "balance":START_BALANCE,"rake_balance":0.0,"turnover":0.0,"wins":0,"games":0,
                 "rake_earned":0.0,"reserve_claimed":0.0,"is_admin":False,"bet":MIN_BET,
                 "work_streak":0,"work_last_value":0,"punish_remaining":0,"punish_total":0,
                 "registered":datetime.now().isoformat()}
        save(DB_FILE, db)
    else:
        ch=False
        if username and db[k].get("username")!=username.lstrip('@'):
            db[k]["username"]=username.lstrip('@'); ch=True
        if first_name and db[k].get("first_name")!=first_name:
            db[k]["first_name"]=first_name; ch=True
        for kk,vv in {"bet":MIN_BET,"work_streak":0,"work_last_value":0,"punish_remaining":0,"punish_total":0,"username":"","first_name":""}.items():
            if kk not in db[k]: db[k][kk]=vv; ch=True
        if ch: save(DB_FILE, db)
    return db[k]

def update_user(uid, **kw):
    db = load(DB_FILE); k = str(uid)
    if k not in db:
        db[k] = {"username":"","first_name":"","balance":START_BALANCE,"rake_balance":0.0,
                 "turnover":0.0,"wins":0,"games":0,"rake_earned":0.0,"reserve_claimed":0.0,
                 "is_admin":False,"bet":MIN_BET,"work_streak":0,"work_last_value":0,
                 "punish_remaining":0,"punish_total":0}
    db[k].update(kw); save(DB_FILE, db)

def find_user(query):
    db = load(DB_FILE); q = query.lstrip('@').strip().lower()
    if q.isdigit() and q in db: return int(q), db[q]
    for uid,d in db.items():
        if str(d.get("username","")).lower()==q: return int(uid),d
    for uid,d in db.items():
        if str(d.get("first_name","")).lower()==q: return int(uid),d
    for uid,d in db.items():
        if str(d.get("username","")).lower().startswith(q) or str(d.get("first_name","")).lower().startswith(q):
            return int(uid),d
    return None,None

def is_admin(m):
    db = load(DB_FILE)
    return db.get(str(m.from_user.id),{}).get("is_admin",False)
def get_reserve():
    return float(load(RESERVE_FILE,{"amount":1000.0}).get("amount",1000.0))
def set_reserve(v):
    save(RESERVE_FILE,{"amount":max(0.0,float(v))})
def add_reserve(v):
    set_reserve(get_reserve()+v)

class States(StatesGroup):
    enter_bet=State(); enter_new_bet=State(); enter_promo=State(); enter_admin_code=State()
    admin_promo_name=State(); admin_promo_amount=State(); admin_promo_limit=State()
    admin_give_user=State(); admin_give_amount=State(); admin_take_user=State(); admin_take_amount=State()
    admin_reserve_amount=State(); admin_broadcast=State(); admin_punish_user=State(); admin_punish_count=State()
    work_guess=State(); mines_game=State(); tower_game=State()

GAMES = {
    "dice":{"emoji":"🎲","name":"Кубик","outcomes_1":[
        ("Чёт (x2)","even",2.0),("Нечет (x2)","odd",2.0),("Меньше (x2)","lt",2.0),("Больше (x2)","gt",2.0),
        ("1 (x6)","eq1",6.0),("2 (x6)","eq2",6.0),("3 (x6)","eq3",6.0),("4 (x6)","eq4",6.0),("5 (x6)","eq5",6.0),("6 (x6)","eq6",6.0),
        ("Лесенка (x2.2)","ladder",2.2)]},
    "football":{"emoji":"⚽","name":"Футбол","outcomes_1":[
        ("Гол в центр (x5)","center",5.0),("Гол в угол (x5)","corner",5.0),("Гол от штанги (x5)","post",5.0),
        ("Любой гол (x1.66)","any",1.66),("Удар об штангу (x2.5)","hit",2.5),("Промах (x2.5)","miss",2.5)]},
    "basketball":{"emoji":"🏀","name":"Баскетбол","outcomes_1":[
        ("Чистый гол (x5)","clean",5.0),("Прокрут (x2.5)","spin",2.5),("Застрял мяч (x5)","stuck",5.0),
        ("Любой гол (x2.5)","any",2.5),("Отскок (x5)","bounce",5.0),("Промах (x1.66)","miss",1.66)]},
    "darts":{"emoji":"🎯","name":"Дартс","outcomes_1":[
        ("Центр (x6)","center",6.0),("Отскок (x6)","bounce",6.0),("Красный сектор (x3)","red",3.0),
        ("Белый сектор (x3)","white",3.0),("Любой сектор (x1.5)","any",1.5)]},
    "bowling":{"emoji":"🎳","name":"Боулинг","outcomes_1":[
        ("Страйк (x6)","strike",6.0),("Промах (x6)","miss",6.0),("Сбита 1/6 (x6)","one",6.0),
        ("Сбито 3/6 (x6)","three",6.0),("Сбито 4/6 (x6)","four",6.0),("Сбито 5/6 (x6)","five",6.0),
        ("Без страйка (x1.44)","ns",1.44),("Без промаха (x1.44)","nm",1.44)]},
    "slots":{"emoji":"🎰","name":"Слоты","outcomes_1":[
        ("3 Семёрки (x64)","s777",64.0),("3 Лимона (x64)","slll",64.0),("3 Винограда (x64)","sggg",64.0),
        ("3 Бара (x64)","sbbb",64.0),("Любая комбинация (x16)","any3",16.0),("Уникальные символы (x2.66)","uniq",2.66)]},
}

def menu_main(u):
    kb = InlineKeyboardBuilder()
    kb.button(text="👛 Кошелёк",callback_data="wallet")
    if u["balance"]<0: kb.button(text="🛠 Отработать",callback_data="work")
    else: kb.button(text="🎮 Игры",callback_data="games")
    kb.button(text="≡ Меню",callback_data="moremenu")
    kb.adjust(3); return kb.as_markup()

def menu_games():
    kb = InlineKeyboardBuilder()
    for k,g in GAMES.items(): kb.button(text=f"{g['emoji']} {g['name']}",callback_data=f"g_{k}")
    kb.button(text="🎨 Авторские",callback_data="custom_games")
    kb.button(text="✏️ Изменить ставку",callback_data="change_bet")
    kb.adjust(3,3,1,1); return kb.as_markup()

def menu_outcomes(gk):
    g = GAMES[gk]; kb = InlineKeyboardBuilder()
    for label,code,mult in g["outcomes_1"]: kb.button(text=label,callback_data=f"o_{gk}_{code}")
    kb.button(text="✏️ Изменить ставку",callback_data="change_bet")
    kb.button(text="⬅️ Назад",callback_data="games")
    kb.adjust(2,2,2,2,2,2,1,1); return kb.as_markup()

def menu_more():
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Профиль",callback_data="profile"); kb.button(text="💎 Рейк",callback_data="rake")
    kb.button(text="🏦 Резерв",callback_data="reserve"); kb.button(text="🎁 Промокод",callback_data="promo")
    kb.button(text="🏆 Топ",callback_data="top"); kb.button(text="⬅️ Назад",callback_data="main")
    kb.adjust(2,2,2,1); return kb.as_markup()

def menu_admin():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎁 Создать промо",callback_data="adm_promo_new")
    kb.button(text="📋 Список промо",callback_data="adm_promo_list")
    kb.button(text="💵 Выдать баланс",callback_data="adm_give")
    kb.button(text="💸 Забрать баланс",callback_data="adm_take")
    kb.button(text="🏦 Резерв",callback_data="adm_reserve")
    kb.button(text="📢 Рассылка",callback_data="adm_broadcast")
    kb.button(text="⚖️ Наказать",callback_data="adm_punish")
    kb.button(text="👥 Все игроки",callback_data="adm_users")
    kb.button(text="❌ Закрыть",callback_data="adm_close")
    kb.adjust(1,1,2,1,1,1,1,1); return kb.as_markup()

def menu_admin_reserve():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить",callback_data="adm_res_add")
    kb.button(text="➖ Убрать",callback_data="adm_res_take")
    kb.button(text="⬅️ Назад",callback_data="adm_back")
    kb.adjust(1); return kb.as_markup()

def menu_custom_games():
    kb = InlineKeyboardBuilder()
    kb.button(text="🪙 Монетка (x1.9)",callback_data="cg_coin")
    kb.button(text="🎰 Слоты 3x3",callback_data="cg_slots")
    kb.button(text="🎡 Колесо Фортуны",callback_data="cg_wheel")
    kb.button(text="💣 Мины 5x5",callback_data="cg_mines")
    kb.button(text="🚪 4 двери",callback_data="cg_doors")
    kb.button(text="🏗 Башня",callback_data="cg_tower")
    kb.button(text="🎈 Шарик (x2–x100)",callback_data="cg_ball")
    kb.button(text="⬅️ Назад",callback_data="games")
    kb.adjust(1,1,1,1,1,1,1,1); return kb.as_markup()

def menu_ball():
    kb = InlineKeyboardBuilder()
    for label,_,_,emoji in BALL_BETS: kb.button(text=f"{emoji} {label}",callback_data=f"ball_{label}")
    kb.button(text="⬅️ Назад",callback_data="custom_games")
    kb.adjust(3,3,3,2,1); return kb.as_markup()

def back(t="main"):
    kb = InlineKeyboardBuilder(); kb.button(text="⬅️ Назад",callback_data=t); return kb.as_markup()

@router.message(CommandStart())
async def cmd_start(m: Message, st: FSMContext):
    await st.clear()
    u = get_user(m.from_user.id, m.from_user.username or "", m.from_user.first_name or "")
    await m.answer(TEXT_START.format(name=m.from_user.first_name,balance=u["balance"],rake=u["rake_balance"]),
                   parse_mode="HTML",reply_markup=menu_main(u))

@router.message(F.text.lower()=="команды")
async def cmd_help(m: Message): await m.answer(TEXT_HELP,parse_mode="HTML")

@router.message(F.text.lower()=="меню")
async def cmd_menu(m: Message, st: FSMContext):
    await st.clear(); u = get_user(m.from_user.id)
    await m.answer(f"🎰 <b>Меню</b>\n\n💵 Баланс: <b>{u['balance']:.2f}$</b>",
                   parse_mode="HTML",reply_markup=menu_main(u))

@router.message(F.text.lower()=="играть")
async def cmd_play(m: Message, st: FSMContext):
    await st.clear(); u = get_user(m.from_user.id)
    if u["balance"]<0:
        await m.answer(TEXT_WORK,parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛠 Отработать",callback_data="work")]]))
        return
    await m.answer(TEXT_GAMES,parse_mode="HTML",reply_markup=menu_games())

@router.message(F.text.lower()=="вб")
async def cmd_vb(m: Message, st: FSMContext):
    await st.clear(); u = get_user(m.from_user.id)
    if u["balance"]<0: await m.answer("❌ Ты в долгу."); return
    if u["balance"]<MIN_BET: await m.answer(f"❌ Баланс мал: <b>{u['balance']:.2f}$</b>",parse_mode="HTML"); return
    update_user(m.from_user.id,bet=u["balance"])
    await m.answer(f"✅ Ставка на весь баланс: <b>{u['balance']:.2f}$</b>",parse_mode="HTML",reply_markup=menu_games())

@router.message(F.text.lower()=="профиль")
async def cmd_prof(m: Message):
    u = get_user(m.from_user.id)
    debt = f"\n⚠️ Долг: <b>{abs(u['balance']):.2f}$</b>" if u["balance"]<0 else ""
    punish = f"\n⚖️ Работ: <b>{u['punish_remaining']}</b>" if u.get("punish_remaining",0)>0 else ""
    await m.answer(
        f"👤 <b>Профиль</b>\n\n🆔 <code>{m.from_user.id}</code>\n📛 @{u.get('username') or '—'}\n"
        f"📝 {u.get('first_name') or '—'}\n\n💵 Баланс: <b>{u['balance']:.2f}$</b>{debt}\n"
        f"📊 Оборот: <b>{u['turnover']:.2f}$</b>\n💎 Рейк: <b>{u['rake_balance']:.2f}$</b>\n"
        f"💵 Ставка: <b>{u['bet']:.2f}$</b>\n🎮 Игр: <b>{u['games']}</b>\n🏆 Побед: <b>{u['wins']}</b>{punish}",
        parse_mode="HTML",reply_markup=back("main"))

@router.message(F.text.lower()=="баланс")
async def cmd_bal(m: Message):
    u = get_user(m.from_user.id)
    debt = f"\n⚠️ Долг: <b>{abs(u['balance']):.2f}$</b>" if u["balance"]<0 else ""
    await m.answer(f"💵 Баланс: <b>{u['balance']:.2f}$</b>\n💎 Рейк: <b>{u['rake_balance']:.2f}$</b>{debt}",
                   parse_mode="HTML",reply_markup=back("main"))

@router.message(F.text.lower()=="рейк")
async def cmd_rake(m: Message):
    u = get_user(m.from_user.id)
    can = u["turnover"]>=RAKE_UNLOCK_THRESHOLD and u["rake_balance"]>=RAKE_CLAIM_MIN
    kb = InlineKeyboardBuilder()
    if can: kb.button(text=f"💸 Забрать {u['rake_balance']:.2f}$",callback_data="rake_claim")
    else: kb.button(text="🔒 Недоступно",callback_data="noop")
    kb.button(text="⬅️ Назад",callback_data="moremenu"); kb.adjust(1)
    await m.answer(f"💎 <b>Рейк</b>\n\n📊 Оборот: <b>{u['turnover']:.2f}$</b>\n"
                   f"💎 Доступно: <b>{u['rake_balance']:.2f}$</b>\n📈 Макс: <b>{RAKE_MAX:.0f}$</b>",
                   parse_mode="HTML",reply_markup=kb.as_markup())

@router.message(F.text.lower()=="забрать рейк")
async def cmd_rake_claim(m: Message):
    u = get_user(m.from_user.id)
    if u["turnover"]<RAKE_UNLOCK_THRESHOLD:
        await m.answer(f"❌ Отыграй <b>{RAKE_UNLOCK_THRESHOLD}$</b>",parse_mode="HTML"); return
    if u["rake_balance"]<RAKE_CLAIM_MIN:
        await m.answer(f"❌ Минимум <b>{RAKE_CLAIM_MIN}$</b>",parse_mode="HTML"); return
    amt = u["rake_balance"]
    update_user(m.from_user.id,balance=u["balance"]+amt,rake_balance=0.0)
    await m.answer(f"✅ Забран: <b>+{amt:.2f}$</b>\n💵 Баланс: <b>{u['balance']+amt:.2f}$</b>",parse_mode="HTML")

@router.message(F.text.lower()=="резерв")
async def cmd_res(m: Message):
    u = get_user(m.from_user.id)
    can = u["turnover"]>=RAKE_UNLOCK_THRESHOLD
    kb = InlineKeyboardBuilder()
    if can: kb.button(text="🏦 Забрать 10%",callback_data="reserve_claim")
    else: kb.button(text="🔒",callback_data="noop")
    kb.button(text="⬅️ Назад",callback_data="moremenu"); kb.adjust(1)
    await m.answer(f"🏦 Резерв: <b>{get_reserve():.2f}$</b>",parse_mode="HTML",reply_markup=kb.as_markup())

@router.message(F.text.lower()=="промо")
async def cmd_promo(m: Message, st: FSMContext):
    await st.set_state(States.enter_promo); await m.answer(TEXT_PROMO_ENTER,parse_mode="HTML")

@router.message(F.text.lower()=="топ")
async def cmd_top(m: Message): await send_top(m)

@router.message(F.text.lower()=="отмена")
async def cmd_cancel(m: Message, st: FSMContext):
    await st.clear(); await m.answer("Отменено.",reply_markup=menu_main(get_user(m.from_user.id)))

@router.message(F.text.lower()==WORK_WORD)
async def work_word(m: Message):
    u = get_user(m.from_user.id); rem = u.get("punish_remaining",0)
    if rem<=0: await m.answer("✅ Нет работ."); return
    rem-=1; update_user(m.from_user.id,punish_remaining=rem)
    total = u.get("punish_total",0) or (rem+1); done = total-rem
    if rem<=0: await m.answer("✅ <b>Работы выполнены!</b>",parse_mode="HTML",reply_markup=back("main"))
    else: await m.answer(f"📝 {done} из {total}\nОсталось: <b>{rem}</b>")

@router.callback_query(F.data=="work")
async def cb_work(c: CallbackQuery, st: FSMContext):
    u = get_user(c.from_user.id)
    if u["balance"]>=0: await c.answer("Нет долга."); return
    await st.set_state(States.work_guess); await c.answer()
    await c.message.edit_text(f"🛠 Долг: <b>{abs(u['balance']):.2f}$</b>\n"
        f"💰 +{DEBT_WORK_REWARD:.0f}$ за 2 угадывания\n\n🎲 Угадай 1-6:",parse_mode="HTML")

@router.message(States.work_guess)
async def process_work(m: Message, st: FSMContext):
    t = (m.text or "").strip().lower()
    if t=="отмена":
        await st.clear(); await m.answer("Отменено.",reply_markup=menu_main(get_user(m.from_user.id))); return
    if not t.isdigit() or not (1<=int(t)<=6): await m.answer("❌ 1-6."); return
    guess = int(t); u = get_user(m.from_user.id)
    msg = await m.answer_dice(emoji="🎲"); await asyncio.sleep(4); val = msg.dice.value
    if val==guess:
        streak = u.get("work_streak",0)+1
        update_user(m.from_user.id,work_streak=streak,work_last_value=val)
        if streak>=2:
            nb = u["balance"]+DEBT_WORK_REWARD
            update_user(m.from_user.id,balance=nb,work_streak=0)
            if nb>=0:
                await m.answer(f"🎲 {describe_result('dice',val)}\n✅ 2 раза! +{DEBT_WORK_REWARD:.0f}$\n💵 {nb:.2f}$\n🎉 Долг закрыт!",
                               parse_mode="HTML",reply_markup=menu_games()); await st.clear()
            else:
                await m.answer(f"🎲 {describe_result('dice',val)}\n✅ +{DEBT_WORK_REWARD:.0f}$\n💵 {nb:.2f}$\n⚠️ Ещё в долгу.",
                    parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛠",callback_data="work")]]))
        else: await m.answer(f"🎲 {describe_result('dice',val)}\n✅ 1/2")
    else:
        update_user(m.from_user.id,work_streak=0,work_last_value=val)
        await m.answer(f"🎲 {describe_result('dice',val)}\n❌ Не угадал.")

@router.message(F.text.lower()=="админка")
async def cmd_adm(m: Message, st: FSMContext):
    if is_admin(m):
        await m.answer(f"👑 Резерв: <b>{get_reserve():.2f}$</b>",parse_mode="HTML",reply_markup=menu_admin()); return
    await st.set_state(States.enter_admin_code)
    await m.answer("🔐 <b>Код</b>",parse_mode="HTML")

@router.message(States.enter_admin_code)
async def process_code(m: Message, st: FSMContext):
    code = (m.text or "").strip()
    if code.lower()=="отмена": await st.clear(); await m.answer("Отменено."); return
    if code==ADMIN_SECRET:
        update_user(m.from_user.id,is_admin=True); await st.clear()
        await m.answer("✅ Теперь ты админ!")
    else: await m.answer("❌ Неверный.")

@router.message(F.text.lower().startswith("нк "))
async def cmd_nk(m: Message):
    p = m.text.split()
    if len(p)!=3: await m.answer("❌ <code>нк @юзер 0.5</code>",parse_mode="HTML"); return
    q = p[1]
    try: amt = float(p[2].replace(",","."))
    except: await m.answer("❌ Число."); return
    if amt<=0: await m.answer("❌ > 0"); return
    tid,td = find_user(q)
    if tid is None: await m.answer(f"❌ «{q}» не найден."); return
    if tid==m.from_user.id: await m.answer("❌ Себе."); return
    s = get_user(m.from_user.id)
    if s["balance"]<amt: await m.answer("❌ Нет средств."); return
    update_user(m.from_user.id,balance=s["balance"]-amt)
    update_user(tid,balance=td["balance"]+amt)
    await m.answer(f"✅ {q}: <b>{amt:.2f}$</b>",parse_mode="HTML")
    try: await m.bot.send_message(tid,f"💰 +{amt:.2f}$",parse_mode="HTML")
    except: pass

@router.callback_query(F.data=="main")
async def cb_main(c: CallbackQuery, st: FSMContext):
    await st.clear(); u = get_user(c.from_user.id)
    await c.message.edit_text(f"🎰 <b>Меню</b>\n\n💵 {u['balance']:.2f}$",parse_mode="HTML",reply_markup=menu_main(u))
    await c.answer()

@router.callback_query(F.data=="wallet")
async def cb_wallet(c: CallbackQuery):
    u = get_user(c.from_user.id)
    debt = f"\n⚠️ Долг: <b>{abs(u['balance']):.2f}$</b>" if u["balance"]<0 else ""
    await c.message.edit_text(f"👛\n\n💵 <b>{u['balance']:.2f}$</b>{debt}\n💎 <b>{u['rake_balance']:.2f}$</b>\n📊 <b>{u['turnover']:.2f}$</b>",
                              parse_mode="HTML",reply_markup=back()); await c.answer()

@router.callback_query(F.data=="games")
async def cb_games(c: CallbackQuery):
    u = get_user(c.from_user.id)
    if u["balance"]<0: await c.answer("❌ В долгу.",show_alert=True); return
    await c.message.edit_text(TEXT_GAMES,parse_mode="HTML",reply_markup=menu_games()); await c.answer()

@router.callback_query(F.data=="moremenu")
async def cb_more(c: CallbackQuery):
    await c.message.edit_text("≡ <b>Меню</b>",parse_mode="HTML",reply_markup=menu_more()); await c.answer()

@router.callback_query(F.data.startswith("g_"))
async def cb_game(c: CallbackQuery, st: FSMContext):
    await st.clear(); u = get_user(c.from_user.id)
    if u["balance"]<0: await c.answer("❌ В долгу.",show_alert=True); return
    k = c.data.split("_",1)[1]
    if k not in GAMES: await c.answer("Нет",show_alert=True); return
    g = GAMES[k]
    await c.message.edit_text(f"{g['emoji']} <b>{g['name']}</b>\n💵 Ставка: <b>{u['bet']:.2f}$</b>\n\n🎯 Выберите:",
                              parse_mode="HTML",reply_markup=menu_outcomes(k)); await c.answer()

@router.callback_query(F.data.startswith("o_"))
async def cb_out(c: CallbackQuery, st: FSMContext):
    parts = c.data.split("_",2)
    if len(parts)!=3: await c.answer("Err",show_alert=True); return
    _,gk,code = parts
    if gk not in GAMES: await c.answer("Нет",show_alert=True); return
    g = GAMES[gk]; out = next((o for o in g["outcomes_1"] if o[1]==code),None)
    if not out: await c.answer("Нет",show_alert=True); return
    label,_,mult = out; u = get_user(c.from_user.id)
    if u["balance"]<0: await c.answer("❌ В долгу.",show_alert=True); return
    bet = u["bet"]
    if u["balance"]<bet: await c.answer(f"❌ Баланс {u['balance']:.2f}$, ставка {bet:.2f}$",show_alert=True); return
    await c.answer(f"Ставка {bet:.2f}$")
    await c.message.edit_text(f"{g['emoji']} {g['name']}\n🎯 {label}\n💵 <b>{bet:.2f}$</b>\n\n<i>Бросаем...</i>",parse_mode="HTML")
    update_user(c.from_user.id,balance=u["balance"]-bet,turnover=u["turnover"]+bet,games=u["games"]+1)
    msg = await c.message.answer_dice(emoji=g["emoji"]); await asyncio.sleep(4); val = msg.dice.value
    win = check_win(gk,code,val); rake = bet*RAKE_PERCENT; desc = describe_result(gk,val)
    u = get_user(c.from_user.id); nr = min(u["rake_balance"]+rake,RAKE_MAX)
    if win:
        pr = bet*mult
        update_user(c.from_user.id,balance=u["balance"]+pr,wins=u["wins"]+1,rake_balance=nr,rake_earned=u["rake_earned"]+rake)
        add_reserve(-pr); nu = get_user(c.from_user.id)
        await c.message.answer(f"🎉 <b>ВЫИГРЫШ!</b>\n\n{g['emoji']} {g['name']}\n🎲 <b>{desc}</b>\n🎯 x{mult}\n💵 {bet:.2f}$\n\n💰 <b>+{pr:.2f}$</b>\n💵 <b>{nu['balance']:.2f}$</b>",parse_mode="HTML")
    else:
        update_user(c.from_user.id,rake_balance=nr,rake_earned=u["rake_earned"]+rake); add_reserve(bet)
        nu = get_user(c.from_user.id)
        await c.message.answer(f"💀 <b>ПРОИГРЫШ</b>\n\n{g['emoji']} {g['name']}\n🎲 <b>{desc}</b>\n🎯 x{mult}\n💵 {bet:.2f}$\n\n📉 <b>-{bet:.2f}$</b>\n💵 <b>{nu['balance']:.2f}$</b>",parse_mode="HTML")
    nu = get_user(c.from_user.id)
    if nu["balance"]<0:
        await c.message.answer("⚠️ В минус. Отрабатывай.",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛠",callback_data="work")]]))
    else: await c.message.answer(TEXT_GAMES,parse_mode="HTML",reply_markup=menu_games())

@router.callback_query(F.data=="change_bet")
async def cb_change(c: CallbackQuery, st: FSMContext):
    u = get_user(c.from_user.id)
    if u["balance"]<0: await c.answer("❌ В долгу.",show_alert=True); return
    await st.set_state(States.enter_new_bet)
    await c.message.edit_text(f"✏️ Ставка: <b>{u['bet']:.2f}$</b>\n💵 Баланс: <b>{u['balance']:.2f}$</b>\n\nНовая (мин {MIN_BET}$) или <b>отмена</b>:",parse_mode="HTML")
    await c.answer()

@router.message(States.enter_new_bet)
async def process_nb(m: Message, st: FSMContext):
    t = (m.text or "").strip().lower()
    if t=="отмена": await st.clear(); await m.answer("Отменено.",reply_markup=menu_games()); return
    try: nb = float(t.replace(",","."))
    except: await m.answer("❌ Число."); return
    if nb<MIN_BET: await m.answer(f"❌ Мин {MIN_BET}$",parse_mode="HTML"); return
    u = get_user(m.from_user.id)
    if nb>u["balance"]: await m.answer(f"❌ > баланса ({u['balance']:.2f}$)",parse_mode="HTML"); return
    update_user(m.from_user.id,bet=nb); await st.clear()
    await m.answer(f"✅ Ставка: <b>{nb:.2f}$</b>",parse_mode="HTML",reply_markup=menu_games())

@router.callback_query(F.data=="custom_games")
async def cb_cg(c: CallbackQuery):
    u = get_user(c.from_user.id)
    if u["balance"]<0: await c.answer("❌ В долгу.",show_alert=True); return
    await c.message.edit_text(f"🎨 <b>Авторские</b>\n\n💵 {u['bet']:.2f}$",parse_mode="HTML",reply_markup=menu_custom_games())
    await c.answer()

@router.callback_query(F.data=="cg_coin")
async def cb_coin(c: CallbackQuery):
    u = get_user(c.from_user.id)
    if u["balance"]<u["bet"]: await c.answer("❌ Нет средств.",show_alert=True); return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🦅 Орёл",callback_data="coin_eagle"),InlineKeyboardButton(text="🪙 Решка",callback_data="coin_tail")],
        [InlineKeyboardButton(text="⬅️",callback_data="custom_games")]])
    await c.message.edit_text(f"🪙 Ставка: <b>{u['bet']:.2f}$</b>\n🎯 x{COIN_MULT}",parse_mode="HTML",reply_markup=kb)
    await c.answer()

@router.callback_query(F.data.startswith("coin_"))
async def cb_coin_play(c: CallbackQuery):
    ch = c.data.split("_",1)[1]; u = get_user(c.from_user.id); bet = u["bet"]
    if u["balance"]<bet: await c.answer("❌",show_alert=True); return
    await c.answer()
    update_user(c.from_user.id,balance=u["balance"]-bet,turnover=u["turnover"]+bet,games=u["games"]+1)
    for f in ["🦅...","🪙...","🦅...","🪙..."]:
        try: await c.message.edit_text(f)
        except: pass
        await asyncio.sleep(0.4)
    res = random.choice(["eagle","tail"]); rt = "🦅 Орёл" if res=="eagle" else "🪙 Решка"
    u = get_user(c.from_user.id)
    if ch==res:
        pr = bet*COIN_MULT; update_user(c.from_user.id,balance=u["balance"]+pr,wins=u["wins"]+1)
        nu = get_user(c.from_user.id)
        await c.message.edit_text(f"🎉 <b>ПОБЕДА!</b>\n\n{rt}\n💵 {bet:.2f}$\n🎯 x{COIN_MULT}\n\n💰 +{pr:.2f}$\n💵 {nu['balance']:.2f}$",parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔁",callback_data="cg_coin")],[InlineKeyboardButton(text="🎨",callback_data="custom_games")]]))
    else:
        nu = get_user(c.from_user.id)
        await c.message.edit_text(f"💀 <b>Проигрыш</b>\n\n{rt}\n💵 {bet:.2f}$\n\n📉 -{bet:.2f}$\n💵 {nu['balance']:.2f}$",parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔁",callback_data="cg_coin")],[InlineKeyboardButton(text="🎨",callback_data="custom_games")]]))

@router.callback_query(F.data=="cg_slots")
async def cb_slots(c: CallbackQuery):
    u = get_user(c.from_user.id); bet = u["bet"]
    if u["balance"]<bet: await c.answer("❌",show_alert=True); return
    await c.answer()
    update_user(c.from_user.id,balance=u["balance"]-bet,turnover=u["turnover"]+bet,games=u["games"]+1)
    for _ in range(6):
        fr = " | ".join(random.choice(SLOT_SYMBOLS) for _ in range(3))
        try: await c.message.edit_text(f"🎰 {fr}")
        except: pass
        await asyncio.sleep(0.35)
    r = [random.choice(SLOT_SYMBOLS) for _ in range(3)]; line = " | ".join(r)
    m = 0.0
    if r[0]==r[1]==r[2]: m = SLOT_MULT.get(r[0],0)
    elif r[0]==r[1] or r[1]==r[2] or r[0]==r[2]: m = SLOT_PAIR_MULT
    u = get_user(c.from_user.id)
    if m>0:
        pr = bet*m; update_user(c.from_user.id,balance=u["balance"]+pr,wins=u["wins"]+1)
        nu = get_user(c.from_user.id)
        await c.message.edit_text(f"🎉 x{m}\n\n🎰 {line}\n💰 +{pr:.2f}$\n💵 {nu['balance']:.2f}$",parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔁",callback_data="cg_slots")],[InlineKeyboardButton(text="🎨",callback_data="custom_games")]]))
    else:
        nu = get_user(c.from_user.id)
        await c.message.edit_text(f"💀\n\n🎰 {line}\n📉 -{bet:.2f}$\n💵 {nu['balance']:.2f}$",parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔁",callback_data="cg_slots")],[InlineKeyboardButton(text="🎨",callback_data="custom_games")]]))

@router.callback_query(F.data=="cg_wheel")
async def cb_wheel(c: CallbackQuery):
    u = get_user(c.from_user.id); bet = u["bet"]
    if u["balance"]<bet: await c.answer("❌",show_alert=True); return
    await c.answer()
    update_user(c.from_user.id,balance=u["balance"]-bet,turnover=u["turnover"]+bet,games=u["games"]+1)
    for f in ["🎡...","🎡 .","🎡 ..","🎡 ...","🎡 ...."]:
        try: await c.message.edit_text(f)
        except: pass
        await asyncio.sleep(0.3)
    r = random.random()*100; acc=0.0; nm,m = WHEEL_SEGMENTS[0][0],WHEEL_SEGMENTS[0][1]
    for sn,sm,sw in WHEEL_SEGMENTS:
        acc += sw
        if r<=acc: nm,m = sn,sm; break
    u = get_user(c.from_user.id)
    if m>0:
        pr = bet*m; update_user(c.from_user.id,balance=u["balance"]+pr,wins=u["wins"]+1)
        nu = get_user(c.from_user.id)
        await c.message.edit_text(f"🎉 {nm}\n💰 +{pr:.2f}$\n💵 {nu['balance']:.2f}$",parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔁",callback_data="cg_wheel")],[InlineKeyboardButton(text="🎨",callback_data="custom_games")]]))
    else:
        nu = get_user(c.from_user.id)
        await c.message.edit_text(f"💀 {nm}\n📉 -{bet:.2f}$\n💵 {nu['balance']:.2f}$",parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔁",callback_data="cg_wheel")],[InlineKeyboardButton(text="🎨",callback_data="custom_games")]]))

@router.callback_query(F.data=="cg_mines")
async def cb_mines(c: CallbackQuery, st: FSMContext):
    u = get_user(c.from_user.id)
    if u["balance"]<u["bet"]: await c.answer("❌",show_alert=True); return
    await c.answer(); bet = u["bet"]
    update_user(c.from_user.id,balance=u["balance"]-bet,turnover=u["turnover"]+bet,games=u["games"]+1)
    mn = random.sample(range(MINES_GRID*MINES_GRID),MINES_COUNT)
    await st.update_data(mines=mn,opened=[],bet=bet); await st.set_state(States.mines_game)
    kb = InlineKeyboardBuilder()
    for i in range(MINES_GRID*MINES_GRID): kb.button(text="⬜",callback_data=f"mopen_{i}")
    kb.button(text=f"💰 Забрать {bet:.2f}$",callback_data="mcashout")
    kb.adjust(*([MINES_GRID]*MINES_GRID),1)
    await c.message.edit_text(f"💣 <b>Мины</b>\n💵 {bet:.2f}$\n💣 Мин: {MINES_COUNT}\n🎯 x1.00",parse_mode="HTML",reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("mopen_"), States.mines_game)
async def cb_mines_open(c: CallbackQuery, st: FSMContext):
    d = await st.get_data(); mn = d.get("mines",[]); op = d.get("opened",[]); bet = d.get("bet",0)
    idx = int(c.data.split("_",1)[1])
    if idx in op: await c.answer("Уже"); return
    if idx in mn:
        await st.clear(); nu = get_user(c.from_user.id)
        await c.message.edit_text(f"💥 ВЗРЫВ\n📉 -{bet:.2f}$\n💵 {nu['balance']:.2f}$",parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔁",callback_data="cg_mines")],[InlineKeyboardButton(text="🎨",callback_data="custom_games")]]))
        await c.answer("💥"); return
    op.append(idx); await st.update_data(opened=op)
    m = MINES_MULTS[min(len(op),len(MINES_MULTS)-1)]; await c.answer(f"✅ x{m:.2f}")
    kb = InlineKeyboardBuilder()
    for i in range(MINES_GRID*MINES_GRID): kb.button(text="✅" if i in op else "⬜",callback_data=f"mopen_{i}")
    pr = bet*m; kb.button(text=f"💰 Забрать {pr:.2f}$",callback_data="mcashout")
    kb.adjust(*([MINES_GRID]*MINES_GRID),1)
    await c.message.edit_text(f"💣 ✅ {len(op)}\n🎯 x{m:.2f}\n💰 {pr:.2f}$",parse_mode="HTML",reply_markup=kb.as_markup())

@router.callback_query(F.data=="mcashout", States.mines_game)
async def cb_mines_cash(c: CallbackQuery, st: FSMContext):
    d = await st.get_data(); op = d.get("opened",[]); bet = d.get("bet",0)
    if not op: await c.answer("Открой",show_alert=True); return
    m = MINES_MULTS[min(len(op),len(MINES_MULTS)-1)]; pr = bet*m; await st.clear()
    u = get_user(c.from_user.id); update_user(c.from_user.id,balance=u["balance"]+pr,wins=u["wins"]+1)
    nu = get_user(c.from_user.id)
    await c.message.edit_text(f"🎉 ЗАБРАЛ x{m:.2f}\n💰 +{pr:.2f}$\n💵 {nu['balance']:.2f}$",parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔁",callback_data="cg_mines")],[InlineKeyboardButton(text="🎨",callback_data="custom_games")]]))

@router.callback_query(F.data=="cg_doors")
async def cb_doors(c: CallbackQuery):
    u = get_user(c.from_user.id)
    if u["balance"]<u["bet"]: await c.answer("❌",show_alert=True); return
    await c.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚪 1",callback_data="door_0"),InlineKeyboardButton(text="🚪 2",callback_data="door_1"),
         InlineKeyboardButton(text="🚪 3",callback_data="door_2"),InlineKeyboardButton(text="🚪 4",callback_data="door_3")],
        [InlineKeyboardButton(text="⬅️",callback_data="custom_games")]])
    await c.message.edit_text(f"🚪 x{DOORS_WIN_MULT}\n💵 {u['bet']:.2f}$",parse_mode="HTML",reply_markup=kb)

@router.callback_query(F.data.startswith("door_"))
async def cb_doors_play(c: CallbackQuery):
    u = get_user(c.from_user.id); bet = u["bet"]
    if u["balance"]<bet: await c.answer("❌",show_alert=True); return
    ch = int(c.data.split("_",1)[1]); await c.answer()
    update_user(c.from_user.id,balance=u["balance"]-bet,turnover=u["turnover"]+bet,games=u["games"]+1)
    for i in range(4):
        f = "  ".join(["🚪" if j!=ch else "🎁" for j in range(4)])
        try: await c.message.edit_text(f"🚪 {f}")
        except: pass
        await asyncio.sleep(0.3)
    w = random.random()<DOORS_WIN_CHANCE; u = get_user(c.from_user.id)
    if w:
        pr = bet*DOORS_WIN_MULT; update_user(c.from_user.id,balance=u["balance"]+pr,wins=u["wins"]+1)
        nu = get_user(c.from_user.id)
        await c.message.edit_text(f"🎉 №{ch+1} 🎁\n💰 +{pr:.2f}$\n💵 {nu['balance']:.2f}$",parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔁",callback_data="cg_doors")],[InlineKeyboardButton(text="🎨",callback_data="custom_games")]]))
    else:
        nu = get_user(c.from_user.id)
        await c.message.edit_text(f"💀 №{ch+1}\n📉 -{bet:.2f}$\n💵 {nu['balance']:.2f}$",parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔁",callback_data="cg_doors")],[InlineKeyboardButton(text="🎨",callback_data="custom_games")]]))

@router.callback_query(F.data=="cg_tower")
async def cb_tower(c: CallbackQuery, st: FSMContext):
    u = get_user(c.from_user.id)
    if u["balance"]<u["bet"]: await c.answer("❌",show_alert=True); return
    await c.answer(); bet = u["bet"]
    update_user(c.from_user.id,balance=u["balance"]-bet,turnover=u["turnover"]+bet,games=u["games"]+1)
    await st.update_data(floor=0,bet=bet); await st.set_state(States.tower_game)
    await c.message.edit_text(f"🏗 0/{TOWER_MAX_FLOOR}\n🎯 x1.00\n⚠️ {int(TOWER_CRASH_CHANCE*100)}%\n💵 {bet:.2f}$",parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🧱",callback_data="tower_up")],[InlineKeyboardButton(text="💰",callback_data="tower_cashout")]]))

@router.callback_query(F.data=="tower_up", States.tower_game)
async def cb_tower_up(c: CallbackQuery, st: FSMContext):
    d = await st.get_data(); fl = d.get("floor",0); bet = d.get("bet",0)
    if fl>=TOWER_MAX_FLOOR: await c.answer("Макс",show_alert=True); return
    if random.random()<TOWER_CRASH_CHANCE:
        await st.clear(); nu = get_user(c.from_user.id)
        await c.message.edit_text(f"💥 ОБРУШЕНИЕ\nЭтаж {fl}\n📉 -{bet:.2f}$\n💵 {nu['balance']:.2f}$",parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔁",callback_data="cg_tower")],[InlineKeyboardButton(text="🎨",callback_data="custom_games")]]))
        await c.answer("💥"); return
    fl+=1; await st.update_data(floor=fl)
    m = TOWER_MULTS[min(fl-1,len(TOWER_MULTS)-1)]; pr = bet*m; await c.answer(f"x{m:.2f}")
    await c.message.edit_text(f"🏗 {fl}/{TOWER_MAX_FLOOR}\n🎯 x{m:.2f}\n💰 {pr:.2f}$\n⚠️ {int(TOWER_CRASH_CHANCE*100)}%",parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🧱",callback_data="tower_up")],[InlineKeyboardButton(text="💰",callback_data="tower_cashout")]]))

@router.callback_query(F.data=="tower_cashout", States.tower_game)
async def cb_tower_cash(c: CallbackQuery, st: FSMContext):
    d = await st.get_data(); fl = d.get("floor",0); bet = d.get("bet",0)
    if fl==0: await c.answer("Построй",show_alert=True); return
    m = TOWER_MULTS[min(fl-1,len(TOWER_MULTS)-1)]; pr = bet*m; await st.clear()
    u = get_user(c.from_user.id); update_user(c.from_user.id,balance=u["balance"]+pr,wins=u["wins"]+1)
    nu = get_user(c.from_user.id)
    await c.message.edit_text(f"🎉 {fl} этажей, x{m:.2f}\n💰 +{pr:.2f}$\n💵 {nu['balance']:.2f}$",parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔁",callback_data="cg_tower")],[InlineKeyboardButton(text="🎨",callback_data="custom_games")]]))

@router.callback_query(F.data=="cg_ball")
async def cb_ball(c: CallbackQuery):
    u = get_user(c.from_user.id)
    if u["balance"]<0: await c.answer("В долгу",show_alert=True); return
    await c.message.edit_text(f"🎈 <b>Шарик</b>\n💵 {u['bet']:.2f}$",parse_mode="HTML",reply_markup=menu_ball())
    await c.answer()

@router.callback_query(F.data.startswith("ball_"))
async def cb_ball_play(c: CallbackQuery):
    lb = c.data.split("_",1)[1]
    f = next((b for b in BALL_BETS if b[0]==lb),None)
    if not f: await c.answer("Нет",show_alert=True); return
    _,m,ch,em = f
    u = get_user(c.from_user.id); bet = u["bet"]
    if u["balance"]<bet: await c.answer("❌",show_alert=True); return
    await c.answer()
    update_user(c.from_user.id,balance=u["balance"]-bet,turnover=u["turnover"]+bet,games=u["games"]+1)
    for fr in [f"{em} {em} {em}",f"  {em} {em}  ",f"    {em}    ",f"  {em} {em}  ",f"{em} {em} {em}"]:
        try: await c.message.edit_text(f"{em} x{m:.0f}\n💵 {bet:.2f}$\n🎯 {ch*100:.2f}%\n\n{fr}",parse_mode="HTML")
        except: pass
        await asyncio.sleep(0.4)
    w = random.random()<ch; u = get_user(c.from_user.id)
    if w:
        pr = bet*m; update_user(c.from_user.id,balance=u["balance"]+pr,wins=u["wins"]+1)
        nu = get_user(c.from_user.id)
        await c.message.edit_text(f"🎉 {em} x{m:.0f}\n💰 +{pr:.2f}$\n💵 {nu['balance']:.2f}$",parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔁",callback_data="cg_ball")],[InlineKeyboardButton(text="🎨",callback_data="custom_games")]]))
    else:
        nu = get_user(c.from_user.id)
        await c.message.edit_text(f"💀 {em} x{m:.0f}\n📉 -{bet:.2f}$\n💵 {nu['balance']:.2f}$",parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔁",callback_data="cg_ball")],[InlineKeyboardButton(text="🎨",callback_data="custom_games")]]))

def check_win(gk, code, val):
    if gk=="dice":
        if code=="even": return val%2==0
        if code=="odd": return val%2==1
        if code=="lt": return val<3.5
        if code=="gt": return val>3.5
        if code in ("eq1","eq2","eq3","eq4","eq5","eq6"): return val==int(code[-1])
        if code=="ladder": return val in (2,3,4,5)
    if gk=="football":
        if code=="center": return val==3
        if code=="corner": return val==5
        if code=="post": return val==4
        if code=="any": return val in (3,4,5)
        if code=="hit": return val in (2,4)
        if code=="miss": return val in (1,2)
    if gk=="basketball":
        if code=="clean": return val==5
        if code=="spin": return val==4
        if code=="stuck": return val==3
        if code=="bounce": return val==2
        if code=="any": return val in (4,5)
        if code=="miss": return val in (1,2,3)
    if gk=="darts":
        if code=="center": return val==6
        if code=="bounce": return val==5
        if code=="red": return val in (2,4)
        if code=="white": return val in (1,3)
        if code=="any": return val in (1,2,3,4)
    if gk=="bowling":
        if code=="strike": return val==6
        if code=="miss": return val==1
        if code=="one": return val==2
        if code=="three": return val==3
        if code=="four": return val==4
        if code=="five": return val==5
        if code=="ns": return val in (2,3,4,5)
        if code=="nm": return val in (2,3,4,5,6)
    if gk=="slots":
        def dec(v):
            v-=1; return ((v>>4)&3,(v>>2)&3,v&3)
        p = dec(val); s = p[0]==p[1]==p[2]; d = len(set(p))==3
        if code=="s777": return val==64
        if code=="sbbb": return val==1
        if code=="slll": return val==43
        if code=="sggg": return val==22
        if code=="any3": return s
        if code=="uniq": return d
    return False

@router.callback_query(F.data=="profile")
async def cb_prof(c: CallbackQuery):
    u = get_user(c.from_user.id)
    debt = f"\n⚠️ Долг: <b>{abs(u['balance']):.2f}$</b>" if u["balance"]<0 else ""
    await c.message.edit_text(f"👤 <b>Профиль</b>\n\n🆔 <code>{c.from_user.id}</code>\n📛 @{u.get('username') or '—'}\n\n"
        f"💵 {u['balance']:.2f}$</b>{debt}\n📊 Оборот: <b>{u['turnover']:.2f}$</b>\n💎 {u['rake_balance']:.2f}$\n"
        f"💵 Ставка: <b>{u['bet']:.2f}$</b>\n🎮 {u['games']}\n🏆 {u['wins']}",parse_mode="HTML",reply_markup=back("moremenu"))
    await c.answer()

@router.callback_query(F.data=="rake")
async def cb_rake(c: CallbackQuery):
    u = get_user(c.from_user.id)
    can = u["turnover"]>=RAKE_UNLOCK_THRESHOLD and u["rake_balance"]>=RAKE_CLAIM_MIN
    kb = InlineKeyboardBuilder()
    if can: kb.button(text=f"💸 {u['rake_balance']:.2f}$",callback_data="rake_claim")
    else: kb.button(text="🔒",callback_data="noop")
    kb.button(text="⬅️",callback_data="moremenu"); kb.adjust(1)
    await c.message.edit_text(f"💎 <b>Рейк</b>\n📊 {u['turnover']:.2f}$\n💎 {u['rake_balance']:.2f}$\n📈 Макс {RAKE_MAX:.0f}$",
                              parse_mode="HTML",reply_markup=kb.as_markup())
    await c.answer()

@router.callback_query(F.data=="rake_claim")
async def cb_rake_cl(c: CallbackQuery):
    u = get_user(c.from_user.id)
    if u["turnover"]<RAKE_UNLOCK_THRESHOLD: await c.answer("Отыграй",show_alert=True); return
    if u["rake_balance"]<RAKE_CLAIM_MIN: await c.answer("Мин",show_alert=True); return
    amt = u["rake_balance"]; update_user(c.from_user.id,balance=u["balance"]+amt,rake_balance=0.0)
    await c.answer(f"+{amt:.2f}$",show_alert=True); await cb_rake(c)

@router.callback_query(F.data=="reserve")
async def cb_res(c: CallbackQuery):
    u = get_user(c.from_user.id); can = u["turnover"]>=RAKE_UNLOCK_THRESHOLD
    kb = InlineKeyboardBuilder()
    if can: kb.button(text="🏦 10%",callback_data="reserve_claim")
    else: kb.button(text="🔒",callback_data="noop")
    kb.button(text="⬅️",callback_data="moremenu"); kb.adjust(1)
    await c.message.edit_text(f"🏦 {get_reserve():.2f}$",parse_mode="HTML",reply_markup=kb.as_markup()); await c.answer()

@router.callback_query(F.data=="reserve_claim")
async def cb_res_cl(c: CallbackQuery):
    u = get_user(c.from_user.id)
    if u["turnover"]<RAKE_UNLOCK_THRESHOLD: await c.answer("Оборот",show_alert=True); return
    r = get_reserve()
    if r<=0: await c.answer("Пусто",show_alert=True); return
    amt = round(r*0.1,2) or r
    set_reserve(r-amt); update_user(c.from_user.id,balance=u["balance"]+amt,reserve_claimed=u["reserve_claimed"]+amt)
    await c.answer(f"+{amt:.2f}$",show_alert=True); await cb_res(c)

@router.callback_query(F.data=="promo")
async def cb_promo(c: CallbackQuery, st: FSMContext):
    await st.set_state(States.enter_promo); await c.message.edit_text(TEXT_PROMO_ENTER,parse_mode="HTML"); await c.answer()

@router.message(States.enter_promo)
async def process_promo(m: Message, st: FSMContext):
    code = (m.text or "").strip().upper()
    if code.lower()=="отмена": await st.clear(); await m.answer("Отменено."); return
    pr = load(PROMOS_FILE)
    if code not in pr: await m.answer("❌ Нет."); await st.clear(); return
    p = pr[code]
    if p.get("used_by") and m.from_user.id in p["used_by"]: await m.answer("❌ Уже."); await st.clear(); return
    if p.get("limit",0)>0 and len(p.get("used_by",[]))>=p["limit"]: await m.answer("❌ Лимит."); await st.clear(); return
    amt = float(p["amount"]); u = get_user(m.from_user.id)
    update_user(m.from_user.id,balance=u["balance"]+amt)
    p.setdefault("used_by",[]).append(m.from_user.id); pr[code]=p; save(PROMOS_FILE,pr)
    await m.answer(f"✅ +{amt:.2f}$",parse_mode="HTML"); await st.clear()

@router.callback_query(F.data=="adm_close")
async def cb_ac(c: CallbackQuery):
    if not is_admin(c): await c.answer("Нет",show_alert=True); return
    await c.message.edit_text("Закрыто.",reply_markup=menu_main(get_user(c.from_user.id))); await c.answer()

@router.callback_query(F.data=="adm_back")
async def cb_ab(c: CallbackQuery, st: FSMContext):
    if not is_admin(c): await c.answer("Нет",show_alert=True); return
    await st.clear(); await c.message.edit_text(f"👑 {get_reserve():.2f}$",parse_mode="HTML",reply_markup=menu_admin()); await c.answer()

@router.callback_query(F.data=="adm_users")
async def cb_au(c: CallbackQuery):
    if not is_admin(c): await c.answer("Нет",show_alert=True); return
    db = load(DB_FILE)
    if not db: await c.message.edit_text("Пусто",reply_markup=menu_admin()); await c.answer(); return
    lines = [f"👥 <b>Игроки</b> ({len(db)}):\n"]
    for uid,d in list(db.items())[:50]:
        lines.append(f"• <code>{uid}</code> @{d.get('username') or '—'} — <b>{d.get('balance',0):.2f}$</b>")
    await c.message.edit_text("\n".join(lines),parse_mode="HTML",reply_markup=menu_admin()); await c.answer()

@router.callback_query(F.data=="adm_promo_new")
async def cb_apn(c: CallbackQuery, st: FSMContext):
    if not is_admin(c): await c.answer("Нет",show_alert=True); return
    await st.set_state(States.admin_promo_name)
    await c.message.edit_text("🎁 Название промо:",parse_mode="HTML"); await c.answer()

@router.message(States.admin_promo_name)
async def apn(m: Message, st: FSMContext):
    if not is_admin(m): await st.clear(); return
    t = (m.text or "").strip()
    if t.lower()=="отмена": await st.clear(); await m.answer("Отменено.",reply_markup=menu_admin()); return
    if not t or " " in t: await m.answer("❌ Без пробелов."); return
    await st.update_data(promo_name=t.upper()); await st.set_state(States.admin_promo_amount)
    await m.answer("💰 Сумма:")

@router.message(States.admin_promo_amount)
async def apa(m: Message, st: FSMContext):
    if not is_admin(m): await st.clear(); return
    t = (m.text or "").strip()
    if t.lower()=="отмена": await st.clear(); await m.answer("Отменено.",reply_markup=menu_admin()); return
    try: amt = float(t.replace(",","."))
    except: await m.answer("❌"); return
    if amt<=0: await m.answer("❌"); return
    await st.update_data(promo_amount=amt); await st.set_state(States.admin_promo_limit)
    await m.answer("🔢 Лимит (0=∞):")

@router.message(States.admin_promo_limit)
async def apl(m: Message, st: FSMContext):
    if not is_admin(m): await st.clear(); return
    t = (m.text or "").strip()
    if t.lower()=="отмена": await st.clear(); await m.answer("Отменено.",reply_markup=menu_admin()); return
    try: lim = int(t)
    except: await m.answer("❌"); return
    d = await st.get_data(); code = d["promo_name"]; amt = d["promo_amount"]
    pr = load(PROMOS_FILE)
    if code in pr: await m.answer("Уже есть"); await st.set_state(States.admin_promo_name); return
    pr[code] = {"amount":amt,"limit":lim,"used_by":[],"created":datetime.now().isoformat()}
    save(PROMOS_FILE,pr); await st.clear()
    await m.answer(f"✅ {code} — {amt}$ · {lim if lim else '∞'}",reply_markup=menu_admin())

@router.callback_query(F.data=="adm_promo_list")
async def cb_apl(c: CallbackQuery):
    if not is_admin(c): await c.answer("Нет",show_alert=True); return
    pr = load(PROMOS_FILE)
    if not pr: t = "Пусто"
    else:
        lines = ["📋 <b>Промо</b>\n"]
        for code,p in pr.items():
            u_ = len(p.get("used_by",[])); l = p.get("limit",0)
            lines.append(f"• <b>{code}</b> — {p['amount']}$ · {u_}/{l if l else '∞'}")
        t = "\n".join(lines)
    await c.message.edit_text(t,parse_mode="HTML",reply_markup=menu_admin()); await c.answer()

@router.callback_query(F.data=="adm_give")
async def cb_ag(c: CallbackQuery, st: FSMContext):
    if not is_admin(c): await c.answer("Нет",show_alert=True); return
    await st.set_state(States.admin_give_user)
    await c.message.edit_text("💵 Юзер/имя/ID:",parse_mode="HTML"); await c.answer()

@router.message(States.admin_give_user)
async def agu(m: Message, st: FSMContext):
    if not is_admin(m): await st.clear(); return
    t = (m.text or "").strip()
    if t.lower()=="отмена": await st.clear(); await m.answer("Отменено.",reply_markup=menu_admin()); return
    uid, d = find_user(t)
    if uid is None: await m.answer(f"❌ «{t}» не найден."); return
    await st.update_data(target_uid=uid,target_uname=t); await st.set_state(States.admin_give_amount)
    await m.answer(f"👤 <code>{uid}</code>\n💵 {d['balance']:.2f}$\n\nСумма:",parse_mode="HTML")

@router.message(States.admin_give_amount)
async def aga(m: Message, st: FSMContext):
    if not is_admin(m): await st.clear(); return
    t = (m.text or "").strip()
    if t.lower()=="отмена": await st.clear(); await m.answer("Отменено.",reply_markup=menu_admin()); return
    try: amt = float(t.replace(",","."))
    except: await m.answer("❌"); return
    if amt<=0: await m.answer("❌"); return
    d = await st.get_data(); uid = d["target_uid"]; u = get_user(uid)
    update_user(uid,balance=u["balance"]+amt); await st.clear()
    await m.answer(f"✅ {uid}: +{amt:.2f}$\n💵 {u['balance']+amt:.2f}$",parse_mode="HTML",reply_markup=menu_admin())
    try: await m.bot.send_message(uid,f"💰 +{amt:.2f}$")
    except: pass

@router.callback_query(F.data=="adm_take")
async def cb_at(c: CallbackQuery, st: FSMContext):
    if not is_admin(c): await c.answer("Нет",show_alert=True); return
    await st.set_state(States.admin_take_user)
    await c.message.edit_text("💸 Юзер/имя/ID:",parse_mode="HTML"); await c.answer()

@router.message(States.admin_take_user)
async def atu(m: Message, st: FSMContext):
    if not is_admin(m): await st.clear(); return
    t = (m.text or "").strip()
    if t.lower()=="отмена": await st.clear(); await m.answer("Отменено.",reply_markup=menu_admin()); return
    uid, d = find_user(t)
    if uid is None: await m.answer(f"❌ «{t}» не найден."); return
    await st.update_data(target_uid=uid,target_uname=t); await st.set_state(States.admin_take_amount)
    await m.answer(f"👤 {uid}\n💵 {d['balance']:.2f}$\n\nСумма:",parse_mode="HTML")

@router.message(States.admin_take_amount)
async def ata(m: Message, st: FSMContext):
    if not is_admin(m): await st.clear(); return
    t = (m.text or "").strip()
    if t.lower()=="отмена": await st.clear(); await m.answer("Отменено.",reply_markup=menu_admin()); return
    try: amt = float(t.replace(",","."))
    except: await m.answer("❌"); return
    if amt<=0: await m.answer("❌"); return
    d = await st.get_data(); uid = d["target_uid"]; u = get_user(uid)
    nb = u["balance"]-amt; update_user(uid,balance=nb); await st.clear()
    await m.answer(f"✅ {uid}: -{amt:.2f}$\n💵 {nb:.2f}$"+("\n⚠️ В минусе." if nb<0 else ""),parse_mode="HTML",reply_markup=menu_admin())

@router.callback_query(F.data=="adm_reserve")
async def cb_ar(c: CallbackQuery):
    if not is_admin(c): await c.answer("Нет",show_alert=True); return
    await c.message.edit_text(f"🏦 {get_reserve():.2f}$",parse_mode="HTML",reply_markup=menu_admin_reserve()); await c.answer()

@router.callback_query(F.data=="adm_res_add")
async def cb_ara(c: CallbackQuery, st: FSMContext):
    if not is_admin(c): await c.answer("Нет",show_alert=True); return
    await st.update_data(reserve_action="add"); await st.set_state(States.admin_reserve_amount)
    await c.message.edit_text("➕ Сумма:"); await c.answer()

@router.callback_query(F.data=="adm_res_take")
async def cb_art(c: CallbackQuery, st: FSMContext):
    if not is_admin(c): await c.answer("Нет",show_alert=True); return
    await st.update_data(reserve_action="take"); await st.set_state(States.admin_reserve_amount)
    await c.message.edit_text("➖ Сумма:"); await c.answer()

@router.message(States.admin_reserve_amount)
async def ara(m: Message, st: FSMContext):
    if not is_admin(m): await st.clear(); return
    t = (m.text or "").strip()
    if t.lower()=="отмена": await st.clear(); await m.answer("Отменено.",reply_markup=menu_admin()); return
    try: amt = float(t.replace(",","."))
    except: await m.answer("❌"); return
    if amt<=0: await m.answer("❌"); return
    d = await st.get_data(); act = d.get("reserve_action"); r = get_reserve()
    if act=="add": set_reserve(r+amt); await m.answer(f"🏦 +{amt:.2f}$\n{r+amt:.2f}$",parse_mode="HTML",reply_markup=menu_admin())
    else: set_reserve(r-amt); await m.answer(f"🏦 -{amt:.2f}$\n{max(0,r-amt):.2f}$",parse_mode="HTML",reply_markup=menu_admin())
    await st.clear()

@router.callback_query(F.data=="adm_broadcast")
async def cb_abr(c: CallbackQuery, st: FSMContext):
    if not is_admin(c): await c.answer("Нет",show_alert=True); return
    await st.set_state(States.admin_broadcast)
    await c.message.edit_text("📢 Текст (или <b>отмена</b>):",parse_mode="HTML"); await c.answer()

@router.message(States.admin_broadcast)
async def abr(m: Message, st: FSMContext):
    if not is_admin(m): await st.clear(); return
    t = (m.text or "").strip()
    if t.lower()=="отмена": await st.clear(); await m.answer("Отменено.",reply_markup=menu_admin()); return
    if not t: await m.answer("❌"); return
    db = load(DB_FILE); tot = len(db); s=0; f=0
    wt = await m.answer(f"📢 0/{tot}")
    for i,u_ in enumerate(db.keys(),1):
        try: await m.bot.send_message(int(u_),t,parse_mode="HTML"); s+=1
        except: f+=1
        if i%10==0 or i==tot:
            try: await wt.edit_text(f"📢 {i}/{tot}")
            except: pass
        await asyncio.sleep(0.05)
    await st.clear()
    await m.answer(f"✅ {s} ок, {f} ошибок, всего {tot}",reply_markup=menu_admin())

@router.callback_query(F.data=="adm_punish")
async def cb_ap(c: CallbackQuery, st: FSMContext):
    if not is_admin(c): await c.answer("Нет",show_alert=True); return
    await st.set_state(States.admin_punish_user)
    await c.message.edit_text("⚖️ Юзер/имя/ID:",parse_mode="HTML"); await c.answer()

@router.message(States.admin_punish_user)
async def apu(m: Message, st: FSMContext):
    if not is_admin(m): await st.clear(); return
    t = (m.text or "").strip()
    if t.lower()=="отмена": await st.clear(); await m.answer("Отменено.",reply_markup=menu_admin()); return
    uid, d = find_user(t)
    if uid is None: await m.answer(f"❌"); return
    await st.update_data(target_uid=uid); await st.set_state(States.admin_punish_count)
    await m.answer(f"👤 {uid}\nСколько работ? (написать <b>{WORK_WORD}</b> N раз)",parse_mode="HTML")

@router.message(States.admin_punish_count)
async def apc(m: Message, st: FSMContext):
    if not is_admin(m): await st.clear(); return
    t = (m.text or "").strip()
    if t.lower()=="отмена": await st.clear(); await m.answer("Отменено.",reply_markup=menu_admin()); return
    try: cnt = int(t)
    except: await m.answer("❌"); return
    if cnt<=0: await m.answer("❌"); return
    d = await st.get_data(); uid = d["target_uid"]
    update_user(uid,punish_remaining=cnt,punish_total=cnt); await st.clear()
    await m.answer(f"✅ {uid}: {cnt} работ",reply_markup=menu_admin())
    try: await m.bot.send_message(uid,f"⚖️ Работ: <b>{cnt}</b>\nНапиши <b>{WORK_WORD}</b> столько раз.",parse_mode="HTML")
    except: pass

async def send_top(m):
    db = load(DB_FILE)
    if not db: await m.answer("🏆 Пусто"); return
    pl = sorted(db.items(),key=lambda x:x[1].get("turnover",0),reverse=True)
    lines = ["🏆 <b>Топ</b>\n"]
    for i,(uid,d) in enumerate(pl[:10],1):
        md = {1:"🥇",2:"🥈",3:"🥉"}.get(i,f"{i}.")
        u_ = d.get("username") or d.get("first_name") or f"id{uid}"
        lines.append(f"{md} @{u_} — <b>{d.get('turnover',0):.2f}$</b>")
    await m.answer("\n".join(lines),parse_mode="HTML",reply_markup=back("moremenu"))

@router.callback_query(F.data=="top")
async def cb_top(c: CallbackQuery): await send_top(c.message); await c.answer()

@router.callback_query(F.data=="noop")
async def cb_noop(c: CallbackQuery): await c.answer()

@router.message(F.text)
async def catch_wrong(m: Message, st: FSMContext):
    cur = await st.get_state()
    if cur is not None: return
    u = get_user(m.from_user.id)
    if u.get("punish_remaining",0)>0 and m.text.strip().lower()!=WORK_WORD:
        code = f"0x{random.randint(0x1000,0xFFFF):X}"
        ln = random.choice([f"⚠️ SYNTAX ERROR {code}\n",f"⚠️ SEGMENTATION FAULT {code}\n",
                           f"⚠️ RUNTIME ERROR {code}\n",f"⚠️ UNKNOWN EXCEPTION {code}\n",f"⚠️ SYSTEM FAILURE {code}\n"])
        gb = "".join(random.choices("!@#$%^&*()_+-=[]{}|;:,.<>?/\\~`0123456789ABCDEFabcdef",k=20))
        await m.answer(f"<code>{ln}\n{gb}\n{gb}</code>\n\n👉 <b>{WORK_WORD}</b>",parse_mode="HTML")

async def main():
    if VPN_PROXY:
        from aiogram.client.session.aiohttp import AiohttpSession
        s = AiohttpSession(proxy=VPN_PROXY); bot = Bot(token=BOT_TOKEN,session=s)
    else: bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(); dp.include_router(router)
    print("Red Cube DEMO запущен.")
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
