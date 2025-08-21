import logging
import requests
import json
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ========== CONFIG ==========
BOT_TOKEN = "8241360344:AAFP0_43PmJRCTa2mpv5F2q_XYixkRXTdYs"
GIST_ID = "426a9400569f40b6f4d664b74801a78a"
PART1 = "github_pat_11BQYPIPI0rMEipIqtHj9h_"
PART2 = "vmPF0bBNpQa1F46Er4SaZHWtvQbznPNohD9"
PART3 = "krhomlbKOPCYCJNUxpcAMUnh"

GITHUB_PAT = PART1 + PART2 + PART
GIST_URL = f"https://api.github.com/gists/{GIST_ID}"
HEADERS = {"Authorization": f"token {GITHUB_PAT}"}
UPI_ID = "withonly.vinay@axl"
ADMIN_ID = 6800292901
# ============================

logging.basicConfig(level=logging.INFO)

# --- Helper: Fetch CCs ---
def fetch_ccs():
    url = "https://raw.githubusercontent.com/dark-2009/CC-Bot/main/ccs.txt"
    try:
        resp = requests.get(url)
        return resp.text.strip().splitlines()
    except Exception as e:
        logging.error(f"Error fetching ccs: {e}")
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

# --- Gist Helper ---
def load_transactions():
    try:
        r = requests.get(GIST_URL, headers=HEADERS).json()
        files = r.get("files", {})
        content = files.get("transactions.json", {}).get("content", "{}")
        return json.loads(content)
    except Exception as e:
        logging.error(f"Load txns error: {e}")
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
        [InlineKeyboardButton("🌟 VIP CCs", callback_data="vip_menu")],
    ]
    await update.message.reply_text("Welcome! Choose a category:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cards = fetch_ccs()

    if query.data.startswith("list_"):
        ctype = query.data.replace("list_", "")
        filtered = filter_cards(cards, ctype)
        if not filtered:
            await query.edit_message_text("No cards found.")
            return
        text = "\n".join(filtered[:5])
        await query.edit_message_text(f"{ctype.upper()} cards:\n\n{text}")

    elif query.data == "vip_menu":
        keyboard = [
            [InlineKeyboardButton("💎 Amex Platinum ($22)", callback_data="vip_amexplat")],
            [InlineKeyboardButton("💎 Visa Gold ($20)", callback_data="vip_visagold")],
            [InlineKeyboardButton("💎 Amex Gold ($20)", callback_data="vip_amexgold")],
            [InlineKeyboardButton("💎 Mastercard Platinum ($18)", callback_data="vip_masterplat")],
            [InlineKeyboardButton("✨ Mastercard ($10)", callback_data="vip_master")],
            [InlineKeyboardButton("✨ Visa ($10)", callback_data="vip_visa")],
            [InlineKeyboardButton("✨ Amex ($10)", callback_data="vip_amex")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_home")],
        ]
        await query.edit_message_text("🌟 VIP CCs 🌟\nSelect a plan:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("vip_"):
        plan = query.data.replace("vip_", "").capitalize()
        context.user_data["selected_plan"] = plan
        await query.edit_message_text(
            f"You selected {plan}\nPay via UPI: `{UPI_ID}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Paid", callback_data="paid"), InlineKeyboardButton("⬅️ Back", callback_data="vip_menu")]
            ])
        )

    elif query.data == "paid":
        await query.edit_message_text("Please enter your UTR below 👇")
        context.user_data["waiting_utr"] = True

    elif query.data == "back_home":
        await start(query, context)

async def text_catcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("waiting_utr"):
        utr = update.message.text.strip()
        user_id = update.message.chat_id
        txns = load_transactions()
        txns[utr] = {"user_id": user_id, "status": "pending"}
        save_transactions(txns)
        context.user_data["waiting_utr"] = False

        keyboard = [
            [InlineKeyboardButton("🔄 Check Status", callback_data=f"check_{utr}")],
            [InlineKeyboardButton("📞 Contact Support", url="https://t.me/alone120122")]
        ]
        await update.message.reply_text(f"✅ UTR `{utr}` submitted.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def check_status(query, utr):
    txns = load_transactions()
    if utr not in txns:
        return "❌ UTR not found."

    status = txns[utr]["status"]
    if status == "pending":
        return "⌛ Pending. Please wait."
    elif status == "approved":
        return "✅ Approved! You will receive your CC within 24 hours."
    else:
        return "❌ Declined. Wrong UTR."

async def handle_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    utr = query.data.replace("check_", "")
    msg = await check_status(query, utr)
    keyboard = [[InlineKeyboardButton("📞 Contact Support", url="https://t.me/alone120122")]]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

# --- Admin commands ---
async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id != ADMIN_ID:
        return
    await update.message.reply_text("Admin commands:\n/pending\n/find <UTR>\n/set <UTR> approved|declined")

async def admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id != ADMIN_ID:
        return
    txns = load_transactions()
    pending = [utr for utr, d in txns.items() if d["status"] == "pending"]
    await update.message.reply_text("Pending:\n" + "\n".join(pending) if pending else "No pending.")

async def admin_find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id != ADMIN_ID:
        return
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /find <UTR>")
        return
    utr = context.args[0]
    txns = load_transactions()
    await update.message.reply_text(str(txns.get(utr, "Not found")))

async def admin_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id != ADMIN_ID:
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /set <UTR> approved|declined")
        return
    utr, status = context.args[0], context.args[1]
    txns = load_transactions()
    if utr not in txns:
        await update.message.reply_text("UTR not found.")
        return
    txns[utr]["status"] = status
    save_transactions(txns)

    user_id = txns[utr]["user_id"]
    text = "✅ Approved! You will receive your CC within 24 hours. Contact support below." if status == "approved" else "❌ Declined! Wrong UTR. Contact support below."
    keyboard = [[InlineKeyboardButton("📞 Contact Support", url="https://t.me/alone120122")]]
    await context.bot.send_message(chat_id=user_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))
    await update.message.reply_text(f"UTR {utr} set to {status} and user notified.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons, pattern="^(list_|vip_|paid|back_home)$"))
    app.add_handler(CallbackQueryHandler(handle_check, pattern="^check_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_catcher))
    app.add_handler(CommandHandler("admin", admin_start))
    app.add_handler(CommandHandler("pending", admin_pending))
    app.add_handler(CommandHandler("find", admin_find))
    app.add_handler(CommandHandler("set", admin_set))
    app.run_polling()

if __name__ == "__main__":
    main()
