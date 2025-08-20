import logging
import requests
import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ========== CONFIG ==========
ADMIN_BOT_TOKEN = "7636476146:AAFl2JDniUNsQYRFsU6BSHPVyS8sqQn0ejg"
ADMIN_CHAT_ID = 6800292901
GIST_ID = "426a9400569f40b6f4d664b74801a78a"

# Split PAT in 3 parts
PART1 = "github_pat_11BQYPIPI0rM"
PART2 = "EipIqtHj9h_vmPF0bBNpQa1F46Er"
PART3 = "4SaZHWtvQbznPNohD9krhomlbKOPCYCJNUxpcAMUnh"
GITHUB_PAT = PART1 + PART2 + PART3

GIST_URL = f"https://api.github.com/gists/{GIST_ID}"
HEADERS = {"Authorization": f"token {GITHUB_PAT}"}
# ============================

logging.basicConfig(level=logging.INFO)

# --- Helpers ---
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
    if update.message.chat_id != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Unauthorized")
        return

    txns = load_transactions()
    if not txns:
        await update.message.reply_text("No pending transactions.")
        return

    for utr, details in txns.items():
        if details["status"] == "pending":
            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_{utr}"),
                    InlineKeyboardButton("❌ Decline", callback_data=f"decline_{utr}")
                ]
            ]
            await update.message.reply_text(f"UTR: {utr}\nUser ID: {details['user_id']}\nStatus: Pending", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, utr = query.data.split("_")
    txns = load_transactions()

    if utr not in txns:
        await query.edit_message_text("❌ Transaction not found.")
        return

    if action == "approve":
        txns[utr]["status"] = "approved"
        msg = "Transaction approved ✅"
    else:
        txns[utr]["status"] = "declined"
        msg = "Transaction declined ❌"

    save_transactions(txns)
    await query.edit_message_text(f"{msg}\nUTR: {utr}")

def main():
    app = Application.builder().token(ADMIN_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.run_polling()

if __name__ == "__main__":
    main()
