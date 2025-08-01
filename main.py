import os
import asyncio
import requests
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import json

# -------- Конфиг --------
TOKEN = os.getenv("TOKEN2")
HF_API_TOKEN = os.getenv("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")  # Токен Hugging Face
HF_MODEL = "microsoft/DialoGPT-medium"   # Модель Hugging Face

app = ApplicationBuilder().token(TOKEN).build()

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

# -------- Тексты --------
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
            "• <a href=\"https://okx.com/join/33545594\">OKX</a>"
        ),
        hdr="💰 Цены:", none="❌ нет данных",
        fav_empty="⚠️ Список избранного пуст.",
        top_gain="📈 <b>Топ 5 рост 24ч:</b>",
        top_loss="📉 <b>Топ 5 падение 24ч:</b>"
    ),
    "uk": dict(
        start=(
            "🔥 Crypto Bot — помічник по крипторинку\n\n"
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
            "• <a href=\"https://okx.com/join/33545594\">OKX</a>"
        ),
        hdr="💰 Ціни:", none="❌ немає даних",
        fav_empty="⚠️ Список порожній.",
        top_gain="📈 <b>Топ 5 зростання 24г:</b>",
        top_loss="📉 <b>Топ 5 падіння 24г:</b>"
    ),
    "en": dict(
        start=(
            "🔥 Crypto Bot — crypto market assistant\n\n"
            "📌 Quick commands\n"
            "• /price — instantly: BTC ETH SOL\n"
            "• /price btc ada doge — prices of any coins\n"
            "• /top — top 5 gain / loss (24h)\n\n"
            "⭐️ Favorites\n"
            "• /fav — show list\n"
            "• /fav_add btc ada — add\n"
            "• /fav_remove btc — remove\n\n"
            "🔗 Services\n"
            "• <a href=\"https://www.binance.com/activity/referral-entry/CPA?ref=CPA_00POHWMMJK\">Binance</a>\n"
            "• <a href=\"https://www.bybit.com/invite?ref=A5Y25JQ\">Bybit</a>\n"
            "• <a href=\"https://promote.mexc.com/r/3EfAE\">MEXC</a>\n"
            "• <a href=\"https://bingx.com/invite/MMT7KG/\">BingX</a>\n"
            "• <a href=\"https://okx.com/join/33545594\">OKX</a>"
        ),
        hdr="💰 Prices:", none="❌ no data",
        fav_empty="⚠️ Favorites empty.",
        top_gain="📈 <b>Top 5 gain 24h:</b>",
        top_loss="📉 <b>Top 5 loss 24h:</b>"
    )
}

def L(u):
    return TXT.get((u.effective_user.language_code or "en")[:2], TXT["en"])

# ---------- Избранное ----------
favs = {}

# --------- Hugging Face simple crypto response ---------
async def hf_query(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": {
            "text": prompt
        }
    }
    try:
        r = requests.post(f"https://api-inference.huggingface.co/models/{HF_MODEL}", headers=headers, data=json.dumps(payload), timeout=10)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and "error" in data:
            return "🤖 Извините, я сейчас не могу ответить."
        if isinstance(data, list) and len(data) > 0 and "generated_text" in data[0]:
            return data[0]["generated_text"]
        if isinstance(data, dict) and "generated_text" in data:
            return data["generated_text"]
        return "🤖 Извините, я сейчас не могу ответить."
    except Exception:
        return "🤖 Извините, я сейчас не могу ответить."

# ---------- Handlers ----------
async def start_cmd(u: Update, _):
    await u.message.reply_text(L(u)["start"], parse_mode="HTML", disable_web_page_preview=True)

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

async def fav_add(u: Update, c):
    if not c.args:
        return await u.message.reply_text("Usage: /fav_add btc ada")
    favs.setdefault(u.effective_user.id, set()).update(a.lower() for a in c.args)
    await u.message.reply_text("✅ added")

async def fav_remove(u: Update, c):
    if not c.args:
        return await u.message.reply_text("Usage: /fav_remove btc ada")
    s = favs.setdefault(u.effective_user.id, set())
    for coin in c.args:
        s.discard(coin.lower())
    await u.message.reply_text("✅ updated")

async def fav_cmd(u: Update, _):
    t = L(u)
    s = favs.get(u.effective_user.id, set())
    if not s:
        return await u.message.reply_text(t["fav_empty"])
    data = await unified_24h()
    lines = ["⭐"]
    for coin in sorted(s):
        if coin.upper() in data:
            lines.append(f"{coin.upper():<6}: ${fmt_price(data[coin.upper()][0])}")
        else:
            lines.append(f"{coin.upper():<6}: {t['none']}")
    await u.message.reply_text("\n".join(lines))

# --------- Новый handler для автоответа через HF -----------
async def message_handler(u: Update, _):
    text = u.message.text
    if text.startswith("/"):
        return
    # Отвечаем только если есть слова крипта и др
    if not any(k in text.lower() for k in ["крипт", "crypto", "btc", "eth", "sol", "ada", "doge"]):
        return
    answer = await hf_query(text)
    tg_channel_url = "https://t.me/+dVqwFKDm3K83ZDli"
    footer = f'\n\n<a href="{tg_channel_url}">&#8205;ТГК админа (подписка по желанию)</a>'
    try:
        await u.message.reply_text(answer + footer, parse_mode="HTML", disable_web_page_preview=True)
    except:
        await u.message.reply_text(answer)

# ---------- Keep-alive Flask для UptimeRobot ----------
keep_alive_app = Flask("")

@keep_alive_app.route("/")
def home():
    return "✅ Bot is alive!"

def run_keep_alive():
    keep_alive_app.run(host="0.0.0.0", port=8080)

# ---------- Main ----------
if __name__ == "__main__":
    Thread(target=run_keep_alive).start()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("price", price_cmd))
    app.add_handler(CommandHandler("top", top_cmd))
    app.add_handler(CommandHandler("fav_add", fav_add))
    app.add_handler(CommandHandler("fav_remove", fav_remove))
    app.add_handler(CommandHandler("fav", fav_cmd))

    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))

    print("🚀 Бот запущен и работает 24/7 на Replit!")
    app.run_polling()
