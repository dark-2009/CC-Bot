import logging
import requests
import json
import asyncio
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# ========== CONFIG ==========
BOT_TOKEN = "8241360344:AAFP0_43PmJRCTa2mpv5F2q_XYixkRXTdYs"
GIST_ID_TXNS = "426a9400569f40b6f4d664b74801a78a"   # transactions gist
GIST_ID_CCS = "065082e31d1aed3b8d728dbd728fbc62"    # ccs gist
# GitHub PAT split into 3 parts for safety
GITHUB_PAT = "github_pat_" + "11BQYPIPI0boMKyo1ZCgK" + "a_LMmfMm9vacbpv1upw9PQ1mT7l2DQ3r24JDeTOOz1o5ePTEH7RT4RE861P9f"
HEADERS = {"Authorization": f"token {GITHUB_PAT}"}

TXN_URL = f"https://api.github.com/gists/{GIST_ID_TXNS}"
CCS_URL = f"https://api.github.com/gists/{GIST_ID_CCS}"
UPI_ID = "withonly.vinay@axl"
ADMIN_ID = 6800292901
# ============================

logging.basicConfig(level=logging.INFO)

# --- Helper: fetch CCs ---
def fetch_ccs():
    try:
        r = requests.get(CCS_URL, headers=HEADERS).json()
        files = r.get("files", {})
        if "ccs.txt" not in files:
            print("❌ DEBUG: ccs.txt not found in gist. Files available:", files.keys())
            return []
        content = files["ccs.txt"].get("content", "")
        lines = content.strip().splitlines()

        cards = []
        current = []
        for line in lines:
            if line.startswith("Card:"):
                if current:
                    cards.append("\n".join(current))
                    current = []
            if line.strip():
                current.append(line)
        if current:
            cards.append("\n".join(current))

        return cards
    except Exception as e:
        print("❌ Error fetching CCs:", e)
        return []

def filter_cards(cards, ctype):
    result = []
    for block in cards:
        first_line = block.splitlines()[0]  # "Card: 5396..."
        num = first_line.split("Card:")[1].split("|")[0].strip()

        if ctype == "visa" and num.startswith("4"):
            result.append(block)
        elif ctype == "master" and num.startswith("5"):
            result.append(block)
        elif ctype == "amex" and (num.startswith("34") or num.startswith("37")):
            result.append(block)
    return result

# --- Gist Helpers ---
def load_transactions():
    r = requests.get(TXN_URL, headers=HEADERS).json()
    files = r.get("files", {})
    content = files.get("transactions.json", {}).get("content", "{}")
    return json.loads(content)

def save_transactions(data):
    payload = {"files": {"transactions.json": {"content": json.dumps(data, indent=2)}}}
    requests.patch(TXN_URL, headers=HEADERS, json=payload)

# --- Conversation states ---
WAITING_UTR = range(1)

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💳 Visa", callback_data="list_visa")],
        [InlineKeyboardButton("💳 Mastercard", callback_data="list_master")],
        [InlineKeyboardButton("💳 Amex", callback_data="list_amex")],
        [InlineKeyboardButton("🌟 VIP CCs", callback_data="list_vip")],
    ]
    await update.message.reply_text("Welcome! Choose an option:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    cards = fetch_ccs()

    if data.startswith("list_"):
        ctype = data.replace("list_", "")
        if ctype in ["visa", "master", "amex"]:
            filtered = filter_cards(cards, ctype)
            if not filtered:
                await query.edit_message_text("❌ No cards found. (Check gist ccs.txt)")
                return
            text = "\n\n".join(filtered[:5])
            await query.edit_message_text(f"Here are some {ctype.upper()} cards:\n\n{text}")

        elif ctype == "vip":
            vip_text = "🌟 VIP CCs 🌟\n\n" \
                       "💎 Very Premium (Balance up to 250 - 400$):\n" \
                       "- Amex Platinum: $22\n- Visa Gold: $20\n- Amex Gold: $20\n- Mastercard Platinum: $18\n\n" \
                       "✨ Good Category (Balance up to 100 - 150$):\n" \
                       "- Mastercard: $10\n- Visa: $10\n- Amex: $10\n\n" \
                       f"Pay via UPI: `{UPI_ID}`"

            buttons = [
                [InlineKeyboardButton("Amex Platinum ($22)", callback_data="vip_amexplat")],
                [InlineKeyboardButton("Visa Gold ($20)", callback_data="vip_visagold")],
                [InlineKeyboardButton("Amex Gold ($20)", callback_data="vip_amexgold")],
                [InlineKeyboardButton("Master Platinum ($18)", callback_data="vip_masterplat")],
                [InlineKeyboardButton("Mastercard ($10)", callback_data="vip_master")],
                [InlineKeyboardButton("Visa ($10)", callback_data="vip_visa")],
                [InlineKeyboardButton("Amex ($10)", callback_data="vip_amex")],
            ]
            await query.edit_message_text(vip_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("vip_"):
        choice = data.replace("vip_", "").capitalize()
        context.user_data["choice"] = choice
        await query.edit_message_text(
            f"You selected {choice}\nPay via UPI: {UPI_ID}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Paid", callback_data="paid")],
                [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_menu")]
            ])
        )

    elif data == "paid":
        await query.edit_message_text("Please enter your UTR below 👇")
        return WAITING_UTR

    elif data == "back_menu":
        await start(update, context)

    return ConversationHandler.END

async def receive_utr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    utr = update.message.text.strip()
    user_id = update.message.chat_id
    choice = context.user_data.get("choice", "Unknown")

    txns = load_transactions()
    txns[utr] = {"user_id": user_id, "status": "pending", "choice": choice}
    save_transactions(txns)

    keyboard = [
        [InlineKeyboardButton("🔎 Check Status", callback_data=f"status_{utr}")],
        [InlineKeyboardButton("📞 Contact Support", url="https://t.me/alone120122")]
    ]
    await update.message.reply_text(f"✅ Your UTR `{utr}` has been submitted.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    utr = query.data.split("_", 1)[1]

    txns = load_transactions()
    if utr not in txns:
        await query.edit_message_text("❌ UTR not found.")
        return

    status = txns[utr]["status"]
    if status == "pending":
        keyboard = [
            [InlineKeyboardButton("🔎 Check Status", callback_data=f"status_{utr}")],
            [InlineKeyboardButton("📞 Contact Support", url="https://t.me/alone120122")]
        ]
        msg = "⌛ Your transaction is still pending. Please wait."
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
    elif status == "approved":
        await query.edit_message_text("✅ Approved! You will receive your CC within 24 hours.",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📞 Contact Support", url="https://t.me/alone120122")]]))
    else:
        await query.edit_message_text("❌ Declined! Wrong UTR.",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📞 Contact Support", url="https://t.me/alone120122")]]))

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_buttons, pattern="^paid$")],
        states={WAITING_UTR: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_utr)]},
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons, pattern="^(list_|vip_|paid|back_menu)$"))
    app.add_handler(CallbackQueryHandler(status_handler, pattern="^status_"))
    app.add_handler(conv_handler)

    app.run_polling()

if __name__ == "__main__":
    main()
