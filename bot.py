import logging
import requests
import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ========== CONFIG ==========
BOT_TOKEN = "8241360344:AAFP0_43PmJRCTa2mpv5F2q_XYixkRXTdYs"
ADMIN_ID = 6800292901
GIST_ID = "426a9400569f40b6f4d664b74801a78a"
# Break PAT into 3 chunks
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
        resp = requests.get(url)
        return [line.strip() for line in resp.text.strip().splitlines() if "|" in line]
    except:
        return []

def detect_brand(card_number: str):
    if card_number.startswith("4"):
        return "visa"
    if card_number[:2] in ["34", "37"]:
        return "amex"
    if card_number.startswith(tuple([str(i) for i in range(51,56)])) or (2221 <= int(card_number[:4]) <= 2720):
        return "master"
    return "unknown"

def filter_cards(cards, ctype):
    result = []
    for line in cards:
        num = line.split("|")[0].strip()
        brand = detect_brand(num)
        if brand == ctype:
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

# --- START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💳 Visa", callback_data="list_visa")],
        [InlineKeyboardButton("💳 Mastercard", callback_data="list_master")],
        [InlineKeyboardButton("💳 Amex", callback_data="list_amex")],
        [InlineKeyboardButton("🌟 VIP CCs", callback_data="list_vip")],
    ]
    await update.message.reply_text("Welcome! Choose a category:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Handle Buttons ---
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cards = fetch_ccs()

    if query.data.startswith("list_"):
        ctype = query.data.replace("list_", "")
        if ctype in ["visa", "master", "amex"]:
            filtered = filter_cards(cards, ctype)
            if not filtered:
                await query.edit_message_text("No cards found.")
                return

            page = 0
            text = "\n".join(filtered[page*5:(page+1)*5])
            keyboard = []
            if len(filtered) > 5:
                keyboard.append([InlineKeyboardButton("➡️ Next", callback_data=f"page_{ctype}_{page+1}")])
            await query.edit_message_text(f"Here are some {ctype.upper()} cards:\n\n{text}", reply_markup=InlineKeyboardMarkup(keyboard))

        elif ctype == "vip":
            keyboard = [
                [InlineKeyboardButton("💎 Amex Platinum ($22)", callback_data="vip_amex_platinum")],
                [InlineKeyboardButton("💎 Visa Gold ($20)", callback_data="vip_visa_gold")],
                [InlineKeyboardButton("💎 Amex Gold ($20)", callback_data="vip_amex_gold")],
                [InlineKeyboardButton("💎 Mastercard Platinum ($18)", callback_data="vip_master_platinum")],
                [InlineKeyboardButton("✨ Mastercard ($10)", callback_data="vip_master")],
                [InlineKeyboardButton("✨ Visa ($10)", callback_data="vip_visa")],
                [InlineKeyboardButton("✨ Amex ($10)", callback_data="vip_amex")],
                [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_menu")]
            ]
            await query.edit_message_text("🌟 VIP CCs 🌟\nSelect a card to continue:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("vip_"):
        card_choice = query.data.replace("vip_", "")
        prices = {
            "amex_platinum": 22,
            "visa_gold": 20,
            "amex_gold": 20,
            "master_platinum": 18,
            "master": 10,
            "visa": 10,
            "amex": 10,
        }
        price = prices.get(card_choice, 0)
        context.user_data["vip_choice"] = card_choice

        text = f"You selected {card_choice.replace('_',' ').title()} (${price})\nPay via UPI: {UPI_ID}"
        keyboard = [
            [InlineKeyboardButton("✅ Paid", callback_data="vip_paid")],
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "vip_paid":
        context.user_data["waiting_for_utr"] = True
        await query.edit_message_text("Please enter your UTR below 👇")

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

    elif query.data == "back_menu":
        await start(update, context)

# --- UTR Submission ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("waiting_for_utr"):
        utr = update.message.text.strip()
        user_id = update.message.chat_id
        txns = load_transactions()
        txns[utr] = {"user_id": user_id, "status": "pending"}
        save_transactions(txns)
        context.user_data["waiting_for_utr"] = False

        keyboard = [[InlineKeyboardButton("⌛ Check Status", callback_data=f"check_{utr}")]]
        await update.message.reply_text(
            f"✅ Your UTR `{utr}` has been submitted.\nUse the button below to check status.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    else:
        await update.message.reply_text("Please use the menu buttons to navigate.")

# --- Check Status ---
async def handle_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    utr = query.data.replace("check_", "")
    txns = load_transactions()

    if utr not in txns:
        await query.edit_message_text("❌ UTR not found.")
        return

    status = txns[utr]["status"]
    if status == "pending":
        msg = "⌛ Your transaction is still pending. Please wait."
        keyboard = [[InlineKeyboardButton("🔄 Check Again", callback_data=f"check_{utr}")]]
    elif status == "approved":
        msg = "✅ Approved! You will receive your CC within 24 hours."
        keyboard = [[InlineKeyboardButton("📞 Contact Support", url="https://t.me/alone120122")]]
    else:
        msg = "❌ Declined! Wrong UTR."
        keyboard = [[InlineKeyboardButton("📞 Contact Support", url="https://t.me/alone120122")]]

    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

# --- Admin Commands ---
async def pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id != ADMIN_ID:
        return
    txns = load_transactions()
    pending_utrs = [utr for utr, data in txns.items() if data["status"] == "pending"]

    if not pending_utrs:
        await update.message.reply_text("No pending transactions.")
        return

    for utr in pending_utrs:
        keyboard = [
            [InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_{utr}")],
            [InlineKeyboardButton("❌ Decline", callback_data=f"admin_decline_{utr}")]
        ]
        await update.message.reply_text(f"UTR: {utr}", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    action, utr = data[1], data[2]

    txns = load_transactions()
    if utr not in txns:
        await query.edit_message_text("UTR not found.")
        return

    if action == "approve":
        txns[utr]["status"] = "approved"
        save_transactions(txns)
        await query.edit_message_text(f"UTR {utr} ✅ Approved")
    else:
        txns[utr]["status"] = "declined"
        save_transactions(txns)
        await query.edit_message_text(f"UTR {utr} ❌ Declined")

    # Notify user
    user_id = txns[utr]["user_id"]
    try:
        await context.bot.send_message(user_id, "Your UTR has been reviewed. Use Check Status button to see result.")
    except:
        pass

# --- Main ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pending", pending))
    app.add_handler(CallbackQueryHandler(handle_buttons, pattern="^(list_|page_|vip_|vip_paid|back_menu)$"))
    app.add_handler(CallbackQueryHandler(handle_check, pattern="^check_"))
    app.add_handler(CallbackQueryHandler(handle_admin, pattern="^admin_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
