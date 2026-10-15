import asyncio, json, os, random, logging
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage

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

DIV = "━━━━━━━━━━━━━━━━━━"

SLOT_SYMBOLS = ["🍒","🍋","🍊","🍇","💎","7️⃣"]
SLOT_MULT = {"🍒":3.0,"🍋":5.0,"🍊":7.0,"🍇":10.0,"💎":25.0,"7️⃣":50.0}
SLOT_PAIR_MULT = 1.2
WHEEL_SEGMENTS = [("Пусто",0.0,63.0),("x1.5",1.5,18.0),("x2",2.0,10.0),("x3",3.0,5.0),
                  ("x5",5.0,2.0),("x8",8.0,1.5),("x20",20.0,0.4),("x50",50.0,0.1)]
COIN_MULT = 1.9
MINES_GRID = 5
MINES_COUNT = 3
MINES_MULTS = [1.0,1.3,1.7,2.3,3.2,4.5,6.5,9.5,14.0,21.0,32.0,48.0,72.0,108.0,162.0,243.0,365.0,550.0,820.0,1230.0,1850.0,2770.0]
DOORS_WIN_PER_ROUND = 0.75
DOORS_MULTS = [1.5,2.2,3.3,5.0,7.5,11.0,17.0,25.0,38.0,57.0,85.0,130.0,195.0,290.0,435.0,650.0,975.0,1460.0,2190.0,3280.0]
TOWER_MAX_FLOOR = 10
TOWER_MULTS = [1.5,2.2,3.3,5.0,7.5,11.0,17.0,25.0,38.0,57.0]
TOWER_CRASH_CHANCE = 0.15
BALL_BETS = [
    ("x2",2.0,0.475,"🎈"),("x5",5.0,0.190,"🐟"),("x7",7.0,0.135,"🐬"),
    ("x10",10.0,0.095,"🐋"),("x15",15.0,0.063,"💸"),("x17",17.0,0.056,"💰"),
    ("x20",20.0,0.0475,"🎩"),("x30",30.0,0.032,"💼"),("x50",50.0,0.019,"💎"),
    ("x70",70.0,0.0135,"👑"),("x100",100.0,0.0095,"🚀"),
]

TEXT_START = (
    "🌟 <b>Red Cube Demo</b> 🌟\n" + DIV + "\n\n"
    "👋 Привет, <b>{name}</b>!\n"
    "Это <b>демо-бот</b> без реальных денег.\n\n"
    "💵 Баланс: <b>{balance:.2f}$</b>\n"
    "💎 Рейк: <b>{rake:.2f}$</b>\n\n"
    "<i>Напиши</i> <b>команды</b> <i>— увидишь список</i>"
)
TEXT_HELP = (
    "📋 <b>КОМАНДЫ БОТА</b>\n" + DIV + "\n\n"
    "🎮 <b>Основное:</b>\n"
    "• <b>меню</b> — главное меню\n"
    "• <b>играть</b> — список игр\n"
    "• <b>вб</b> — поставить всё\n"
    "• <b>отмена</b> — отменить действие\n\n"
    "💼 <b>Профиль:</b>\n"
    "• <b>профиль</b> — подробно о тебе\n"
    "• <b>баланс</b> — короткая сводка\n"
    "• <b>топ</b> — топ игроков\n\n"
    "💰 <b>Финансы:</b>\n"
    "• <b>рейк</b> — подарочный баланс\n"
    "• <b>забрать рейк</b> — вывести\n"
    "• <b>резерв</b> — общий резерв\n"
    "• <b>промо</b> — ввести код\n"
    "• <b>нк @юзер 0.5</b> — перевести\n\n"
    + DIV + "\n<i>Кнопки меню 👇</i>"
)
TEXT_GAMES = (
    "🎮 <b>ВЫБЕРИ ИГРУ</b>\n" + DIV + "\n\n"
    "🎲 Кубик · ⚽ Футбол · 🏀 Баскет\n"
    "🎳 Боулинг · 🎰 Слоты\n\n"
    "🎨 Или зайди в <b>Авторские</b>"
)
TEXT_WORK = "🛠 <b>РЕЖИМ ОТРАБОТКИ</b>\n" + DIV + "\n\nТы в долгу. Отработай кубиком."
TEXT_PROMO = "🎁 <b>ВВЕДИ ПРОМОКОД</b>\n" + DIV + "\n\n<i>Отмена — напиши</i> <b>отмена</b>"

logging.basicConfig(level=logging.INFO)
router = Router()

# ==================== БАЗА ====================
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
                 "is_admin":False,"bet":MIN_BET,"work_streak":0,
                 "punish_remaining":0,"punish_total":0,"registered":datetime.now().isoformat()}
        save(DB_FILE, db)
    else:
        ch=False
        if username and db[k].get("username")!=username.lstrip('@'):
            db[k]["username"]=username.lstrip('@'); ch=True
        if first_name and db[k].get("first_name")!=first_name:
            db[k]["first_name"]=first_name; ch=True
        for kk,vv in {"bet":MIN_BET,"work_streak":0,"punish_remaining":0,"punish_total":0,
                      "username":"","first_name":"","is_admin":False}.items():
            if kk not in db[k]: db[k][kk]=vv; ch=True
        if ch: save(DB_FILE, db)
    return db[k]

def update_user(uid, **kw):
    db = load(DB_FILE); k = str(uid)
    if k not in db:
        db[k] = {"username":"","first_name":"","balance":START_BALANCE,"rake_balance":0.0,
                 "turnover":0.0,"wins":0,"games":0,"is_admin":False,"bet":MIN_BET,
                 "work_streak":0,"punish_remaining":0,"punish_total":0}
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
    return load(DB_FILE).get(str(m.from_user.id),{}).get("is_admin",False)
def get_reserve():
    return float(load(RESERVE_FILE,{"amount":1000.0}).get("amount",1000.0))
def set_reserve(v):
    save(RESERVE_FILE,{"amount":max(0.0,float(v))})
def add_reserve(v):
    set_reserve(get_reserve()+v)

# ==================== ОПИСАНИЕ ====================
def describe_result(game_key, value):
    if game_key == "dice":
        return {1:"1️⃣ Единица",2:"2️⃣ Двойка",3:"3️⃣ Тройка",4:"4️⃣ Четвёрка",5:"5️⃣ Пятёрка",6:"6️⃣ Шестёрка"}.get(value,str(value))
    if game_key == "football":
        return {1:"🚫 Промах",2:"🥅 Удар об штангу",3:"⚽ Гол в центр",4:"⚽ Гол от штанги",5:"⚽ Гол в угол"}.get(value,str(value))
    if game_key == "basketball":
        return {1:"🚫 Промах",2:"🏀 Отскок",3:"🏀 Застрял",4:"🏀 Прокрут",5:"🏀 Чистый гол"}.get(value,str(value))
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

def check_win(gk, code, val):
    if gk=="dice":
        if code=="even": return val%2==0
        if code=="odd": return val%2==1
        if code=="lt": return val<3.5
        if code=="gt": return val>3.5
        if code in ("eq1","eq2","eq3","eq4","eq5","eq6"): return val==int(code[-1])
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

# ==================== СОСТОЯНИЯ ====================
class States(StatesGroup):
    new_bet=State(); promo=State(); admin_code=State()
    promo_name=State(); promo_amount=State(); promo_limit=State()
    give_user=State(); give_amount=State(); take_user=State(); take_amount=State()
    reserve_amount=State(); broadcast=State(); punish_user=State(); punish_count=State()
    work_guess=State(); mines=State(); tower=State(); doors=State()

# ==================== ИГРЫ ====================
GAMES = {
    "dice":{"emoji":"🎲","name":"Кубик","outcomes":[
        ("Чёт (x2)","even",2.0),("Нечет (x2)","odd",2.0),("Меньше (x2)","lt",2.0),("Больше (x2)","gt",2.0),
        ("1 (x6)","eq1",6.0),("2 (x6)","eq2",6.0),("3 (x6)","eq3",6.0),("4 (x6)","eq4",6.0),("5 (x6)","eq5",6.0),("6 (x6)","eq6",6.0)]},
    "football":{"emoji":"⚽","name":"Футбол","outcomes":[
        ("Гол в центр (x5)","center",5.0),("Гол в угол (x5)","corner",5.0),("Гол от штанги (x5)","post",5.0),
        ("Любой гол (x1.66)","any",1.66),("Удар об штангу (x2.5)","hit",2.5),("Промах (x2.5)","miss",2.5)]},
    "basketball":{"emoji":"🏀","name":"Баскетбол","outcomes":[
        ("Чистый гол (x5)","clean",5.0),("Прокрут (x2.5)","spin",2.5),("Застрял мяч (x5)","stuck",5.0),
        ("Любой гол (x2.5)","any",2.5),("Отскок (x5)","bounce",5.0),("Промах (x1.66)","miss",1.66)]},
    "bowling":{"emoji":"🎳","name":"Боулинг","outcomes":[
        ("Страйк (x6)","strike",6.0),("Промах (x6)","miss",6.0),("Сбита 1/6 (x6)","one",6.0),
        ("Сбито 3/6 (x6)","three",6.0),("Сбито 4/6 (x6)","four",6.0),("Сбито 5/6 (x6)","five",6.0),
        ("Без страйка (x1.44)","ns",1.44),("Без промаха (x1.44)","nm",1.44)]},
    "slots":{"emoji":"🎰","name":"Слоты","outcomes":[
        ("3 Семёрки (x64)","s777",64.0),("3 Лимона (x64)","slll",64.0),("3 Винограда (x64)","sggg",64.0),
        ("3 Бара (x64)","sbbb",64.0),("Любая комбинация (x16)","any3",16.0),("Уникальные (x2.66)","uniq",2.66)]},
}

# ==================== КЛАВИАТУРЫ ====================
def kb_main(u):
    kb = InlineKeyboardBuilder()
    kb.button(text="👛 Кошелёк",callback_data="wallet")
    if u["balance"]<0: kb.button(text="🛠 Отработать",callback_data="work")
    else: kb.button(text="🎮 Игры",callback_data="games")
    kb.button(text="≡ Меню",callback_data="more")
    kb.adjust(3); return kb.as_markup()

def kb_games():
    kb = InlineKeyboardBuilder()
    for k,g in GAMES.items(): kb.button(text=f"{g['emoji']} {g['name']}",callback_data=f"g_{k}")
    kb.button(text="🎨 Авторские",callback_data="custom")
    kb.button(text="✏️ Изменить ставку",callback_data="chbet")
    kb.adjust(3,2,1,1); return kb.as_markup()

def kb_outcomes(gk):
    g = GAMES[gk]; kb = InlineKeyboardBuilder()
    for label,code,mult in g["outcomes"]: kb.button(text=label,callback_data=f"o_{gk}_{code}")
    kb.button(text="⬅️ Назад",callback_data="games")
    kb.adjust(2,2,2,2,2,1); return kb.as_markup()

def kb_more():
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Профиль",callback_data="profile"); kb.button(text="💎 Рейк",callback_data="rake")
    kb.button(text="🏦 Резерв",callback_data="reserve"); kb.button(text="🎁 Промокод",callback_data="promo")
    kb.button(text="🏆 Топ",callback_data="top"); kb.button(text="⬅️ Назад",callback_data="main")
    kb.adjust(2,2,2,1); return kb.as_markup()

def kb_admin():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎁 Создать промо",callback_data="a_promo_new")
    kb.button(text="📋 Список промо",callback_data="a_promo_list")
    kb.button(text="💵 Выдать",callback_data="a_give")
    kb.button(text="💸 Забрать",callback_data="a_take")
    kb.button(text="🏦 Резерв",callback_data="a_reserve")
    kb.button(text="📢 Рассылка",callback_data="a_bcast")
    kb.button(text="⚖️ Наказать",callback_data="a_punish")
    kb.button(text="👥 Игроки",callback_data="a_users")
    kb.button(text="❌ Закрыть",callback_data="a_close")
    kb.adjust(1,1,2,1,1,1,1,1); return kb.as_markup()

def kb_admin_res():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить",callback_data="a_res_add")
    kb.button(text="➖ Убрать",callback_data="a_res_take")
    kb.button(text="⬅️ Назад",callback_data="a_back")
    kb.adjust(1); return kb.as_markup()

def kb_custom():
    kb = InlineKeyboardBuilder()
    kb.button(text="🪙 Монетка",callback_data="cg_coin")
    kb.button(text="🎰 Слоты 3x3",callback_data="cg_slots")
    kb.button(text="🎡 Колесо",callback_data="cg_wheel")
    kb.button(text="💣 Мины",callback_data="cg_mines")
    kb.button(text="🚪 4 двери (20 раундов)",callback_data="cg_doors")
    kb.button(text="🏗 Башня",callback_data="cg_tower")
    kb.button(text="🎈 Шарик",callback_data="cg_ball")
    kb.button(text="⬅️ Назад",callback_data="games")
    kb.adjust(1,1,1,1,1,1,1,1); return kb.as_markup()

def kb_ball():
    kb = InlineKeyboardBuilder()
    for label,_,_,emoji in BALL_BETS: kb.button(text=f"{emoji} {label}",callback_data=f"b_{label}")
    kb.button(text="⬅️ Назад",callback_data="custom")
    kb.adjust(3,3,3,2,1); return kb.as_markup()

def back(t="main"):
    kb = InlineKeyboardBuilder(); kb.button(text="⬅️ Назад",callback_data=t); return kb.as_markup()

# ==================== СТАРТ И КОМАНДЫ ====================
@router.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext = None):
    if state: await state.clear()
    u = get_user(m.from_user.id, m.from_user.username or "", m.from_user.first_name or "")
    await m.answer(TEXT_START.format(name=m.from_user.first_name,balance=u["balance"],rake=u["rake_balance"]),
                   parse_mode="HTML",reply_markup=kb_main(u))

@router.message(F.text.lower()=="команды")
async def cmd_help(m: Message):
    await m.answer(TEXT_HELP,parse_mode="HTML")

@router.message(F.text.lower()=="меню")
async def cmd_menu(m: Message, state: FSMContext = None):
    if state: await state.clear()
    u = get_user(m.from_user.id)
    await m.answer(
        f"🏠 <b>ГЛАВНОЕ МЕНЮ</b>\n{DIV}\n\n"
        f"💵 Баланс: <b>{u['balance']:.2f}$</b>\n"
        f"💵 Ставка: <b>{u['bet']:.2f}$</b>",
        parse_mode="HTML",reply_markup=kb_main(u))

@router.message(F.text.lower()=="играть")
async def cmd_play(m: Message, state: FSMContext = None):
    if state: await state.clear()
    u = get_user(m.from_user.id)
    if u["balance"]<0:
        await m.answer(TEXT_WORK,parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛠 Отработать",callback_data="work")]]))
        return
    await m.answer(TEXT_GAMES,parse_mode="HTML",reply_markup=kb_games())

@router.message(F.text.lower()=="вб")
async def cmd_vb(m: Message, state: FSMContext = None):
    if state: await state.clear()
    u = get_user(m.from_user.id)
    if u["balance"]<0: await m.answer("❌ Ты в долгу."); return
    if u["balance"]<MIN_BET: await m.answer(f"❌ Баланс мал: <b>{u['balance']:.2f}$</b>",parse_mode="HTML"); return
    update_user(m.from_user.id,bet=u["balance"])
    await m.answer(f"✅ <b>Ставка:</b> {u['balance']:.2f}$",parse_mode="HTML",reply_markup=kb_games())

@router.message(F.text.lower()=="профиль")
async def cmd_prof(m: Message):
    u = get_user(m.from_user.id)
    debt = f"\n⚠️ Долг: <b>{abs(u['balance']):.2f}$</b>" if u["balance"]<0 else ""
    punish = f"\n⚖️ Работ: <b>{u['punish_remaining']}</b>" if u.get("punish_remaining",0)>0 else ""
    await m.answer(
        f"👤 <b>ПРОФИЛЬ</b>\n{DIV}\n\n"
        f"🆔 ID: <code>{m.from_user.id}</code>\n"
        f"📛 Ник: @{u.get('username') or '—'}\n"
        f"📝 Имя: {u.get('first_name') or '—'}\n\n"
        f"💵 Баланс: <b>{u['balance']:.2f}$</b>{debt}\n"
        f"📊 Оборот: <b>{u['turnover']:.2f}$</b>\n"
        f"💎 Рейк: <b>{u['rake_balance']:.2f}$</b>\n"
        f"💵 Ставка: <b>{u['bet']:.2f}$</b>\n"
        f"🎮 Игр: <b>{u['games']}</b>\n"
        f"🏆 Побед: <b>{u['wins']}</b>{punish}\n\n"
        f"📅 {u['registered'][:10]}",
        parse_mode="HTML",reply_markup=back("main"))

@router.message(F.text.lower()=="баланс")
async def cmd_bal(m: Message):
    u = get_user(m.from_user.id)
    debt = f"\n⚠️ Долг: <b>{abs(u['balance']):.2f}$</b>" if u["balance"]<0 else ""
    await m.answer(
        f"💼 <b>БАЛАНС</b>\n{DIV}\n\n"
        f"💵 Игровой: <b>{u['balance']:.2f}$</b>{debt}\n"
        f"💎 Рейк: <b>{u['rake_balance']:.2f}$</b>",
        parse_mode="HTML",reply_markup=back("main"))

@router.message(F.text.lower()=="рейк")
async def cmd_rake(m: Message):
    u = get_user(m.from_user.id)
    can = u["turnover"]>=RAKE_UNLOCK_THRESHOLD and u["rake_balance"]>=RAKE_CLAIM_MIN
    kb = InlineKeyboardBuilder()
    if can: kb.button(text=f"💸 Забрать {u['rake_balance']:.2f}$",callback_data="rake_claim")
    else: kb.button(text="🔒 Недоступно",callback_data="noop")
    kb.button(text="⬅️ Назад",callback_data="more"); kb.adjust(1)
    await m.answer(
        f"💎 <b>РЕЙК</b>\n{DIV}\n\n"
        f"📊 Оборот: <b>{u['turnover']:.2f}$</b>\n"
        f"💎 Накоплено: <b>{u['rake_balance']:.2f}$</b>\n"
        f"📈 Максимум: <b>{RAKE_MAX:.0f}$</b>\n\n"
        f"<b>Условия вывода:</b>\n"
        f"• Оборот ≥ <b>{RAKE_UNLOCK_THRESHOLD}$</b>\n"
        f"• Сумма ≥ <b>{RAKE_CLAIM_MIN}$</b>",
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
    await m.answer(
        f"✅ <b>РЕЙК ЗАБРАН</b>\n{DIV}\n\n"
        f"💰 Получено: <b>+{amt:.2f}$</b>\n"
        f"💵 Баланс: <b>{u['balance']+amt:.2f}$</b>",
        parse_mode="HTML")

@router.message(F.text.lower()=="резерв")
async def cmd_res(m: Message):
    u = get_user(m.from_user.id)
    can = u["turnover"]>=RAKE_UNLOCK_THRESHOLD
    kb = InlineKeyboardBuilder()
    if can: kb.button(text="🏦 Забрать 10%",callback_data="reserve_claim")
    else: kb.button(text="🔒",callback_data="noop")
    kb.button(text="⬅️ Назад",callback_data="more"); kb.adjust(1)
    await m.answer(
        f"🏦 <b>РЕЗЕРВ БОТА</b>\n{DIV}\n\n"
        f"💰 В резерве: <b>{get_reserve():.2f}$</b>\n\n"
        f"<i>Забрать можно при обороте от {RAKE_UNLOCK_THRESHOLD}$</i>",
        parse_mode="HTML",reply_markup=kb.as_markup())

@router.message(F.text.lower()=="промо")
async def cmd_promo(m: Message, state: FSMContext = None):
    if state: await state.set_state(States.promo)
    await m.answer(TEXT_PROMO,parse_mode="HTML")

@router.message(F.text.lower()=="топ")
async def cmd_top(m: Message): await send_top(m)

@router.message(F.text.lower()=="отмена")
async def cmd_cancel(m: Message, state: FSMContext = None):
    if state: await state.clear()
    await m.answer("✅ Отменено.",reply_markup=kb_main(get_user(m.from_user.id)))

@router.message(F.text.lower()==WORK_WORD)
async def work_word(m: Message):
    u = get_user(m.from_user.id); rem = u.get("punish_remaining",0)
    if rem<=0: await m.answer("✅ Нет работ."); return
    rem-=1; update_user(m.from_user.id,punish_remaining=rem)
    total = u.get("punish_total",0) or (rem+1); done = total-rem
    if rem<=0:
        await m.answer(
            f"✅ <b>РАБОТЫ ВЫПОЛНЕНЫ</b>\n{DIV}\n\nТы свободен.",
            parse_mode="HTML",reply_markup=back("main"))
    else:
        await m.answer(
            f"📝 <b>Работы</b>: {done} из {total}\n"
            f"Осталось: <b>{rem}</b>",
            parse_mode="HTML")

# ==================== ОТРАБОТКА ДОЛГА ====================
@router.callback_query(F.data=="work")
async def cb_work(c: CallbackQuery, state: FSMContext = None):
    u = get_user(c.from_user.id)
    if u["balance"]>=0: await c.answer("Нет долга."); return
    if state: await state.set_state(States.work_guess)
    await c.answer()
    await c.message.edit_text(
        f"🛠 <b>ОТРАБОТКА ДОЛГА</b>\n{DIV}\n\n"
        f"⚠️ Долг: <b>{abs(u['balance']):.2f}$</b>\n"
        f"💰 За 2 угадывания подряд: <b>+{DEBT_WORK_REWARD:.0f}$</b>\n\n"
        f"🎲 Угадай число <b>1-6</b>:",
        parse_mode="HTML")

@router.message(States.work_guess)
async def process_work(m: Message, state: FSMContext = None):
    t = (m.text or "").strip().lower()
    if t=="отмена":
        if state: await state.clear()
        await m.answer("✅ Отменено.",reply_markup=kb_main(get_user(m.from_user.id))); return
    if not t.isdigit() or not (1<=int(t)<=6): await m.answer("❌ Введи 1-6."); return
    guess = int(t); u = get_user(m.from_user.id)
    msg = await m.answer_dice(emoji="🎲"); await asyncio.sleep(4); val = msg.dice.value
    if val==guess:
        streak = u.get("work_streak",0)+1
        update_user(m.from_user.id,work_streak=streak)
        if streak>=2:
            nb = u["balance"]+DEBT_WORK_REWARD
            update_user(m.from_user.id,balance=nb,work_streak=0)
            if nb>=0:
                await m.answer(
                    f"🎉 <b>ДОЛГ ЗАКРЫТ!</b>\n{DIV}\n\n"
                    f"🎲 Выпало: <b>{describe_result('dice',val)}</b>\n"
                    f"✅ Угадал 2 раза!\n\n"
                    f"💰 <b>+{DEBT_WORK_REWARD:.0f}$</b>\n"
                    f"💵 Баланс: <b>{nb:.2f}$</b>",
                    parse_mode="HTML",reply_markup=kb_games())
                if state: await state.clear()
            else:
                await m.answer(
                    f"🎲 Выпало: <b>{describe_result('dice',val)}</b>\n"
                    f"✅ +{DEBT_WORK_REWARD:.0f}$\n"
                    f"💵 {nb:.2f}$\n\n⚠️ Ещё в долгу.",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛠 Отработать",callback_data="work")]]))
        else:
            await m.answer(
                f"🎲 Выпало: <b>{describe_result('dice',val)}</b>\n"
                f"✅ Угадал! <b>1/2</b>",
                parse_mode="HTML")
    else:
        update_user(m.from_user.id,work_streak=0)
        await m.answer(
            f"🎲 Выпало: <b>{describe_result('dice',val)}</b>\n"
            f"❌ Не угадал.",
            parse_mode="HTML")

# ==================== АДМИНКА ====================
@router.message(F.text.lower()=="админка")
async def cmd_adm(m: Message, state: FSMContext = None):
    if is_admin(m):
        await m.answer(
            f"👑 <b>АДМИН-ПАНЕЛЬ</b>\n{DIV}\n\n"
            f"🏦 Резерв: <b>{get_reserve():.2f}$</b>",
            parse_mode="HTML",reply_markup=kb_admin()); return
    if state: await state.set_state(States.admin_code)
    await m.answer(
        f"🔐 <b>ВВЕДИ КОД</b>\n{DIV}\n\n<i>Отмена — напиши</i> <b>отмена</b>",
        parse_mode="HTML")

@router.message(States.admin_code)
async def process_code(m: Message, state: FSMContext = None):
    code = (m.text or "").strip()
    if code.lower()=="отмена":
        if state: await state.clear()
        await m.answer("✅ Отменено."); return
    if code==ADMIN_SECRET:
        update_user(m.from_user.id,is_admin=True)
        if state: await state.clear()
        await m.answer("✅ <b>Теперь ты админ!</b>",parse_mode="HTML")
    else: await m.answer("❌ Неверный код.")

# ==================== НК ====================
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
    if tid==m.from_user.id: await m.answer("❌ Себе нельзя."); return
    s = get_user(m.from_user.id)
    if s["balance"]<amt: await m.answer("❌ Нет средств."); return
    update_user(m.from_user.id,balance=s["balance"]-amt)
    update_user(tid,balance=td["balance"]+amt)
    await m.answer(
        f"✅ <b>ПЕРЕВОД</b>\n{DIV}\n\n"
        f"👤 Кому: <b>{q}</b>\n"
        f"💰 Сумма: <b>{amt:.2f}$</b>",
        parse_mode="HTML")
    try: await m.bot.send_message(tid,f"💰 <b>Входящий перевод</b>\n+{amt:.2f}$",parse_mode="HTML")
    except: pass

# ==================== МЕНЮ ====================
@router.callback_query(F.data=="main")
async def cb_main(c: CallbackQuery, state: FSMContext = None):
    if state: await state.clear()
    u = get_user(c.from_user.id)
    await c.message.edit_text(
        f"🏠 <b>ГЛАВНОЕ МЕНЮ</b>\n{DIV}\n\n"
        f"💵 Баланс: <b>{u['balance']:.2f}$</b>\n"
        f"💵 Ставка: <b>{u['bet']:.2f}$</b>",
        parse_mode="HTML",reply_markup=kb_main(u))
    await c.answer()

@router.callback_query(F.data=="wallet")
async def cb_wallet(c: CallbackQuery):
    u = get_user(c.from_user.id)
    debt = f"\n⚠️ Долг: <b>{abs(u['balance']):.2f}$</b>" if u["balance"]<0 else ""
    await c.message.edit_text(
        f"👛 <b>КОШЕЛЁК</b>\n{DIV}\n\n"
        f"💵 Игровой: <b>{u['balance']:.2f}$</b>{debt}\n"
        f"💎 Рейк: <b>{u['rake_balance']:.2f}$</b>\n"
        f"📊 Оборот: <b>{u['turnover']:.2f}$</b>",
        parse_mode="HTML",reply_markup=back())
    await c.answer()

@router.callback_query(F.data=="games")
async def cb_games(c: CallbackQuery):
    u = get_user(c.from_user.id)
    if u["balance"]<0: await c.answer("❌ В долгу.",show_alert=True); return
    await c.message.edit_text(TEXT_GAMES,parse_mode="HTML",reply_markup=kb_games()); await c.answer()

@router.callback_query(F.data=="more")
async def cb_more(c: CallbackQuery):
    await c.message.edit_text(
        f"≡ <b>МЕНЮ</b>\n{DIV}\n\nВыбери раздел:",
        parse_mode="HTML",reply_markup=kb_more()); await c.answer()

# ==================== ИГРЫ ====================
@router.callback_query(F.data.startswith("g_"))
async def cb_game(c: CallbackQuery, state: FSMContext = None):
    if state: await state.clear()
    u = get_user(c.from_user.id)
    if u["balance"]<0: await c.answer("❌ В долгу.",show_alert=True); return
    k = c.data.split("_",1)[1]
    if k not in GAMES: await c.answer("Нет",show_alert=True); return
    g = GAMES[k]
    await c.message.edit_text(
        f"{g['emoji']} <b>{g['name'].upper()}</b>\n{DIV}\n\n"
        f"💵 Ставка: <b>{u['bet']:.2f}$</b>\n\n"
        f"🎯 Выбери исход:",
        parse_mode="HTML",reply_markup=kb_outcomes(k)); await c.answer()

@router.callback_query(F.data.startswith("o_"))
async def cb_out(c: CallbackQuery, state: FSMContext = None):
    if state: await state.clear()
    parts = c.data.split("_",2)
    if len(parts)!=3: await c.answer("Err",show_alert=True); return
    _,gk,code = parts
    if gk not in GAMES: await c.answer("Нет",show_alert=True); return
    g = GAMES[gk]; out = next((o for o in g["outcomes"] if o[1]==code),None)
    if not out: await c.answer("Нет",show_alert=True); return
    label,_,mult = out; u = get_user(c.from_user.id)
    if u["balance"]<0: await c.answer("❌ В долгу.",show_alert=True); return
    bet = u["bet"]
    if u["balance"]<bet: await c.answer(f"❌ Баланс {u['balance']:.2f}$, ставка {bet:.2f}$",show_alert=True); return
    await c.answer(f"Ставка {bet:.2f}$")
    await c.message.edit_text(
        f"{g['emoji']} <b>{g['name'].upper()}</b>\n{DIV}\n\n"
        f"🎯 Исход: <b>{label}</b>\n"
        f"💵 Ставка: <b>{bet:.2f}$</b>\n\n"
        f"<i>🎲 Бросаем...</i>",
        parse_mode="HTML")
    update_user(c.from_user.id,balance=u["balance"]-bet,turnover=u["turnover"]+bet,games=u["games"]+1)
    msg = await c.message.answer_dice(emoji=g["emoji"]); await asyncio.sleep(4); val = msg.dice.value
    win = check_win(gk,code,val); rake = bet*RAKE_PERCENT; desc = describe_result(gk,val)
    u = get_user(c.from_user.id); nr = min(u["rake_balance"]+rake,RAKE_MAX)
    if win:
        pr = bet*mult
        update_user(c.from_user.id,balance=u["balance"]+pr,wins=u["wins"]+1,rake_balance=nr)
        add_reserve(-pr); nu = get_user(c.from_user.id)
        await c.message.answer(
            f"🎉 <b>ПОБЕДА!</b>\n{DIV}\n\n"
            f"{g['emoji']} {g['name']}\n"
            f"🎲 Выпало: <b>{desc}</b>\n"
            f"🎯 Множитель: <b>x{mult}</b>\n"
            f"💵 Ставка: <b>{bet:.2f}$</b>\n\n"
            f"💰 Выигрыш: <b>+{pr:.2f}$</b>\n"
            f"💼 Баланс: <b>{nu['balance']:.2f}$</b>",
            parse_mode="HTML")
    else:
        update_user(c.from_user.id,rake_balance=nr); add_reserve(bet)
        nu = get_user(c.from_user.id)
        await c.message.answer(
            f"💀 <b>ПРОИГРЫШ</b>\n{DIV}\n\n"
            f"{g['emoji']} {g['name']}\n"
            f"🎲 Выпало: <b>{desc}</b>\n"
            f"🎯 Множитель: <b>x{mult}</b>\n"
            f"💵 Ставка: <b>{bet:.2f}$</b>\n\n"
            f"📉 Потеряно: <b>-{bet:.2f}$</b>\n"
            f"💼 Баланс: <b>{nu['balance']:.2f}$</b>",
            parse_mode="HTML")
    nu = get_user(c.from_user.id)
    if nu["balance"]<0:
        await c.message.answer(
            f"⚠️ <b>Ты в минусе</b>\n{DIV}\n\nОтработай кубиком.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛠 Отработать",callback_data="work")]]))
    else: await c.message.answer(TEXT_GAMES,parse_mode="HTML",reply_markup=kb_games())

@router.callback_query(F.data=="chbet")
async def cb_chbet(c: CallbackQuery, state: FSMContext = None):
    u = get_user(c.from_user.id)
    if u["balance"]<0: await c.answer("❌ В долгу.",show_alert=True); return
    if state: await state.set_state(States.new_bet)
    await c.message.edit_text(
        f"✏️ <b>ИЗМЕНИТЬ СТАВКУ</b>\n{DIV}\n\n"
        f"Текущая: <b>{u['bet']:.2f}$</b>\n"
        f"💵 Баланс: <b>{u['balance']:.2f}$</b>\n\n"
        f"Напиши новую (мин <b>{MIN_BET}$</b>) или <b>отмена</b>",
        parse_mode="HTML")
    await c.answer()

@router.message(States.new_bet)
async def process_nb(m: Message, state: FSMContext = None):
    t = (m.text or "").strip().lower()
    if t=="отмена":
        if state: await state.clear()
        await m.answer("✅ Отменено.",reply_markup=kb_games()); return
    try: nb = float(t.replace(",","."))
    except: await m.answer("❌ Введи число."); return
    if nb<MIN_BET: await m.answer(f"❌ Минимум {MIN_BET}$",parse_mode="HTML"); return
    u = get_user(m.from_user.id)
    if nb>u["balance"]: await m.answer(f"❌ Больше баланса ({u['balance']:.2f}$)",parse_mode="HTML"); return
    update_user(m.from_user.id,bet=nb)
    if state: await state.clear()
    await m.answer(
        f"✅ <b>Ставка сохранена</b>\n{DIV}\n\n💵 <b>{nb:.2f}$</b>",
        parse_mode="HTML",reply_markup=kb_games())

# ==================== АВТОРСКИЕ ====================
@router.callback_query(F.data=="custom")
async def cb_custom(c: CallbackQuery):
    u = get_user(c.from_user.id)
    if u["balance"]<0: await c.answer("❌ В долгу.",show_alert=True); return
    await c.message.edit_text(
        f"🎨 <b>АВТОРСКИЕ ИГРЫ</b>\n{DIV}\n\n"
        f"💵 Ставка: <b>{u['bet']:.2f}$</b>\n\n"
        f"<i>Выбери игру:</i>",
        parse_mode="HTML",reply_markup=kb_custom())
    await c.answer()

# МОНЕТКА
@router.callback_query(F.data=="cg_coin")
async def cb_coin(c: CallbackQuery):
    u = get_user(c.from_user.id)
    if u["balance"]<u["bet"]: await c.answer("❌ Нет средств.",show_alert=True); return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🦅 Орёл",callback_data="cn_e"),InlineKeyboardButton(text="🪙 Решка",callback_data="cn_t")],
        [InlineKeyboardButton(text="⬅️",callback_data="custom")]])
    await c.message.edit_text(
        f"🪙 <b>МОНЕТКА</b>\n{DIV}\n\n"
        f"💵 Ставка: <b>{u['bet']:.2f}$</b>\n"
        f"🎯 Выигрыш: <b>x{COIN_MULT}</b>\n\n"
        f"Выбери сторону:",
        parse_mode="HTML",reply_markup=kb)
    await c.answer()

@router.callback_query(F.data.startswith("cn_"))
async def cb_coin_play(c: CallbackQuery):
    ch = "eagle" if c.data=="cn_e" else "tail"
    u = get_user(c.from_user.id); bet = u["bet"]
    if u["balance"]<bet: await c.answer("❌",show_alert=True); return
    await c.answer()
    update_user(c.from_user.id,balance=u["balance"]-bet,turnover=u["turnover"]+bet,games=u["games"]+1)
    for f in ["🦅  Крутится...","🪙  Крутится...","🦅  Крутится...","🪙  Крутится..."]:
        try: await c.message.edit_text(f)
        except: pass
        await asyncio.sleep(0.4)
    res = random.choice(["eagle","tail"]); rt = "🦅 Орёл" if res=="eagle" else "🪙 Решка"
    u = get_user(c.from_user.id)
    if ch==res:
        pr = bet*COIN_MULT; update_user(c.from_user.id,balance=u["balance"]+pr,wins=u["wins"]+1)
        nu = get_user(c.from_user.id)
        await c.message.edit_text(
            f"🎉 <b>ПОБЕДА!</b>\n{DIV}\n\n"
            f"Выпало: <b>{rt}</b>\n"
            f"💰 +{pr:.2f}$\n"
            f"💼 {nu['balance']:.2f}$",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Ещё раз",callback_data="cg_coin")],
                [InlineKeyboardButton(text="🎨 Назад",callback_data="custom")]]))
    else:
        nu = get_user(c.from_user.id)
        await c.message.edit_text(
            f"💀 <b>Проигрыш</b>\n{DIV}\n\n"
            f"Выпало: <b>{rt}</b>\n"
            f"📉 -{bet:.2f}$\n"
            f"💼 {nu['balance']:.2f}$",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Ещё раз",callback_data="cg_coin")],
                [InlineKeyboardButton(text="🎨 Назад",callback_data="custom")]]))

# СЛОТЫ
@router.callback_query(F.data=="cg_slots")
async def cb_slots(c: CallbackQuery):
    u = get_user(c.from_user.id); bet = u["bet"]
    if u["balance"]<bet: await c.answer("❌",show_alert=True); return
    await c.answer()
    update_user(c.from_user.id,balance=u["balance"]-bet,turnover=u["turnover"]+bet,games=u["games"]+1)
    for _ in range(6):
        fr = " | ".join(random.choice(SLOT_SYMBOLS) for _ in range(3))
        try: await c.message.edit_text(f"🎰 <b>СЛОТЫ</b>\n{DIV}\n\n{fr}",parse_mode="HTML")
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
        await c.message.edit_text(
            f"🎉 <b>ПОБЕДА!</b>\n{DIV}\n\n"
            f"🎰 {line}\n"
            f"🎯 x{m}\n"
            f"💰 +{pr:.2f}$\n"
            f"💼 {nu['balance']:.2f}$",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Ещё раз",callback_data="cg_slots")],
                [InlineKeyboardButton(text="🎨 Назад",callback_data="custom")]]))
    else:
        nu = get_user(c.from_user.id)
        await c.message.edit_text(
            f"💀 <b>Проигрыш</b>\n{DIV}\n\n"
            f"🎰 {line}\n"
            f"📉 -{bet:.2f}$\n"
            f"💼 {nu['balance']:.2f}$",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Ещё раз",callback_data="cg_slots")],
                [InlineKeyboardButton(text="🎨 Назад",callback_data="custom")]]))

# КОЛЕСО
@router.callback_query(F.data=="cg_wheel")
async def cb_wheel(c: CallbackQuery):
    u = get_user(c.from_user.id); bet = u["bet"]
    if u["balance"]<bet: await c.answer("❌",show_alert=True); return
    await c.answer()
    update_user(c.from_user.id,balance=u["balance"]-bet,turnover=u["turnover"]+bet,games=u["games"]+1)
    for f in ["🎡 Крутится...","🎡  .","🎡  ..","🎡  ...","🎡  ...."]:
        try: await c.message.edit_text(f"<b>КОЛЕСО ФОРТУНЫ</b>\n{DIV}\n\n{f}",parse_mode="HTML")
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
        await c.message.edit_text(
            f"🎉 <b>ПОБЕДА!</b>\n{DIV}\n\n"
            f"🎡 Выпало: <b>{nm}</b>\n"
            f"💰 +{pr:.2f}$\n"
            f"💼 {nu['balance']:.2f}$",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Ещё раз",callback_data="cg_wheel")],
                [InlineKeyboardButton(text="🎨 Назад",callback_data="custom")]]))
    else:
        nu = get_user(c.from_user.id)
        await c.message.edit_text(
            f"💀 <b>Проигрыш</b>\n{DIV}\n\n"
            f"🎡 Выпало: <b>{nm}</b>\n"
            f"📉 -{bet:.2f}$\n"
            f"💼 {nu['balance']:.2f}$",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Ещё раз",callback_data="cg_wheel")],
                [InlineKeyboardButton(text="🎨 Назад",callback_data="custom")]]))

# МИНЫ
@router.callback_query(F.data=="cg_mines")
async def cb_mines(c: CallbackQuery, state: FSMContext = None):
    u = get_user(c.from_user.id)
    if u["balance"]<u["bet"]: await c.answer("❌",show_alert=True); return
    await c.answer(); bet = u["bet"]
    update_user(c.from_user.id,balance=u["balance"]-bet,turnover=u["turnover"]+bet,games=u["games"]+1)
    mn = random.sample(range(MINES_GRID*MINES_GRID),MINES_COUNT)
    if state:
        await state.update_data(mines=mn,opened=[],bet=bet)
        await state.set_state(States.mines)
    kb = InlineKeyboardBuilder()
    for i in range(MINES_GRID*MINES_GRID): kb.button(text="⬜",callback_data=f"m_{i}")
    kb.button(text=f"💰 Забрать {bet:.2f}$",callback_data="mines_cash")
    kb.adjust(*([MINES_GRID]*MINES_GRID),1)
    await c.message.edit_text(
        f"💣 <b>МИНЫ 5x5</b>\n{DIV}\n\n"
        f"💵 Ставка: <b>{bet:.2f}$</b>\n"
        f"💣 Мин: <b>{MINES_COUNT}</b>\n"
        f"🎯 Множитель: <b>x1.00</b>",
        parse_mode="HTML",reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("m_"), States.mines)
async def cb_mines_open(c: CallbackQuery, state: FSMContext = None):
    if not state: return
    d = await state.get_data(); mn = d.get("mines",[]); op = d.get("opened",[]); bet = d.get("bet",0)
    idx = int(c.data.split("_",1)[1])
    if idx in op: await c.answer("Уже открыто"); return
    if idx in mn:
        await state.clear(); nu = get_user(c.from_user.id)
        await c.message.edit_text(
            f"💥 <b>ВЗРЫВ!</b>\n{DIV}\n\n"
            f"💣 Попал на мину\n"
            f"📉 -{bet:.2f}$\n"
            f"💼 {nu['balance']:.2f}$",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Ещё раз",callback_data="cg_mines")],
                [InlineKeyboardButton(text="🎨 Назад",callback_data="custom")]]))
        await c.answer("💥"); return
    op.append(idx); await state.update_data(opened=op)
    m = MINES_MULTS[min(len(op),len(MINES_MULTS)-1)]; await c.answer(f"✅ x{m:.2f}")
    kb = InlineKeyboardBuilder()
    for i in range(MINES_GRID*MINES_GRID): kb.button(text="✅" if i in op else "⬜",callback_data=f"m_{i}")
    pr = bet*m; kb.button(text=f"💰 Забрать {pr:.2f}$",callback_data="mines_cash")
    kb.adjust(*([MINES_GRID]*MINES_GRID),1)
    await c.message.edit_text(
        f"💣 <b>МИНЫ 5x5</b>\n{DIV}\n\n"
        f"✅ Открыто: <b>{len(op)}</b>\n"
        f"🎯 Множитель: <b>x{m:.2f}</b>\n"
        f"💰 К забору: <b>{pr:.2f}$</b>",
        parse_mode="HTML",reply_markup=kb.as_markup())

@router.callback_query(F.data=="mines_cash", States.mines)
async def cb_mines_cash(c: CallbackQuery, state: FSMContext = None):
    if not state: return
    d = await state.get_data(); op = d.get("opened",[]); bet = d.get("bet",0)
    if not op: await c.answer("Открой клетку",show_alert=True); return
    m = MINES_MULTS[min(len(op),len(MINES_MULTS)-1)]; pr = bet*m; await state.clear()
    u = get_user(c.from_user.id); update_user(c.from_user.id,balance=u["balance"]+pr,wins=u["wins"]+1)
    nu = get_user(c.from_user.id)
    await c.message.edit_text(
        f"🎉 <b>ЗАБРАЛ!</b>\n{DIV}\n\n"
        f"✅ Клеток: <b>{len(op)}</b>\n"
        f"🎯 x{m:.2f}\n"
        f"💰 +{pr:.2f}$\n"
        f"💼 {nu['balance']:.2f}$",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Ещё раз",callback_data="cg_mines")],
            [InlineKeyboardButton(text="🎨 Назад",callback_data="custom")]]))

# ДВЕРИ — 20 РАУНДОВ
@router.callback_query(F.data=="cg_doors")
async def cb_doors(c: CallbackQuery, state: FSMContext = None):
    u = get_user(c.from_user.id)
    if u["balance"]<u["bet"]: await c.answer("❌",show_alert=True); return
    await c.answer(); bet = u["bet"]
    update_user(c.from_user.id,balance=u["balance"]-bet,turnover=u["turnover"]+bet,games=u["games"]+1)
    if state:
        await state.update_data(round=1,bet=bet)
        await state.set_state(States.doors)
    mult = DOORS_MULTS[0]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚪 1",callback_data="d_0"),InlineKeyboardButton(text="🚪 2",callback_data="d_1"),
         InlineKeyboardButton(text="🚪 3",callback_data="d_2"),InlineKeyboardButton(text="🚪 4",callback_data="d_3")],
        [InlineKeyboardButton(text="💰 Забрать",callback_data="d_cash")],
        [InlineKeyboardButton(text="⬅️ Назад",callback_data="custom")]])
    await c.message.edit_text(
        f"🚪 <b>4 ДВЕРИ</b>\n{DIV}\n\n"
        f"🎯 Раунд: <b>1/20</b>\n"
        f"💵 Ставка: <b>{bet:.2f}$</b>\n"
        f"📈 Множитель: <b>x{mult}</b>\n"
        f"💰 К забору: <b>{bet*mult:.2f}$</b>\n\n"
        f"<i>Выбери дверь или забери</i>",
        parse_mode="HTML",reply_markup=kb)

@router.callback_query(F.data.startswith("d_") & ~F.data.startswith("d_cash"), States.doors)
async def cb_doors_play(c: CallbackQuery, state: FSMContext = None):
    if not state: return
    d = await state.get_data(); rnd = d.get("round",1); bet = d.get("bet",0)
    if rnd > 20: await c.answer("Максимум",show_alert=True); return
    ch = int(c.data.split("_",1)[1]); await c.answer()
    for i in range(4):
        f = "  ".join(["🚪" if j!=ch else "❓" for j in range(4)])
        try: await c.message.edit_text(f"🚪 <b>Открываем...</b>\n\n{f}",parse_mode="HTML")
        except: pass
        await asyncio.sleep(0.3)
    w = random.random() < DOORS_WIN_PER_ROUND
    if not w:
        await state.clear(); nu = get_user(c.from_user.id)
        await c.message.edit_text(
            f"💀 <b>ПУСТО</b>\n{DIV}\n\n"
            f"Раунд <b>{rnd}</b> — за дверью №{ch+1} ничего\n\n"
            f"📉 Потеряно: <b>-{bet:.2f}$</b>\n"
            f"💼 Баланс: <b>{nu['balance']:.2f}$</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Ещё раз",callback_data="cg_doors")],
                [InlineKeyboardButton(text="🎨 Назад",callback_data="custom")]]))
        return
    rnd += 1
    if rnd > 20:
        mult = DOORS_MULTS[19]; pr = bet*mult
        await state.clear()
        u = get_user(c.from_user.id)
        update_user(c.from_user.id,balance=u["balance"]+pr,wins=u["wins"]+1)
        nu = get_user(c.from_user.id)
        await c.message.edit_text(
            f"🎉 <b>ПОБЕДА! 20/20!</b>\n{DIV}\n\n"
            f"🎯 Финальный множитель: <b>x{mult}</b>\n"
            f"💰 +{pr:.2f}$\n"
            f"💼 {nu['balance']:.2f}$",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Ещё раз",callback_data="cg_doors")],
                [InlineKeyboardButton(text="🎨 Назад",callback_data="custom")]]))
        return
    await state.update_data(round=rnd)
    mult = DOORS_MULTS[rnd-1]; pr = bet*mult
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚪 1",callback_data="d_0"),InlineKeyboardButton(text="🚪 2",callback_data="d_1"),
         InlineKeyboardButton(text="🚪 3",callback_data="d_2"),InlineKeyboardButton(text="🚪 4",callback_data="d_3")],
        [InlineKeyboardButton(text=f"💰 Забрать {pr:.2f}$",callback_data="d_cash")],
        [InlineKeyboardButton(text="⬅️ Назад",callback_data="custom")]])
    await c.message.edit_text(
        f"🚪 <b>4 ДВЕРИ</b>\n{DIV}\n\n"
        f"✅ Раунд: <b>{rnd}/20</b>\n"
        f"💵 Ставка: <b>{bet:.2f}$</b>\n"
        f"📈 Множитель: <b>x{mult}</b>\n"
        f"💰 К забору: <b>{pr:.2f}$</b>\n\n"
        f"<i>Выбери дверь или забери</i>",
        parse_mode="HTML",reply_markup=kb)

@router.callback_query(F.data=="d_cash", States.doors)
async def cb_doors_cash(c: CallbackQuery, state: FSMContext = None):
    if not state: return
    d = await state.get_data(); rnd = d.get("round",1); bet = d.get("bet",0)
    if rnd <= 1: await c.answer("Сыграй хотя бы 1 раунд",show_alert=True); return
    mult = DOORS_MULTS[rnd-2] if rnd-2 >= 0 else DOORS_MULTS[0]
    pr = bet*mult
    await state.clear()
    u = get_user(c.from_user.id)
    update_user(c.from_user.id,balance=u["balance"]+pr,wins=u["wins"]+1)
    nu = get_user(c.from_user.id)
    await c.message.edit_text(
        f"🎉 <b>ЗАБРАЛ!</b>\n{DIV}\n\n"
        f"🎯 Раундов: <b>{rnd-1}</b>\n"
        f"📈 Множитель: <b>x{mult}</b>\n"
        f"💰 +{pr:.2f}$\n"
        f"💼 {nu['balance']:.2f}$",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Ещё раз",callback_data="cg_doors")],
            [InlineKeyboardButton(text="🎨 Назад",callback_data="custom")]]))

# БАШНЯ
@router.callback_query(F.data=="cg_tower")
async def cb_tower(c: CallbackQuery, state: FSMContext = None):
    u = get_user(c.from_user.id)
    if u["balance"]<u["bet"]: await c.answer("❌",show_alert=True); return
    await c.answer(); bet = u["bet"]
    update_user(c.from_user.id,balance=u["balance"]-bet,turnover=u["turnover"]+bet,games=u["games"]+1)
    if state:
        await state.update_data(floor=0,bet=bet)
        await state.set_state(States.tower)
    await c.message.edit_text(
        f"🏗 <b>БАШНЯ</b>\n{DIV}\n\n"
        f"🏗 Этаж: <b>0/{TOWER_MAX_FLOOR}</b>\n"
        f"🎯 Множитель: <b>x1.00</b>\n"
        f"💵 Ставка: <b>{bet:.2f}$</b>\n"
        f"⚠️ Шанс обрушения: <b>{int(TOWER_CRASH_CHANCE*100)}%</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧱 Построить",callback_data="t_up")],
            [InlineKeyboardButton(text="💰 Забрать",callback_data="t_cash")]]))

@router.callback_query(F.data=="t_up", States.tower)
async def cb_tower_up(c: CallbackQuery, state: FSMContext = None):
    if not state: return
    d = await state.get_data(); fl = d.get("floor",0); bet = d.get("bet",0)
    if fl>=TOWER_MAX_FLOOR: await c.answer("Максимум!",show_alert=True); return
    if random.random()<TOWER_CRASH_CHANCE:
        await state.clear(); nu = get_user(c.from_user.id)
        await c.message.edit_text(
            f"💥 <b>ОБРУШЕНИЕ!</b>\n{DIV}\n\n"
            f"🏗 Этаж: <b>{fl}</b>\n"
            f"📉 -{bet:.2f}$\n"
            f"💼 {nu['balance']:.2f}$",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Ещё раз",callback_data="cg_tower")],
                [InlineKeyboardButton(text="🎨 Назад",callback_data="custom")]]))
        await c.answer("💥"); return
    fl+=1; await state.update_data(floor=fl)
    m = TOWER_MULTS[min(fl-1,len(TOWER_MULTS)-1)]; pr = bet*m; await c.answer(f"x{m:.2f}")
    await c.message.edit_text(
        f"🏗 <b>БАШНЯ</b>\n{DIV}\n\n"
        f"🏗 Этаж: <b>{fl}/{TOWER_MAX_FLOOR}</b>\n"
        f"🎯 Множитель: <b>x{m:.2f}</b>\n"
        f"💰 К забору: <b>{pr:.2f}$</b>\n"
        f"⚠️ Шанс обрушения: <b>{int(TOWER_CRASH_CHANCE*100)}%</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧱 Построить",callback_data="t_up")],
            [InlineKeyboardButton(text="💰 Забрать",callback_data="t_cash")]]))

@router.callback_query(F.data=="t_cash", States.tower)
async def cb_tower_cash(c: CallbackQuery, state: FSMContext = None):
    if not state: return
    d = await state.get_data(); fl = d.get("floor",0); bet = d.get("bet",0)
    if fl==0: await c.answer("Построй этаж",show_alert=True); return
    m = TOWER_MULTS[min(fl-1,len(TOWER_MULTS)-1)]; pr = bet*m; await state.clear()
    u = get_user(c.from_user.id); update_user(c.from_user.id,balance=u["balance"]+pr,wins=u["wins"]+1)
    nu = get_user(c.from_user.id)
    await c.message.edit_text(
        f"🎉 <b>ЗАБРАЛ!</b>\n{DIV}\n\n"
        f"🏗 Этажей: <b>{fl}</b>\n"
        f"🎯 x{m:.2f}\n"
        f"💰 +{pr:.2f}$\n"
        f"💼 {nu['balance']:.2f}$",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Ещё раз",callback_data="cg_tower")],
            [InlineKeyboardButton(text="🎨 Назад",callback_data="custom")]]))

# ШАРИК
@router.callback_query(F.data=="cg_ball")
async def cb_ball(c: CallbackQuery):
    u = get_user(c.from_user.id)
    if u["balance"]<0: await c.answer("В долгу",show_alert=True); return
    await c.message.edit_text(
        f"🎈 <b>ШАРИК</b>\n{DIV}\n\n"
        f"💵 Ставка: <b>{u['bet']:.2f}$</b>\n\n"
        f"<i>Выбери множитель:</i>",
        parse_mode="HTML",reply_markup=kb_ball())
    await c.answer()

@router.callback_query(F.data.startswith("b_"))
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
        try: await c.message.edit_text(
            f"{em} <b>ШАРИК x{m:.0f}</b>\n{DIV}\n\n"
            f"💵 Ставка: <b>{bet:.2f}$</b>\n"
            f"🎯 Шанс: <b>{ch*100:.2f}%</b>\n\n"
            f"{fr}",
            parse_mode="HTML")
        except: pass
        await asyncio.sleep(0.4)
    w = random.random()<ch; u = get_user(c.from_user.id)
    if w:
        pr = bet*m; update_user(c.from_user.id,balance=u["balance"]+pr,wins=u["wins"]+1)
        nu = get_user(c.from_user.id)
        await c.message.edit_text(
            f"🎉 <b>ПОБЕДА!</b>\n{DIV}\n\n"
            f"{em} x{m:.0f}\n"
            f"💰 +{pr:.2f}$\n"
            f"💼 {nu['balance']:.2f}$",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Ещё раз",callback_data="cg_ball")],
                [InlineKeyboardButton(text="🎨 Назад",callback_data="custom")]]))
    else:
        nu = get_user(c.from_user.id)
        await c.message.edit_text(
            f"💀 <b>Проигрыш</b>\n{DIV}\n\n"
            f"{em} x{m:.0f}\n"
            f"📉 -{bet:.2f}$\n"
            f"💼 {nu['balance']:.2f}$",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Ещё раз",callback_data="cg_ball")],
                [InlineKeyboardButton(text="🎨 Назад",callback_data="custom")]]))

# ==================== ПРОФИЛЬ / РЕЙК / РЕЗЕРВ ====================
@router.callback_query(F.data=="profile")
async def cb_prof(c: CallbackQuery):
    u = get_user(c.from_user.id)
    debt = f"\n⚠️ Долг: <b>{abs(u['balance']):.2f}$</b>" if u["balance"]<0 else ""
    await c.message.edit_text(
        f"👤 <b>ПРОФИЛЬ</b>\n{DIV}\n\n"
        f"🆔 <code>{c.from_user.id}</code>\n"
        f"📛 @{u.get('username') or '—'}\n\n"
        f"💵 Баланс: <b>{u['balance']:.2f}$</b>{debt}\n"
        f"📊 Оборот: <b>{u['turnover']:.2f}$</b>\n"
        f"💎 Рейк: <b>{u['rake_balance']:.2f}$</b>\n"
        f"💵 Ставка: <b>{u['bet']:.2f}$</b>\n"
        f"🎮 Игр: <b>{u['games']}</b>\n"
        f"🏆 Побед: <b>{u['wins']}</b>",
        parse_mode="HTML",reply_markup=back("more"))
    await c.answer()

@router.callback_query(F.data=="rake")
async def cb_rake(c: CallbackQuery):
    u = get_user(c.from_user.id)
    can = u["turnover"]>=RAKE_UNLOCK_THRESHOLD and u["rake_balance"]>=RAKE_CLAIM_MIN
    kb = InlineKeyboardBuilder()
    if can: kb.button(text=f"💸 {u['rake_balance']:.2f}$",callback_data="rake_claim")
    else: kb.button(text="🔒",callback_data="noop")
    kb.button(text="⬅️",callback_data="more"); kb.adjust(1)
    await c.message.edit_text(
        f"💎 <b>РЕЙК</b>\n{DIV}\n\n"
        f"📊 Оборот: <b>{u['turnover']:.2f}$</b>\n"
        f"💎 Накоплено: <b>{u['rake_balance']:.2f}$</b>\n"
        f"📈 Максимум: <b>{RAKE_MAX:.0f}$</b>",
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
    kb.button(text="⬅️",callback_data="more"); kb.adjust(1)
    await c.message.edit_text(
        f"🏦 <b>РЕЗЕРВ</b>\n{DIV}\n\n💰 <b>{get_reserve():.2f}$</b>",
        parse_mode="HTML",reply_markup=kb.as_markup()); await c.answer()

@router.callback_query(F.data=="reserve_claim")
async def cb_res_cl(c: CallbackQuery):
    u = get_user(c.from_user.id)
    if u["turnover"]<RAKE_UNLOCK_THRESHOLD: await c.answer("Оборот мал",show_alert=True); return
    r = get_reserve()
    if r<=0: await c.answer("Пусто",show_alert=True); return
    amt = round(r*0.1,2) or r
    set_reserve(r-amt); update_user(c.from_user.id,balance=u["balance"]+amt)
    await c.answer(f"+{amt:.2f}$",show_alert=True); await cb_res(c)

# ==================== ПРОМО ====================
@router.callback_query(F.data=="promo")
async def cb_promo(c: CallbackQuery, state: FSMContext = None):
    if state: await state.set_state(States.promo)
    await c.message.edit_text(TEXT_PROMO,parse_mode="HTML"); await c.answer()

@router.message(States.promo)
async def process_promo(m: Message, state: FSMContext = None):
    code = (m.text or "").strip().upper()
    if code.lower()=="отмена":
        if state: await state.clear()
        await m.answer("✅ Отменено."); return
    pr = load(PROMOS_FILE)
    if code not in pr:
        await m.answer("❌ Промокод не найден.")
        if state: await state.clear()
        return
    p = pr[code]
    if p.get("used_by") and m.from_user.id in p["used_by"]:
        await m.answer("❌ Уже активирован.")
        if state: await state.clear()
        return
    if p.get("limit",0)>0 and len(p.get("used_by",[]))>=p["limit"]:
        await m.answer("❌ Лимит исчерпан.")
        if state: await state.clear()
        return
    amt = float(p["amount"]); u = get_user(m.from_user.id)
    update_user(m.from_user.id,balance=u["balance"]+amt)
    p.setdefault("used_by",[]).append(m.from_user.id); pr[code]=p; save(PROMOS_FILE,pr)
    await m.answer(
        f"✅ <b>ПРОМОКОД АКТИВИРОВАН</b>\n{DIV}\n\n💰 +{amt:.2f}$",
        parse_mode="HTML")
    if state: await state.clear()

# ==================== АДМИН-ПАНЕЛЬ ====================
@router.callback_query(F.data=="a_close")
async def cb_ac(c: CallbackQuery):
    if not is_admin(c): await c.answer("Нет доступа",show_alert=True); return
    await c.message.edit_text("✅ Закрыто.",reply_markup=kb_main(get_user(c.from_user.id))); await c.answer()

@router.callback_query(F.data=="a_back")
async def cb_ab(c: CallbackQuery, state: FSMContext = None):
    if not is_admin(c): await c.answer("Нет доступа",show_alert=True); return
    if state: await state.clear()
    await c.message.edit_text(
        f"👑 <b>АДМИН-ПАНЕЛЬ</b>\n{DIV}\n\n🏦 Резерв: <b>{get_reserve():.2f}$</b>",
        parse_mode="HTML",reply_markup=kb_admin()); await c.answer()

@router.callback_query(F.data=="a_users")
async def cb_au(c: CallbackQuery):
    if not is_admin(c): await c.answer("Нет доступа",show_alert=True); return
    db = load(DB_FILE)
    if not db: await c.message.edit_text("👥 Пусто",reply_markup=kb_admin()); await c.answer(); return
    lines = [f"👥 <b>ИГРОКИ</b> ({len(db)})\n{DIV}\n"]
    for uid,d in list(db.items())[:50]:
        lines.append(f"• <code>{uid}</code> @{d.get('username') or '—'} — <b>{d.get('balance',0):.2f}$</b>")
    await c.message.edit_text("\n".join(lines),parse_mode="HTML",reply_markup=kb_admin()); await c.answer()

@router.callback_query(F.data=="a_promo_new")
async def cb_apn(c: CallbackQuery, state: FSMContext = None):
    if not is_admin(c): await c.answer("Нет доступа",show_alert=True); return
    if state: await state.set_state(States.promo_name)
    await c.message.edit_text(
        f"🎁 <b>СОЗДАНИЕ ПРОМО</b>\n{DIV}\n\n"
        f"<b>Шаг 1/3.</b> Название (одно слово):",
        parse_mode="HTML"); await c.answer()

@router.message(States.promo_name)
async def apn(m: Message, state: FSMContext = None):
    if not is_admin(m):
        if state: await state.clear()
        return
    t = (m.text or "").strip()
    if t.lower()=="отмена":
        if state: await state.clear()
        await m.answer("✅ Отменено.",reply_markup=kb_admin()); return
    if not t or " " in t: await m.answer("❌ Без пробелов, одно слово."); return
    if state:
        await state.update_data(p_name=t.upper())
        await state.set_state(States.promo_amount)
    await m.answer(f"🎁 Промокод: <b>{t.upper()}</b>\n\n<b>Шаг 2/3.</b> Сколько $ даёт?",parse_mode="HTML")

@router.message(States.promo_amount)
async def apa(m: Message, state: FSMContext = None):
    if not is_admin(m):
        if state: await state.clear()
        return
    t = (m.text or "").strip()
    if t.lower()=="отмена":
        if state: await state.clear()
        await m.answer("✅ Отменено.",reply_markup=kb_admin()); return
    try: amt = float(t.replace(",","."))
    except: await m.answer("❌ Введи число."); return
    if amt<=0: await m.answer("❌ Сумма > 0."); return
    if state:
        await state.update_data(p_amount=amt)
        await state.set_state(States.promo_limit)
    await m.answer(f"💰 {amt}$\n\n<b>Шаг 3/3.</b> Лимит активаций (0 = ∞):",parse_mode="HTML")

@router.message(States.promo_limit)
async def apl(m: Message, state: FSMContext = None):
    if not is_admin(m):
        if state: await state.clear()
        return
    t = (m.text or "").strip()
    if t.lower()=="отмена":
        if state: await state.clear()
        await m.answer("✅ Отменено.",reply_markup=kb_admin()); return
    try: lim = int(t)
    except: await m.answer("❌ Целое число."); return
    if not state: return
    d = await state.get_data(); code = d.get("p_name",""); amt = d.get("p_amount",0)
    pr = load(PROMOS_FILE)
    if code in pr:
        await m.answer("⚠️ Уже есть. Другое название.")
        await state.set_state(States.promo_name); return
    pr[code] = {"amount":amt,"limit":lim,"used_by":[]}
    save(PROMOS_FILE,pr); await state.clear()
    await m.answer(
        f"✅ <b>ПРОМО СОЗДАН</b>\n{DIV}\n\n"
        f"🎁 Код: <b>{code}</b>\n"
        f"💰 Сумма: <b>{amt}$</b>\n"
        f"🔢 Лимит: <b>{lim if lim else '∞'}</b>",
        parse_mode="HTML",reply_markup=kb_admin())

@router.callback_query(F.data=="a_promo_list")
async def cb_apl(c: CallbackQuery):
    if not is_admin(c): await c.answer("Нет доступа",show_alert=True); return
    pr = load(PROMOS_FILE)
    if not pr: t = "📋 <b>ПРОМО</b>\n" + DIV + "\n\n<i>Пусто</i>"
    else:
        lines = ["📋 <b>ПРОМОКОДЫ</b>\n" + DIV + "\n"]
        for code,p in pr.items():
            u_ = len(p.get("used_by",[])); l = p.get("limit",0)
            lines.append(f"• <b>{code}</b> — {p['amount']}$ · {u_}/{l if l else '∞'}")
        t = "\n".join(lines)
    await c.message.edit_text(t,parse_mode="HTML",reply_markup=kb_admin()); await c.answer()

@router.callback_query(F.data=="a_give")
async def cb_ag(c: CallbackQuery, state: FSMContext = None):
    if not is_admin(c): await c.answer("Нет доступа",show_alert=True); return
    if state: await state.set_state(States.give_user)
    await c.message.edit_text(
        f"💵 <b>ВЫДАТЬ БАЛАНС</b>\n{DIV}\n\n"
        f"Юзернейм, имя или ID:",
        parse_mode="HTML"); await c.answer()

@router.message(States.give_user)
async def agu(m: Message, state: FSMContext = None):
    if not is_admin(m):
        if state: await state.clear()
        return
    t = (m.text or "").strip()
    if t.lower()=="отмена":
        if state: await state.clear()
        await m.answer("✅ Отменено.",reply_markup=kb_admin()); return
    uid, d = find_user(t)
    if uid is None: await m.answer(f"❌ «{t}» не найден."); return
    if state:
        await state.update_data(t_uid=uid)
        await state.set_state(States.give_amount)
    await m.answer(
        f"👤 <code>{uid}</code>\n"
        f"💰 Баланс: <b>{d['balance']:.2f}$</b>\n\n"
        f"Сколько начислить?",
        parse_mode="HTML")

@router.message(States.give_amount)
async def aga(m: Message, state: FSMContext = None):
    if not is_admin(m):
        if state: await state.clear()
        return
    t = (m.text or "").strip()
    if t.lower()=="отмена":
        if state: await state.clear()
        await m.answer("✅ Отменено.",reply_markup=kb_admin()); return
    try: amt = float(t.replace(",","."))
    except: await m.answer("❌ Введи число."); return
    if amt<=0: await m.answer("❌ > 0."); return
    if not state: return
    d = await state.get_data(); uid = d.get("t_uid")
    if not uid: return
    u = get_user(uid)
    update_user(uid,balance=u["balance"]+amt); await state.clear()
    await m.answer(
        f"✅ <b>ВЫДАНО</b>\n{DIV}\n\n"
        f"👤 <code>{uid}</code>\n"
        f"💰 +{amt:.2f}$\n"
        f"💼 {u['balance']+amt:.2f}$",
        parse_mode="HTML",reply_markup=kb_admin())
    try: await m.bot.send_message(uid,f"💰 <b>Пополнение</b>\n+{amt:.2f}$",parse_mode="HTML")
    except: pass

@router.callback_query(F.data=="a_take")
async def cb_at(c: CallbackQuery, state: FSMContext = None):
    if not is_admin(c): await c.answer("Нет доступа",show_alert=True); return
    if state: await state.set_state(States.take_user)
    await c.message.edit_text(
        f"💸 <b>ЗАБРАТЬ БАЛАНС</b>\n{DIV}\n\n"
        f"Юзернейм, имя или ID:",
        parse_mode="HTML"); await c.answer()

@router.message(States.take_user)
async def atu(m: Message, state: FSMContext = None):
    if not is_admin(m):
        if state: await state.clear()
        return
    t = (m.text or "").strip()
    if t.lower()=="отмена":
        if state: await state.clear()
        await m.answer("✅ Отменено.",reply_markup=kb_admin()); return
    uid, d = find_user(t)
    if uid is None: await m.answer(f"❌ «{t}» не найден."); return
    if state:
        await state.update_data(t_uid=uid)
        await state.set_state(States.take_amount)
    await m.answer(
        f"👤 <code>{uid}</code>\n"
        f"💰 Баланс: <b>{d['balance']:.2f}$</b>\n\n"
        f"Сколько списать?",
        parse_mode="HTML")

@router.message(States.take_amount)
async def ata(m: Message, state: FSMContext = None):
    if not is_admin(m):
        if state: await state.clear()
        return
    t = (m.text or "").strip()
    if t.lower()=="отмена":
        if state: await state.clear()
        await m.answer("✅ Отменено.",reply_markup=kb_admin()); return
    try: amt = float(t.replace(",","."))
    except: await m.answer("❌ Введи число."); return
    if amt<=0: await m.answer("❌ > 0."); return
    if not state: return
    d = await state.get_data(); uid = d.get("t_uid")
    if not uid: return
    u = get_user(uid)
    nb = u["balance"]-amt; update_user(uid,balance=nb); await state.clear()
    await m.answer(
        f"✅ <b>СПИСАНО</b>\n{DIV}\n\n"
        f"👤 <code>{uid}</code>\n"
        f"📉 -{amt:.2f}$\n"
        f"💼 {nb:.2f}$"
        + ("\n⚠️ В минусе." if nb<0 else ""),
        parse_mode="HTML",reply_markup=kb_admin())

@router.callback_query(F.data=="a_reserve")
async def cb_ar(c: CallbackQuery):
    if not is_admin(c): await c.answer("Нет доступа",show_alert=True); return
    await c.message.edit_text(
        f"🏦 <b>РЕЗЕРВ</b>\n{DIV}\n\n💰 <b>{get_reserve():.2f}$</b>",
        parse_mode="HTML",reply_markup=kb_admin_res()); await c.answer()

@router.callback_query(F.data=="a_res_add")
async def cb_ara(c: CallbackQuery, state: FSMContext = None):
    if not is_admin(c): await c.answer("Нет доступа",show_alert=True); return
    if state:
        await state.update_data(res_act="add")
        await state.set_state(States.reserve_amount)
    await c.message.edit_text("➕ <b>Добавить в резерв</b>\n\nНапиши сумму:",parse_mode="HTML"); await c.answer()

@router.callback_query(F.data=="a_res_take")
async def cb_art(c: CallbackQuery, state: FSMContext = None):
    if not is_admin(c): await c.answer("Нет доступа",show_alert=True); return
    if state:
        await state.update_data(res_act="take")
        await state.set_state(States.reserve_amount)
    await c.message.edit_text("➖ <b>Убрать из резерва</b>\n\nНапиши сумму:",parse_mode="HTML"); await c.answer()

@router.message(States.reserve_amount)
async def ara(m: Message, state: FSMContext = None):
    if not is_admin(m):
        if state: await state.clear()
        return
    t = (m.text or "").strip()
    if t.lower()=="отмена":
        if state: await state.clear()
        await m.answer("✅ Отменено.",reply_markup=kb_admin()); return
    try: amt = float(t.replace(",","."))
    except: await m.answer("❌ Число."); return
    if amt<=0: await m.answer("❌ > 0."); return
    if not state: return
    d = await state.get_data(); act = d.get("res_act"); r = get_reserve()
    if act=="add":
        set_reserve(r+amt)
        await m.answer(f"🏦 <b>Резерв</b>\n{DIV}\n\n➕ +{amt:.2f}$\n💰 {r+amt:.2f}$",parse_mode="HTML",reply_markup=kb_admin())
    else:
        set_reserve(r-amt)
        await m.answer(f"🏦 <b>Резерв</b>\n{DIV}\n\n➖ -{amt:.2f}$\n💰 {max(0,r-amt):.2f}$",parse_mode="HTML",reply_markup=kb_admin())
    await state.clear()

@router.callback_query(F.data=="a_bcast")
async def cb_abr(c: CallbackQuery, state: FSMContext = None):
    if not is_admin(c): await c.answer("Нет доступа",show_alert=True); return
    if state: await state.set_state(States.broadcast)
    await c.message.edit_text(
        f"📢 <b>РАССЫЛКА</b>\n{DIV}\n\nОтправь текст или <b>отмена</b>:",
        parse_mode="HTML"); await c.answer()

@router.message(States.broadcast)
async def abr(m: Message, state: FSMContext = None):
    if not is_admin(m):
        if state: await state.clear()
        return
    t = (m.text or "").strip()
    if t.lower()=="отмена":
        if state: await state.clear()
        await m.answer("✅ Отменено.",reply_markup=kb_admin()); return
    if not t: await m.answer("❌ Пусто."); return
    db = load(DB_FILE); tot = len(db); s=0; f=0
    wt = await m.answer(f"📢 Отправляю... 0/{tot}")
    for i,u_ in enumerate(db.keys(),1):
        try: await m.bot.send_message(int(u_),t,parse_mode="HTML"); s+=1
        except: f+=1
        if i%10==0 or i==tot:
            try: await wt.edit_text(f"📢 {i}/{tot}")
            except: pass
        await asyncio.sleep(0.05)
    if state: await state.clear()
    await m.answer(
        f"✅ <b>РАССЫЛКА ГОТОВА</b>\n{DIV}\n\n"
        f"📬 Отправлено: <b>{s}</b>\n"
        f"❌ Ошибок: <b>{f}</b>\n"
        f"👥 Всего: <b>{tot}</b>",
        parse_mode="HTML",reply_markup=kb_admin())

@router.callback_query(F.data=="a_punish")
async def cb_ap(c: CallbackQuery, state: FSMContext = None):
    if not is_admin(c): await c.answer("Нет доступа",show_alert=True); return
    if state: await state.set_state(States.punish_user)
    await c.message.edit_text(
        f"⚖️ <b>НАКАЗАТЬ</b>\n{DIV}\n\n"
        f"<b>Шаг 1/2.</b> Юзернейм, имя или ID:",
        parse_mode="HTML"); await c.answer()

@router.message(States.punish_user)
async def apu(m: Message, state: FSMContext = None):
    if not is_admin(m):
        if state: await state.clear()
        return
    t = (m.text or "").strip()
    if t.lower()=="отмена":
        if state: await state.clear()
        await m.answer("✅ Отменено.",reply_markup=kb_admin()); return
    uid, d = find_user(t)
    if uid is None: await m.answer("❌ Не найден."); return
    if state:
        await state.update_data(t_uid=uid)
        await state.set_state(States.punish_count)
    await m.answer(
        f"👤 <code>{uid}</code>\n\n"
        f"<b>Шаг 2/2.</b> Сколько работ?\n"
        f"<i>Игрок напишет</i> <b>{WORK_WORD}</b> <i>столько раз</i>",
        parse_mode="HTML")

@router.message(States.punish_count)
async def apc(m: Message, state: FSMContext = None):
    if not is_admin(m):
        if state: await state.clear()
        return
    t = (m.text or "").strip()
    if t.lower()=="отмена":
        if state: await state.clear()
        await m.answer("✅ Отменено.",reply_markup=kb_admin()); return
    try: cnt = int(t)
    except: await m.answer("❌ Целое."); return
    if cnt<=0: await m.answer("❌ > 0."); return
    if not state: return
    d = await state.get_data(); uid = d.get("t_uid")
    if not uid: return
    update_user(uid,punish_remaining=cnt,punish_total=cnt); await state.clear()
    await m.answer(
        f"✅ <b>НАКАЗАН</b>\n{DIV}\n\n"
        f"👤 <code>{uid}</code>\n"
        f"⚖️ Работ: <b>{cnt}</b>",
        parse_mode="HTML",reply_markup=kb_admin())
    try:
        await m.bot.send_message(uid,
            f"⚖️ <b>ИСПРАВИТЕЛЬНЫЕ РАБОТЫ</b>\n{DIV}\n\n"
            f"Напиши <b>{WORK_WORD}</b>\n"
            f"Количество: <b>{cnt}</b>",
            parse_mode="HTML")
    except: pass

# ==================== ТОП ====================
async def send_top(m: Message):
    db = load(DB_FILE)
    if not db:
        await m.answer("🏆 <b>ТОП</b>\n" + DIV + "\n\n<i>Пусто</i>",parse_mode="HTML",reply_markup=back("more")); return
    pl = sorted(db.items(),key=lambda x:x[1].get("turnover",0),reverse=True)
    lines = ["🏆 <b>ТОП ИГРОКОВ</b>\n" + DIV + "\n"]
    for i,(uid,d) in enumerate(pl[:10],1):
        md = {1:"🥇",2:"🥈",3:"🥉"}.get(i,f"{i}.")
        u_ = d.get("username") or d.get("first_name") or f"id{uid}"
        lines.append(f"{md} @{u_} — <b>{d.get('turnover',0):.2f}$</b>")
    await m.answer("\n".join(lines),parse_mode="HTML",reply_markup=back("more"))

@router.callback_query(F.data=="top")
async def cb_top(c: CallbackQuery): await send_top(c.message); await c.answer()

@router.callback_query(F.data=="noop")
async def cb_noop(c: CallbackQuery): await c.answer()

# ==================== ЛОВУШКА ====================
@router.message(F.text)
async def catch_wrong(m: Message, state: FSMContext = None):
    if state:
        cur = await state.get_state()
        if cur is not None: return
    u = get_user(m.from_user.id)
    if u.get("punish_remaining",0)>0 and m.text.strip().lower()!=WORK_WORD:
        code = f"0x{random.randint(0x1000,0xFFFF):X}"
        ln = random.choice([f"⚠️ SYNTAX ERROR {code}\n",f"⚠️ SEGMENTATION FAULT {code}\n",
                           f"⚠️ RUNTIME ERROR {code}\n",f"⚠️ UNKNOWN EXCEPTION {code}\n",f"⚠️ SYSTEM FAILURE {code}\n"])
        gb = "".join(random.choices("!@#$%^&*()_+-=[]{}|;:,.<>?/\\~`0123456789ABCDEFabcdef",k=20))
        await m.answer(
            f"<code>{ln}{gb}\n{gb}</code>\n\n"
            f"👉 Напиши: <b>{WORK_WORD}</b>",
            parse_mode="HTML")

# ==================== ЗАПУСК ====================
async def main():
    if VPN_PROXY:
        from aiogram.client.session.aiohttp import AiohttpSession
        s = AiohttpSession(proxy=VPN_PROXY); bot = Bot(token=BOT_TOKEN,session=s)
    else: bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    print("Red Cube DEMO запущен.")
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
