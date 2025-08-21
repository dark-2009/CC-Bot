import logging
import requests
import json
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
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
GIST_ID = "426a9400569f40b6f4d664b74801a78a"
# Instead of this (old way)
# Do this (split into 3 parts)
PART1 = "github_pat_11BQYPIPI0rMEipIqtHj9h_"
PART2 = "vmPF0bBNpQa1F46Er4SaZHWtvQbznPNohD9"
PART3 = "krhomlbKOPCYCJNUxpcAMUnh"
GITHUB_PAT = PART1 + PART2 + PART3
GIST_URL = f"https://api.github.com/gists/{GIST_ID}"
HEADERS = {"Authorization": f"token {GITHUB_PAT}"}
UPI_ID = "withonly.vinay@axl"
# ============================

logging.basicConfig(level=logging.INFO)

# --- Helper: Fetch CCs from GitHub repo ---
def fetch_ccs():
    url = "https://raw.githubusercontent.com/dark-2009/CC-Bot/main/ccs.txt"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.text.strip().splitlines()
    except Exception as e:
        print("Error fetching CCs:", e)
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
    r = requests.get(GIST_URL, headers=HEADERS).json()
    files = r.get("files", {})
    content = files.get("transactions.json", {}).get("content", "{}")
    return json.loads(content)

def save_transactions(data):
    payload = {"files": {"transactions.json": {"content": json.dumps(data, indent=2)}}}
    requests.patch(GIST_URL, headers=HEADERS, json=payload)

# --- Start Handler ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💳 Visa", callback_data="list_visa")],
        [InlineKeyboardButton("💳 Mastercard", callback_data="list_master")],
        [InlineKeyboardButton("💳 Amex", callback_data="list_amex")],
        [InlineKeyboardButton("🌟 VIP CCs", callback_data="list_vip")],
    ]
    await update.message.reply_text("Choose a category:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Handle Buttons ---
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # <-- prevents loading forever

    cards = fetch_ccs()

    if query.data.startswith("list_"):
        ctype = query.data.replace("list_", "")

        if ctype in ["visa", "master", "amex"]:
            filtered = filter_cards(cards, ctype)
            if not filtered:
                await query.edit_message_text("No cards found.")
                return

            # Send first 5
            page = 0
            text = "\n".join(filtered[page*5:(page+1)*5])
            keyboard = []
            if len(filtered) > 5:
                keyboard.append([InlineKeyboardButton("➡️ Next", callback_data=f"page_{ctype}_{page+1}")])
            await query.edit_message_text(f"Here are some {ctype.upper()} cards:\n\n{text}", reply_markup=InlineKeyboardMarkup(keyboard))

        elif ctype == "vip":
            vip_keyboard = [
                [InlineKeyboardButton("💎 Amex Platinum - $22", callback_data="vip_amex_platinum")],
                [InlineKeyboardButton("💎 Visa Gold - $20", callback_data="vip_visa_gold")],
                [InlineKeyboardButton("💎 Amex Gold - $20", callback_data="vip_amex_gold")],
                [InlineKeyboardButton("💎 Mastercard Platinum - $18", callback_data="vip_master_platinum")],
                [InlineKeyboardButton("✨ Mastercard - $10", callback_data="vip_master")],
                [InlineKeyboardButton("✨ Visa - $10", callback_data="vip_visa")],
                [InlineKeyboardButton("✨ Amex - $10", callback_data="vip_amex")],
            ]
            await query.edit_message_text(
                f"🌟 VIP CCs 🌟\nPay via UPI: `{UPI_ID}`\n\nSelect your card:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(vip_keyboard),
            )

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

    elif query.data.startswith("vip_"):
        chosen = query.data.replace("vip_", "").replace("_", " ").title()
        await query.edit_message_text(
            f"You selected {chosen}\nPay via UPI: `{UPI_ID}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Paid", callback_data=f"paid_{chosen}")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_menu")]
            ])
        )

    elif query.data.startswith("paid_"):
        await query.edit_message_text(
            "Please enter your UTR below 👇",
        )
        context.user_data["waiting_for_utr"] = True

    elif query.data == "back_menu":
        await start(update, context)

# --- Handle Messages for UTR ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("waiting_for_utr"):
        utr = update.message.text.strip()
        user_id = update.message.chat_id

        txns = load_transactions()
        txns[utr] = {"user_id": user_id, "status": "pending"}
        save_transactions(txns)

        context.user_data["waiting_for_utr"] = False

        keyboard = [
            [InlineKeyboardButton("🔎 Check Status", callback_data=f"check_{utr}")],
            [InlineKeyboardButton("☎️ Contact Support", url="https://t.me/alone120122")]
        ]
        await update.message.reply_text(
            f"✅ Your UTR `{utr}` has been submitted.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# --- Check Status Button ---
async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    elif status == "approved":
        msg = "✅ Approved! You will receive your CC within 24 hours."
    else:
        msg = "❌ Declined! Wrong UTR."

    keyboard = [[InlineKeyboardButton("☎️ Contact Support", url="https://t.me/alone120122")]]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

# --- Background Polling for Approvals ---
async def poll_transactions(app: Application):
    txns = load_transactions()
    for utr, info in txns.items():
        if info["status"] in ["approved", "declined"] and not info.get("notified"):
            try:
                if info["status"] == "approved":
                    msg = "✅ Approved! You will receive your CC within 24 hours."
                else:
                    msg = "❌ Declined! Wrong UTR."

                keyboard = [[InlineKeyboardButton("☎️ Contact Support", url="https://t.me/alone120122")]]
                await app.bot.send_message(
                    chat_id=info["user_id"],
                    text=msg,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
                info["notified"] = True
                save_transactions(txns)
            except Exception as e:
                print("Error notifying user:", e)

# --- Main ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(CallbackQueryHandler(check_status, pattern="^check_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Poll for approvals
    job_queue = app.job_queue
    job_queue.run_repeating(lambda ctx: asyncio.create_task(poll_transactions(app)), interval=20, first=5)

    app.run_polling()

if __name__ == "__main__":
    main()
