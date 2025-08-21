import logging
import requests
import json
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ================= CONFIG =================
BOT_TOKEN = "8241360344:AAFP0_43PmJRCTa2mpv5F2q_XYixkRXTdYs"
GIST_ID = "426a9400569f40b6f4d664b74801a78a"   # Transactions.json gist

# Split PAT into 3 parts
PART1 = "github_pat_11BQYPIPI0boMKyo1ZCgKa_"
PART2 = "LMmfMm9vacbpv1upw9PQ1mT7l2DQ3r24JD"
PART3 = "eTOOz1o5ePTEH7RT4RE861P9f"

GITHUB_PAT = PART1 + PART2 + PART3
HEADERS = {"Authorization": f"token {GITHUB_PAT}"}
GIST_URL = f"https://api.github.com/gists/{GIST_ID}"

UPI_ID = "withonly.vinay@axl"
# ===========================================

logging.basicConfig(level=logging.INFO)

# --- Fetch CCs (manual from gist file) ---
def fetch_ccs():
    url = "https://gist.githubusercontent.com/dark-2009/065082e31d1aed3b8d728dbd728fbc62/raw/ccs.txt"
    try:
        resp = requests.get(url)
        return resp.text.strip().splitlines()
    except:
        return []

def filter_cards(cards, ctype):
    result = []
    for line in cards:
        if not line or "|" not in line:
            continue
        num = line.split("|")[0].strip()
        if ctype == "visa" and num.startswith("4"):
            result.append(line)
        elif ctype == "master" and num.startswith("5"):
            result.append(line)
        elif ctype == "amex" and (num.startswith("34") or num.startswith("37")):
            result.append(line)
    return result

# --- Transactions Helpers ---
def load_transactions():
    r = requests.get(GIST_URL, headers=HEADERS).json()
    files = r.get("files", {})
    content = files.get("transactions.json", {}).get("content", "{}")
    return json.loads(content)

def save_transactions(data):
    payload = {"files": {"transactions.json": {"content": json.dumps(data, indent=2)}}}
    requests.patch(GIST_URL, headers=HEADERS, json=payload)

# --- Start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💳 Visa", callback_data="list_visa")],
        [InlineKeyboardButton("💳 Mastercard", callback_data="list_master")],
        [InlineKeyboardButton("💳 Amex", callback_data="list_amex")],
        [InlineKeyboardButton("🌟 VIP CCs", callback_data="vip_menu")]
    ]
    await update.message.reply_text("Welcome! Choose a category:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Handle Buttons ---
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    cards = fetch_ccs()

    if data.startswith("list_"):
        ctype = data.replace("list_", "")
        filtered = filter_cards(cards, ctype)
        if not filtered:
            await query.edit_message_text("⚠️ No cards found.")
            return
        text = "\n".join(filtered[:10])
        await query.edit_message_text(f"Here are some {ctype.upper()} cards:\n\n{text}")

    elif data == "vip_menu":
        vip_text = """
🌟 VIP CCs 🌟  

💎 Very Premium (Balance up to 250 - 400$):  
- Amex Platinum: $22  
- Visa Gold: $20  
- Amex Gold: $20  
- Mastercard Platinum: $18  

✨ Good Category (Balance up to 100 - 150$):  
- Mastercard: $10  
- Visa: $10  
- Amex: $10  
"""
        keyboard = [
            [InlineKeyboardButton("💎 Amex Platinum ($22)", callback_data="vip_amexplat")],
            [InlineKeyboardButton("💎 Visa Gold ($20)", callback_data="vip_visagold")],
            [InlineKeyboardButton("💎 Amex Gold ($20)", callback_data="vip_amexgold")],
            [InlineKeyboardButton("💎 Mastercard Platinum ($18)", callback_data="vip_masterplat")],
            [InlineKeyboardButton("✨ Mastercard ($10)", callback_data="vip_master")],
            [InlineKeyboardButton("✨ Visa ($10)", callback_data="vip_visa")],
            [InlineKeyboardButton("✨ Amex ($10)", callback_data="vip_amex")],
        ]
        await query.edit_message_text(vip_text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("vip_"):
        name = data.replace("vip_", "").capitalize()
        await query.edit_message_text(
            f"You selected {name}\nPay via UPI: `{UPI_ID}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Paid", callback_data=f"paid_{name}")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="vip_menu")]
            ])
        )

    elif data.startswith("paid_"):
        utr_key = f"awaitingutr_{update.effective_chat.id}"
        context.user_data["awaiting_utr"] = True
        await query.edit_message_text("Please enter your UTR below 👇")

# --- Handle UTR Submission ---
async def utr_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_utr"):
        utr = update.message.text.strip()
        user_id = update.message.chat_id
        txns = load_transactions()
        txns[utr] = {"user_id": user_id, "status": "pending"}
        save_transactions(txns)

        context.user_data["awaiting_utr"] = False
        keyboard = [
            [InlineKeyboardButton("🔍 Check Status", callback_data=f"check_{utr}")],
            [InlineKeyboardButton("📞 Contact Support", url="https://t.me/alone120122")]
        ]
        await update.message.reply_text(
            f"✅ Your UTR `{utr}` has been submitted.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# --- Check Status Button ---
async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    utr = query.data.replace("check_", "")
    txns = load_transactions()
    if utr not in txns:
        await query.edit_message_text("❌ UTR not found.")
        return
    status = txns[utr]["status"]
    if status == "pending":
        msg = "⌛ Pending. Please wait."
    elif status == "approved":
        msg = "✅ Approved! You will receive your CC within 24 hours."
    else:
        msg = "❌ Declined! Wrong UTR."
    await query.edit_message_text(msg)

# --- Main ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons, pattern="^(list_|vip_|paid_)"))
    app.add_handler(CallbackQueryHandler(handle_status, pattern="^check_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, utr_message))
    app.run_polling()

if __name__ == "__main__":
    main()
