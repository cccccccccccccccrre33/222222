import os
import json
import asyncio
import requests
from flask import Flask
from threading import Thread
from telegram import Update, BotCommand, BotCommandScope
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# -------- Конфиг --------
TOKEN = os.getenv("TOKEN")
YOUR_ADMIN_ID = 123456789  # <- Заменить на твой Telegram ID
app = ApplicationBuilder().token(TOKEN).build()

# -------- Сохранение статистики пользователей --------
USERS_FILE = 'users.json'

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)  # словарь { user_id(str): count(int) }
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

users = load_users()

def increment_user_count(user_id: int):
    key = str(user_id)
    users[key] = users.get(key, 0) + 1
    save_users(users)

def get_user_count(user_id: int) -> int:
    return users.get(str(user_id), 0)

# -------- Ютилиты --------
def fmt_price(p):
    if p >= 1: return f"{p:,.2f}"
    elif p >= 0.01: return f"{p:,.4f}"
    return f"{p:,.6f}"

def pct(x): return f"{x:+.2f}%"

# -------- Получение цен --------
def b24_binance():
    j = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=5).json()
    return {d["symbol"][:-4]: (float(d["lastPrice"]), float(d["priceChangePercent"]))
            for d in j if d["symbol"].endswith("USDT")}

def b24_bybit():
    j = requests.get("https://api.bybit.com/v2/public/tickers", timeout=5).json()["result"]
    return {d["symbol"][:-5]: (float(d["last_price"]), float(d["price_24h_pcnt"])*100)
            for d in j if d["symbol"].endswith("USDT")}

def b24_mexc():
    j = requests.get("https://api.mexc.com/api/v3/ticker/24hr", timeout=5).json()
    return {d["symbol"][:-4]: (float(d["lastPrice"]), float(d["priceChangePercent"]))
            for d in j if d["symbol"].endswith("USDT")}

def b24_bingx():
    j = requests.get("https://api.bingx.com/api/v1/market/getAllTickers", timeout=5).json()["data"]
    return {d["symbol"][:-4].upper(): (float(d["lastPrice"]), float(d["priceChangePercent"]))
            for d in j if d["symbol"].endswith("USDT")}

def b24_okx():
    j = requests.get("https://www.okx.com/api/v5/market/tickers?instType=SPOT", timeout=5).json()["data"]
    out = {}
    for d in j:
        if d["instId"].endswith("-USDT"):
            coin = d["instId"][:-5]
            last, open_24h = float(d["last"]), float(d["open24h"])
            pct24 = (last - open_24h) / open_24h * 100 if open_24h else 0
            out[coin] = (last, pct24)
    return out

EX_FUNCS = [b24_binance, b24_bybit, b24_mexc, b24_bingx, b24_okx]

async def unified_24h():
    coins = {}
    for fn in EX_FUNCS:
        try:
            data = await asyncio.to_thread(fn)
            for k, v in data.items():
                if k not in coins:
                    coins[k] = v
        except:
            pass
    return coins

TXT = {
    "ru": dict(
        start=(
            "🔥 Crypto Bot — помощник по крипторынку\n\n"
            "📌 Быстрые команды\n"
            "• /price — мгновенно: BTC ETH SOL\n"
            "• /price btc ada doge — цены любых монет\n"
            "• /top — топ 5 рост / падение (24ч)\n\n"
            "⭐️ Избранное\n"
            "• /fav — показать список\n"
            "• /fav_add btc ada — добавить\n"
            "• /fav_remove btc — удалить\n\n"
            "🔗 Сервисы\n"
            "• <a href=\"https://www.binance.com/activity/referral-entry/CPA?ref=CPA_00POHWMMJK\">Binance</a>\n"
            "• <a href=\"https://www.bybit.com/invite?ref=A5Y25JQ\">Bybit</a>\n"
            "• <a href=\"https://promote.mexc.com/r/3EfAE\">MEXC</a>\n"
            "• <a href=\"https://bingx.com/invite/MMT7KG/\">BingX</a>\n"
            "• <a href=\"https://okx.com/join/33545594\">OKX</a>\n\n"
            "📢 <a href=\"https://t.me/+dVqwFKDm3K83ZDli\">Наш Telegram-канал</a>"
        ),
        hdr="💰 Цены:", none="❌ нет данных",
        fav_empty="⚠️ Список избранного пуст.",
        top_gain="📈 <b>Топ 5 рост 24ч:</b>",
        top_loss="📉 <b>Топ 5 падение 24ч:</b>",
        stats="ℹ️ Ты использовал бота <b>{count}</b> раз(а)."
    ),
    "uk": dict(
        start=(
            "🔥 Crypto Bot — помічник на крипторинку\n\n"
            "📌 Швидкі команди\n"
            "• /price — миттєво: BTC ETH SOL\n"
            "• /price btc ada doge — ціни будь-яких монет\n"
            "• /top — топ 5 зростання / падіння (24г)\n\n"
            "⭐️ Обране\n"
            "• /fav — показати список\n"
            "• /fav_add btc ada — додати\n"
            "• /fav_remove btc — видалити\n\n"
            "🔗 Сервіси\n"
            "• <a href=\"https://www.binance.com/activity/referral-entry/CPA?ref=CPA_00POHWMMJK\">Binance</a>\n"
            "• <a href=\"https://www.bybit.com/invite?ref=A5Y25JQ\">Bybit</a>\n"
            "• <a href=\"https://promote.mexc.com/r/3EfAE\">MEXC</a>\n"
            "• <a href=\"https://bingx.com/invite/MMT7KG/\">BingX</a>\n"
            "• <a href=\"https://okx.com/join/33545594\">OKX</a>\n\n"
            "📢 <a href=\"https://t.me/+dVqwFKDm3K83ZDli\">Наш Telegram-канал</a>"
        ),
        hdr="💰 Ціни:", none="❌ немає даних",
        fav_empty="⚠️ Список обраного порожній.",
        top_gain="📈 <b>Топ 5 зростання 24г:</b>",
        top_loss="📉 <b>Топ 5 падіння 24г:</b>",
        stats="ℹ️ Ви використовували бота <b>{count}</b> раз(и)."
    ),
    "en": dict(
        start=(
            "🔥 Crypto Bot — crypto market assistant\n\n"
            "📌 Quick commands\n"
            "• /price — instantly: BTC ETH SOL\n"
            "• /price btc ada doge — any coin prices\n"
            "• /top — top 5 gainers / losers (24h)\n\n"
            "⭐️ Favorites\n"
            "• /fav — show list\n"
            "• /fav_add btc ada — add\n"
            "• /fav_remove btc — remove\n\n"
            "🔗 Services\n"
            "• <a href=\"https://www.binance.com/activity/referral-entry/CPA?ref=CPA_00POHWMMJK\">Binance</a>\n"
            "• <a href=\"https://www.bybit.com/invite?ref=A5Y25JQ\">Bybit</a>\n"
            "• <a href=\"https://promote.mexc.com/r/3EfAE\">MEXC</a>\n"
            "• <a href=\"https://bingx.com/invite/MMT7KG/\">BingX</a>\n"
            "• <a href=\"https://okx.com/join/33545594\">OKX</a>\n\n"
            "📢 <a href=\"https://t.me/+dVqwFKDm3K83ZDli\">Our Telegram Channel</a>"
        ),
        hdr="💰 Prices:", none="❌ no data",
        fav_empty="⚠️ Favorites list is empty.",
        top_gain="📈 <b>Top 5 gainers (24h):</b>",
        top_loss="📉 <b>Top 5 losers (24h):</b>",
        stats="ℹ️ You have used the bot <b>{count}</b> times."
    )
}


def L(u):
    return TXT.get((u.effective_user.language_code or "en")[:2], TXT["en"])

# -------- Избранное --------
favs = {}

# -------- Обертка для команд чтобы считать использование --------
def count_usage(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        increment_user_count(update.effective_user.id)
        return await func(update, context)
    return wrapper

# -------- Команды --------
@count_usage
async def start_cmd(u: Update, _):
    await u.message.reply_text(L(u)["start"], parse_mode="HTML", disable_web_page_preview=True)

@count_usage
async def price_cmd(u: Update, c: ContextTypes.DEFAULT_TYPE):
    t = L(u)
    coins = c.args or ["BTC", "ETH", "SOL"]
    data = await unified_24h()
    out = [t["hdr"]]
    for coin in coins:
        if coin.upper() in data:
            price, _ = data[coin.upper()]
            out.append(f"{coin.upper():<6}: ${fmt_price(price)}")
        else:
            out.append(f"{coin.upper():<6}: {t['none']}")
    await u.message.reply_text("\n".join(out))

@count_usage
async def top_cmd(u: Update, _):
    t = L(u)
    data = await unified_24h()
    gain = sorted(data.items(), key=lambda x: x[1][1], reverse=True)[:5]
    loss = sorted(data.items(), key=lambda x: x[1][1])[:5]
    lines = [t["top_gain"]]
    for n, (p, ch) in gain:
        lines.append(f"{n:<6} {pct(ch):>7}  ${fmt_price(p)}")
    lines.append("\n" + t["top_loss"])
    for n, (p, ch) in loss:
        lines.append(f"{n:<6} {pct(ch):>7}  ${fmt_price(p)}")
    await u.message.reply_text("\n".join(lines), parse_mode="HTML")

@count_usage
async def fav_add(u: Update, c):
    if not c.args:
        return await u.message.reply_text("Usage: /fav_add btc ada")
    favs.setdefault(u.effective_user.id, set()).update(a.lower() for a in c.args)
    await u.message.reply_text("✅ added")

@count_usage
async def fav_remove(u: Update, c):
    if not c.args:
        return await u.message.reply_text("Usage: /fav_remove btc ada")
    s = favs.setdefault(u.effective_user.id, set())
    for coin in c.args:
        s.discard(coin.lower())
    await u.message.reply_text("✅ updated")

@count_usage
async def fav_cmd(u: Update, _):
    t = L(u)
    s = favs.get(u.effective_user.id, set())
    if not s:
        return await u.message.reply_text(t["fav_empty"])
    data = await unified_24h()
    lines = ["⭐️"]
    for coin in sorted(s):
        if coin.upper() in data:
            lines.append(f"{coin.upper():<6}: ${fmt_price(data[coin.upper()][0])}")
        else:
            lines.append(f"{coin.upper():<6}: {t['none']}")
    await u.message.reply_text("\n".join(lines))

async def stats_cmd(u: Update, _):
    if u.effective_user.id != YOUR_ADMIN_ID:
        return await u.message.reply_text("⛔ У тебя нет доступа.")
    count = get_user_count(u.effective_user.id)
    await u.message.reply_text(L(u)["stats"].format(count=count), parse_mode="HTML")

# -------- Set Commands --------
async def set_commands():
    await app.bot.set_my_commands([
        BotCommand("start", "Start"),
        BotCommand("price", "Coin prices"),
        BotCommand("top", "Top movers"),
        BotCommand("fav", "Favorites"),
        BotCommand("fav_add", "Add to fav"),
        BotCommand("fav_remove", "Remove from fav"),
        BotCommand("stats", "Bot stats (only for admin)"),
    ], scope=BotCommandScope(type="chat", chat_id=YOUR_ADMIN_ID))

    await app.bot.set_my_commands([
        BotCommand("start", "Start"),
        BotCommand("price", "Coin prices"),
        BotCommand("top", "Top movers"),
        BotCommand("fav", "Favorites"),
        BotCommand("fav_add", "Add to fav"),
        BotCommand("fav_remove", "Remove from fav"),
    ], scope=BotCommandScope(type="default"))

# -------- Keep-alive Flask --------
keep_alive_app = Flask("")

@keep_alive_app.route("/")
def home():
    return "✅ Bot is alive!"

def run_keep_alive():
    keep_alive_app.run(host="0.0.0.0", port=8080)

# -------- MAIN --------
if __name__ == "__main__":
    Thread(target=run_keep_alive).start()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("price", price_cmd))
    app.add_handler(CommandHandler("top", top_cmd))
    app.add_handler(CommandHandler("fav", fav_cmd))
    app.add_handler(CommandHandler("fav_add", fav_add))
    app.add_handler(CommandHandler("fav_remove", fav_remove))
    app.add_handler(CommandHandler("stats", stats_cmd))

    print("🚀 Бот запущен и работает 24/7!")
    asyncio.run(set_commands())
    app.run_polling()
