import logging
import requests
import json
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ========== CONFIG ==========
BOT_TOKEN = "8241360344:AAFP0_43PmJRCTa2mpv5F2q_XYixkRXTdYs"

# Transactions Gist
TXN_GIST_ID = "426a9400569f40b6f4d664b74801a78a"

# Split PAT 🔑
PART1 = "github_pat_11BQYPIPI0boMKyo1ZCgKa_LMmfMm9vac"
PART2 = "bpv1upw9PQ1mT7l2DQ3r24JDeTOOz1o5e"
PART3 = "PTEH7RT4RE861P9f"
GITHUB_PAT = PART1 + PART2 + PART3

HEADERS = {"Authorization": f"token {GITHUB_PAT}"}

# Free CC Gist
CCS_GIST_ID = "065082e31d1aed3b8d728dbd728fbc62"
CCS_URL = f"https://api.github.com/gists/{CCS_GIST_ID}"
UPI_ID = "withonly.vinay@axl"
# ============================

logging.basicConfig(level=logging.INFO)

# --- Helper: Fetch CCs from Gist ---
def fetch_ccs():
    try:
        r = requests.get(GIST_URL, headers=HEADERS).json()
        files = r.get("files", {})
        if "ccs.txt" not in files:
            return []
        content = files["ccs.txt"]["content"]

        cards = []
        for block in content.split("Card:"):
            block = block.strip()
            if not block:
                continue
            first_line = block.splitlines()[0].strip()
            if "|" in first_line:
                cards.append(first_line)  # Example: 5396890005865006|07|28|038
        return cards
    except Exception as e:
        print("Error fetching CCs:", e)
        return []


# --- Sorting CCs properly ---
def filter_cards(cards, card_type):
    result = []
    for line in cards:
        num = line.split("|")[0].strip()
        if not num.isdigit():
            continue

        # Detect brand based on BIN/IIN
        if card_type == "visa" and num.startswith("4"):
            result.append(line)
        elif card_type == "master" and num.startswith("5"):
            result.append(line)
        elif card_type == "amex" and (num.startswith("34") or num.startswith("37")):
            result.append(line)
    return result

# --- Gist Helpers ---
def load_transactions():
    url = f"https://api.github.com/gists/{TXN_GIST_ID}"
    r = requests.get(url, headers=HEADERS).json()
    files = r.get("files", {})
    content = files.get("transactions.json", {}).get("content", "{}")
    return json.loads(content)

def save_transactions(data):
    url = f"https://api.github.com/gists/{TXN_GIST_ID}"
    payload = {"files": {"transactions.json": {"content": json.dumps(data, indent=2)}}}
    requests.patch(url, headers=HEADERS, json=payload)

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💳 Visa", callback_data="list_visa")],
        [InlineKeyboardButton("💳 Mastercard", callback_data="list_master")],
        [InlineKeyboardButton("💳 Amex", callback_data="list_amex")],
        [InlineKeyboardButton("🌟 VIP CCs", callback_data="list_vip")],
    ]
    await update.message.reply_text("Welcome! Choose a category:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cards = fetch_ccs()

    if query.data.startswith("list_"):
        ctype = query.data.replace("list_", "")
        if ctype in ["visa", "master", "amex"]:
            filtered = filter_cards(cards, ctype)
            if not filtered:
                await query.edit_message_text("❌ No cards found. (Check gist ccs.txt)")
                return
            text = "\n".join(filtered[:5])
            await query.edit_message_text(f"Here are some {ctype.upper()} cards:\n\n{text}")

        elif ctype == "vip":
            text = """
🌟 *VIP CCs* 🌟  

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
                [InlineKeyboardButton("💎 Amex Platinum ($22)", callback_data="vip_amex_platinum")],
                [InlineKeyboardButton("💎 Visa Gold ($20)", callback_data="vip_visa_gold")],
                [InlineKeyboardButton("💎 Amex Gold ($20)", callback_data="vip_amex_gold")],
                [InlineKeyboardButton("💎 Mastercard Platinum ($18)", callback_data="vip_master_platinum")],
                [InlineKeyboardButton("✨ Mastercard ($10)", callback_data="vip_master")],
                [InlineKeyboardButton("✨ Visa ($10)", callback_data="vip_visa")],
                [InlineKeyboardButton("✨ Amex ($10)", callback_data="vip_amex")],
                [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_menu")],
            ]
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("vip_"):
        plan = query.data.replace("vip_", "").replace("_", " ").title()
        text = f"You selected *{plan}*\nPay via UPI: `{UPI_ID}`"
        keyboard = [
            [InlineKeyboardButton("✅ Paid", callback_data=f"paid_{plan}")],
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_menu")],
        ]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("paid_"):
        plan = query.data.replace("paid_", "")
        context.user_data["waiting_for_utr"] = plan
        await query.edit_message_text("Please enter your UTR below 👇")

    elif query.data == "back_menu":
        await start(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "waiting_for_utr" in context.user_data:
        utr = update.message.text.strip()
        user_id = update.message.chat_id
        plan = context.user_data["waiting_for_utr"]

        txns = load_transactions()
        txns[utr] = {"user_id": user_id, "status": "pending", "plan": plan}
        save_transactions(txns)

        keyboard = [
            [InlineKeyboardButton("🔎 Check Status", callback_data=f"status_{utr}")],
            [InlineKeyboardButton("📞 Contact Support", url="https://t.me/alone120122")],
        ]
        await update.message.reply_text(
            f"✅ Your UTR `{utr}` has been submitted.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        del context.user_data["waiting_for_utr"]

async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    utr = query.data.replace("status_", "")
    txns = load_transactions()

    if utr not in txns:
        await query.edit_message_text("❌ UTR not found.")
        return

    status = txns[utr]["status"]
    if status == "pending":
        msg = "⌛ Your transaction is still pending. Please wait."
        keyboard = [
            [InlineKeyboardButton("🔎 Check Status", callback_data=f"status_{utr}")],
            [InlineKeyboardButton("📞 Contact Support", url="https://t.me/alone120122")],
        ]
    elif status == "approved":
        msg = "✅ Approved! You will receive your CC within 24 hours."
        keyboard = [
            [InlineKeyboardButton("📞 Contact Support", url="https://t.me/alone120122")],
        ]
    else:
        msg = "❌ Declined! Wrong UTR."
        keyboard = [
            [InlineKeyboardButton("📞 Contact Support", url="https://t.me/alone120122")],
        ]

    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons, pattern="^(list_|vip_|paid_|back_menu)"))
    app.add_handler(CallbackQueryHandler(handle_status, pattern="^status_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
