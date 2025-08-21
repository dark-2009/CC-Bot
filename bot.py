import logging
import requests
import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ========== CONFIG ==========
BOT_TOKEN = "8241360344:AAFP0_43PmJRCTa2mpv5F2q_XYixkRXTdYs"
ADMIN_ID = 6800292901
GIST_ID = "426a9400569f40b6f4d664b74801a78a"

# Split PAT into 3 parts
PART1 = "github_pat_11BQYPIPI0rMEipIqtHj9h"
PART2 = "_vmPF0bBNpQa1F46Er4SaZHWtvQbznPNoh"
PART3 = "D9krhomlbKOPCYCJNUxpcAMUnh"
GITHUB_PAT = PART1 + PART2 + PART3

GIST_URL = f"https://api.github.com/gists/{GIST_ID}"
HEADERS = {"Authorization": f"token {GITHUB_PAT}"}
UPI_ID = "withonly.vinay@axl"
# ============================

logging.basicConfig(level=logging.INFO)

# --- Helper: Fetch CCs from GitHub Pages ---
def fetch_ccs():
    url = "https://dark-2009.github.io/CC-Bot/ccs.txt"
    try:
        resp = requests.get(url, timeout=10)
        cards = [line.strip() for line in resp.text.splitlines() if "|" in line]
        return cards
    except Exception as e:
        logging.error(f"Error fetching CCs: {e}")
        return []

def filter_cards(cards, card_type):
    result = []
    for line in cards:
        num = line.split("|")[0].strip()
        if card_type == "visa" and num.startswith("4"):
            result.append(line)
        elif card_type == "master" and num.startswith("5"):
            result.append(line)
        elif card_type == "amex" and (num.startswith("34") or num.startswith("37")):
            result.append(line)
    return result

# --- Gist Helpers ---
def load_transactions():
    try:
        r = requests.get(GIST_URL, headers=HEADERS).json()
        files = r.get("files", {})
        content = files.get("transactions.json", {}).get("content", "{}")
        return json.loads(content)
    except Exception:
        return {}

def save_transactions(data):
    payload = {"files": {"transactions.json": {"content": json.dumps(data, indent=2)}}}
    requests.patch(GIST_URL, headers=HEADERS, json=payload)

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
    ctype = query.data.replace("list_", "")

    # Free CCs
    if ctype in ["visa", "master", "amex"]:
        filtered = filter_cards(cards, ctype)
        if not filtered:
            await query.edit_message_text(f"No {ctype.upper()} cards found.")
            return

        page = 0
        text = "\n".join(filtered[page*5:(page+1)*5])
        keyboard = []
        if len(filtered) > 5:
            keyboard.append([InlineKeyboardButton("➡️ Next", callback_data=f"page_{ctype}_{page+1}")])
        await query.edit_message_text(f"Here are some {ctype.upper()} cards:\n\n{text}", reply_markup=InlineKeyboardMarkup(keyboard))

    # VIP CCs
    elif ctype == "vip":
        keyboard = [
            [InlineKeyboardButton("Amex Platinum ($22)", callback_data="vip_amexplatinum")],
            [InlineKeyboardButton("Visa Gold ($20)", callback_data="vip_visagold")],
            [InlineKeyboardButton("Amex Gold ($20)", callback_data="vip_amexgold")],
            [InlineKeyboardButton("Mastercard Platinum ($18)", callback_data="vip_masterplatinum")],
            [InlineKeyboardButton("Mastercard ($10)", callback_data="vip_master")],
            [InlineKeyboardButton("Visa ($10)", callback_data="vip_visa")],
            [InlineKeyboardButton("Amex ($10)", callback_data="vip_amex")],
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_menu")]
        ]
        await query.edit_message_text("🌟 VIP CCs 🌟\nChoose your card:", reply_markup=InlineKeyboardMarkup(keyboard))

    # VIP Selected
    elif query.data.startswith("vip_"):
        choice = query.data.replace("vip_", "")
        context.user_data["vip_choice"] = choice
        msg = f"You selected {choice.replace('_', ' ').title()}\nPay via UPI: `{UPI_ID}`"
        keyboard = [
            [InlineKeyboardButton("✅ Paid", callback_data="paid")],
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_menu")]
        ]
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    # Paid → ask UTR
    elif query.data == "paid":
        await query.edit_message_text("Please enter your UTR below 👇")
        context.user_data["awaiting_utr"] = True

    # Back to menu
    elif query.data == "back_menu":
        await start(query, context)

    # Pagination
    elif query.data.startswith("page_"):
        _, ctype, page = query.data.split("_")
        page = int(page)
        filtered = filter_cards(cards, ctype)
        text = "\n".join(filtered[page*5:(page+1)*5])
        keyboard = []
        if page > 0:
            keyboard.append([InlineKeyboardButton("⬅️ Previous", callback_data=f"page_{ctype}_{page-1}")])
        if (page+1)*5 < len(filtered):
            keyboard.append([InlineKeyboardButton("➡️ Next", callback_data=f"page_{ctype}_{page+1}")])
        await query.edit_message_text(f"{ctype.upper()} cards:\n\n{text}", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_utr"):
        utr = update.message.text.strip()
        user_id = update.message.chat_id
        txns = load_transactions()
        txns[utr] = {"user_id": user_id, "status": "pending"}
        save_transactions(txns)
        context.user_data["awaiting_utr"] = False
        await update.message.reply_text(f"✅ Your UTR `{utr}` has been submitted. Wait for admin approval.", parse_mode="Markdown")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
