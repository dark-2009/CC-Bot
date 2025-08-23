import random
import json
import xml.etree.ElementTree as ET
import io
import logging
from datetime import datetime

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ------------------------------------------------------------------------------------------
# CONFIG
BOT_TOKEN = "8241360344:AAFP0_43PmJRCTa2mpv5F2q_XYixkRXTdYs"  # <---- replace with your bot token
GIST_ID_TXN = "426a9400569f40b6f4d664b74801a78a"  # transactions gist
GIST_ID_CCS = "065082e31d1aed3b8d728dbd728fbc62"  # ccs gist
GITHUB_PAT = "github_pat_11BQYPIPI0boMKyo1ZCgKa_LMmfMm9vac" + "bpv1upw9PQ1mT7l2DQ3r24JDeTOOz1o5e" + "PTEH7RT4RE861P9f"  # <-- split your PAT here like before

GIST_URL_TXN = f"https://api.github.com/gists/{GIST_ID_TXN}"
GIST_URL_CCS = f"https://api.github.com/gists/{GIST_ID_CCS}"
HEADERS = {"Authorization": f"token {GITHUB_PAT}"}

UPI_ID = "withonly.vinay@axl"
SUPPORT_LINK = "https://t.me/alone120122"

# ------------------------------------------------------------------------------------------
# Logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------------------
# CC GENERATOR CLASS (from your provided script, trimmed slightly)
class CCGenerator:
    def __init__(self):
        self.card_data = []
        self.country_codes = {
            'US': 'United States', 'GB': 'United Kingdom', 'CA': 'Canada',
            'AU': 'Australia', 'DE': 'Germany', 'FR': 'France', 'JP': 'Japan',
        }
        self.bin_db = {
            '4': {'brand': 'Visa', 'length': 16},
            '5': {'brand': 'Mastercard', 'length': 16},
            '34': {'brand': 'American Express', 'length': 15},
            '37': {'brand': 'American Express', 'length': 15},
            '6011': {'brand': 'Discover', 'length': 16},
        }

    def get_bin_info(self, bin_number):
        first_digit = bin_number[0]
        if first_digit == '3':
            return {'brand': 'American Express', 'length': 15}
        elif first_digit == '4':
            return {'brand': 'Visa', 'length': 16}
        elif first_digit == '5':
            return {'brand': 'Mastercard', 'length': 16}
        elif first_digit == '6':
            return {'brand': 'Discover', 'length': 16}
        return {'brand': 'Unknown', 'length': 16}

    def luhn_checksum(self, card_number):
        def digits_of(n): return [int(d) for d in str(n)]
        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        return checksum % 10

    def calculate_luhn(self, partial_card):
        check_digit = self.luhn_checksum(int(partial_card) * 10)
        return check_digit if check_digit == 0 else 10 - check_digit

    def generate_card(self, bin_number):
        bin_info = self.get_bin_info(bin_number)
        card_length = bin_info['length']
        needed_length = card_length - len(bin_number) - 1
        account_number = ''.join([str(random.randint(0, 9)) for _ in range(needed_length)])
        partial_card = bin_number + account_number
        luhn_digit = self.calculate_luhn(partial_card)
        card_number = partial_card + str(luhn_digit)
        exp_month = f"{random.randint(1, 12):02d}"
        exp_year = f"{(datetime.now().year + random.randint(1, 5)) % 100:02d}"
        cvv_length = 4 if bin_info.get('brand') == 'American Express' else 3
        cvv = f"{random.randint(0, 9999 if cvv_length == 4 else 999):0{cvv_length}d}"
        return f"{card_number}|{exp_month}|{exp_year}|{cvv} ({bin_info['brand']})"

generator = CCGenerator()
user_states = {}

# ------------------------------------------------------------------------------------------
# Helpers: Gist
def load_transactions():
    try:
        r = requests.get(GIST_URL_TXN, headers=HEADERS).json()
        files = r.get("files", {})
        content = files.get("transactions.json", {}).get("content", "{}")
        return json.loads(content)
    except Exception as e:
        logger.error(f"load_transactions: {e}")
        return {}

def save_transactions(data):
    try:
        payload = {"files": {"transactions.json": {"content": json.dumps(data, indent=2)}}}
        requests.patch(GIST_URL_TXN, headers=HEADERS, json=payload)
    except Exception as e:
        logger.error(f"save_transactions: {e}")

def fetch_ccs_from_gist():
    try:
        r = requests.get(GIST_URL_CCS, headers=HEADERS).json()
        files = r.get("files", {})
        content = files.get("ccs.txt", {}).get("content", "")
        return content.strip().splitlines()
    except Exception as e:
        logger.error(f"fetch_ccs_from_gist: {e}")
        return []

def filter_cards(cards, brand):
    result = []
    for line in cards:
        if "Card:" in line:
            if brand == "visa" and "|4" in line:
                result.append(line)
            elif brand == "master" and "|5" in line:
                result.append(line)
            elif brand == "amex" and "|3" in line:
                result.append(line)
    return result

# ------------------------------------------------------------------------------------------
# Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("ð³ Visa", callback_data="list_visa")],
        [InlineKeyboardButton("ð³ Mastercard", callback_data="list_master")],
        [InlineKeyboardButton("ð³ Amex", callback_data="list_amex")],
        [InlineKeyboardButton("â¡ CC-GEN", callback_data="ccgen")],
        [InlineKeyboardButton("ð VIP CCs", callback_data="vipcc")],
    ]
    await update.message.reply_text("Welcome! Choose an option:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # Free CCs
    if data.startswith("list_"):
        brand = data.replace("list_", "")
        cards = fetch_ccs_from_gist()
        filtered = filter_cards(cards, brand)
        if not filtered:
            await query.edit_message_text("â No cards found. (Check gist ccs.txt)")
            return
        await query.edit_message_text("\n".join(filtered[:5]))

    # VIP CCs
    elif data == "vipcc":
        text = f"""ð VIP CCs ð

ð Very Premium (Balance up to 250 - 400$ ):
- Amex Platinum: $22
- Visa Gold: $20
- Amex Gold: $20
- Mastercard Platinum: $18

â¨ Good Category (Balance up to 100 - 150$):
- Mastercard: $10
- Visa: $10
- Amex: $10

Pay via UPI: `{UPI_ID}`
"""
        await query.edit_message_text(text, parse_mode="Markdown")

    # CC Generator
    elif data == "ccgen":
        user_states[user_id] = "awaiting_bin"
        await query.edit_message_text("Enter a BIN (6 digits):")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    state = user_states.get(user_id)
    if state == "awaiting_bin":
        bin_number = update.message.text.strip()
        if not bin_number.isdigit():
            await update.message.reply_text("â Invalid BIN.")
            return
        user_states[user_id] = "awaiting_qty"
        context.user_data["bin"] = bin_number
        await update.message.reply_text("How many cards to generate? (max 10)")
    elif state == "awaiting_qty":
        qty = int(update.message.text.strip())
        if qty > 10: qty = 10
        bin_number = context.user_data["bin"]
        cards = [generator.generate_card(bin_number) for _ in range(qty)]
        await update.message.reply_text("\n".join(cards))
        del user_states[user_id]

# ------------------------------------------------------------------------------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
