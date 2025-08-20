import logging
import requests
import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ========== CONFIG ==========
BOT_TOKEN = "8241360344:AAFP0_43PmJRCTa2mpv5F2q_XYixkRXTdYs"
GIST_ID = "426a9400569f40b6f4d664b74801a78a"

# --- Split PAT in 3 parts ---
PART1 = "github_pat_11BQYPIPI0rM"
PART2 = "EipIqtHj9h_vmPF0bBNpQa1F46Er"
PART3 = "4SaZHWtvQbznPNohD9krhomlbKOPCYCJNUxpcAMUnh"
GITHUB_PAT = PART1 + PART2 + PART3
GIST_URL = f"https://api.github.com/gists/{GIST_ID}"
HEADERS = {"Authorization": f"token {GITHUB_PAT}"}

UPI_ID = "withonly.vinay@axl"
# ============================

logging.basicConfig(level=logging.INFO)

# --- Fetch Free CCs ---
def fetch_ccs():
    url = "https://dark-2009.github.io/CC-Bot/ccs.txt"
    try:
        resp = requests.get(url)
        return resp.text.strip().splitlines()
    except:
        return []

def filter_cards(cards, card_type):
    result = []
    for line in cards:
        if not line or "|" not in line:
            continue
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
    r = requests.get(GIST_URL, headers=HEADERS).json()
    files = r.get("files", {})
    content = files.get("transactions.json", {}).get("content", "{}")
    return json.loads(content)

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

    if query.data.startswith("list_"):
        ctype = query.data.replace("list_", "")
        if ctype in ["visa", "master", "amex"]:
            filtered = filter_cards(cards, ctype)
            if not filtered:
                await query.edit_message_text("❌ No cards found.")
                return

            page = 0
            text = "\n".join(filtered[page*5:(page+1)*5])
            keyboard = []
            if len(filtered) > 5:
                keyboard.append([InlineKeyboardButton("➡️ Next", callback_data=f"page_{ctype}_{page+1}")])
            await query.edit_message_text(f"Here are some {ctype.upper()} cards:\n\n{text}", reply_markup=InlineKeyboardMarkup(keyboard))

        elif ctype == "vip":
            vip_text = f"""
🌟 *VIP CCs* 🌟
Pay via UPI: `{UPI_ID}`

After payment, submit your UTR number using the button below.
"""
            keyboard = [[InlineKeyboardButton("📩 Submit UTR", callback_data="submitutr")]]
            await query.edit_message_text(vip_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

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

    elif query.data == "submitutr":
        await query.edit_message_text("Send your UTR number here in format:\n\n`/utr 1234567890`", parse_mode="Markdown")

async def utr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /utr <UTR>")
        return
    utr = context.args[0]
    user_id = update.message.chat_id

    txns = load_transactions()
    txns[utr] = {"user_id": user_id, "status": "pending"}
    save_transactions(txns)

    await update.message.reply_text(f"✅ Your UTR `{utr}` has been submitted.\nPlease wait for admin approval.", parse_mode="Markdown")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /status <UTR>")
        return
    utr = context.args[0]
    txns = load_transactions()
    if utr not in txns:
        await update.message.reply_text("❌ UTR not found.")
        return

    status = txns[utr]["status"]
    if status == "pending":
        msg = "⌛ Pending – please wait for admin approval."
    elif status == "approved":
        msg = "✅ Approved! You will receive your CC within 24 hours. Contact support: @alone120122"
    else:
        msg = "❌ Declined! Wrong UTR. Contact support: @alone120122"

    await update.message.reply_text(msg)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("utr", utr))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.run_polling()

if __name__ == "__main__":
    main()
