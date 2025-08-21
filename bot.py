import logging, requests, json, asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CONFIG ---
BOT_TOKEN = "8241360344:AAFP0_43PmJRCTa2mpv5F2q_XYixkRXTdYs"
GIST_ID = "426a9400569f40b6f4d664b74801a78a"
PART1 = "github_pat_11BQYPIPI0rMEipIqtHj9h"
PART2 = "_vmPF0bBNpQa1F46Er4SaZHWtvQbznPNoh"
PART3 = "D9krhomlbKOPCYCJNUxpcAMUnh"
GITHUB_PAT = PART1 + PART2 + PART3
GIST_URL = f"https://api.github.com/gists/{GIST_ID}"
HEADERS = {"Authorization": f"token {GITHUB_PAT}"}
UPI_ID = "withonly.vinay@axl"
SUPPORT_URL = "https://t.me/alone120122"

logging.basicConfig(level=logging.INFO)

# --- Fetch Free CCs ---
def fetch_ccs():
    url = "https://raw.githubusercontent.com/dark-2009/CC-Bot/main/ccs.txt"
    try:
        resp = requests.get(url)
        return [line.strip() for line in resp.text.splitlines() if "|" in line]
    except:
        return []

def filter_cards(cards, card_type):
    result = []
    for line in cards:
        num = line.split("|")[0].strip()
        if card_type == "visa" and num.startswith("4"): result.append(line)
        elif card_type == "master" and num.startswith("5"): result.append(line)
        elif card_type == "amex" and (num.startswith("34") or num.startswith("37")): result.append(line)
    return result

# --- Gist Helpers ---
def load_transactions():
    r = requests.get(GIST_URL, headers=HEADERS).json()
    content = r.get("files", {}).get("transactions.json", {}).get("content", "{}")
    return json.loads(content)

def save_transactions(data):
    payload = {"files": {"transactions.json": {"content": json.dumps(data, indent=2)}}}
    requests.patch(GIST_URL, headers=HEADERS, json=payload)

# --- User Cache (to notify later) ---
user_txn_cache = {}   # utr -> status (to track changes)

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💳 Visa", callback_data="list_visa")],
        [InlineKeyboardButton("💳 Mastercard", callback_data="list_master")],
        [InlineKeyboardButton("💳 Amex", callback_data="list_amex")],
        [InlineKeyboardButton("🌟 VIP CCs", callback_data="list_vip")],
    ]
    await update.message.reply_text("Choose a category:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cards = fetch_ccs()

    if query.data.startswith("list_"):
        ctype = query.data.replace("list_", "")
        filtered = filter_cards(cards, ctype)
        if not filtered:
            await query.edit_message_text("❌ No cards found.")
            return
        text = "\n".join(filtered[:5])
        await query.edit_message_text(f"Here are {ctype.upper()} cards:\n\n{text}")

    elif query.data == "list_vip":
        vip_text = f"""
🌟 *VIP CCs* 🌟
Pay via UPI: `{UPI_ID}`

💎 Very Premium (Balance 20–30k INR):
- Amex Platinum: $22
- Visa Gold: $20
- Amex Gold: $20
- Mastercard Platinum: $18

✨ Good Category (Balance up to 10k INR):
- Mastercard: $10
- Visa: $10
- Amex: $10
"""
        vip_keyboard = [
            [InlineKeyboardButton("Amex Platinum - $22", callback_data="vip_amex_platinum")],
            [InlineKeyboardButton("Visa Gold - $20", callback_data="vip_visa_gold")],
            [InlineKeyboardButton("Amex Gold - $20", callback_data="vip_amex_gold")],
            [InlineKeyboardButton("Master Platinum - $18", callback_data="vip_master_platinum")],
            [InlineKeyboardButton("⬅️ Back", callback_data="menu")]
        ]
        await query.edit_message_text(vip_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(vip_keyboard))

    elif query.data.startswith("vip_"):
        choice = query.data.replace("vip_", "").replace("_", " ").title()
        context.user_data["selected_vip"] = choice
        await query.edit_message_text(
            f"You selected {choice}\nPay via UPI: `{UPI_ID}`\n\nClick Paid after payment.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Paid", callback_data="paid")],
                [InlineKeyboardButton("⬅️ Back", callback_data="list_vip")]
            ]))

    elif query.data == "paid":
        await query.edit_message_text("Please enter your UTR below 👇")
        context.user_data["awaiting_utr"] = True

    elif query.data == "menu":
        await start(query, context)

    elif query.data.startswith("status_"):
        utr = query.data.replace("status_", "")
        txns = load_transactions()
        if utr not in txns:
            await query.edit_message_text("❌ UTR not found.")
            return
        status = txns[utr]["status"]
        if status == "pending":
            msg = "⌛ Your transaction is still pending."
        elif status == "approved":
            msg = "✅ Approved! You will receive your CC within 24 hours."
        else:
            msg = "❌ Declined! Wrong UTR."
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📞 Contact Support", url=SUPPORT_URL)]
        ]))

async def capture_utr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_utr"):
        utr = update.message.text.strip()
        user_id = update.message.chat_id
        txns = load_transactions()
        txns[utr] = {"user_id": user_id, "status": "pending"}
        save_transactions(txns)

        keyboard = [
            [InlineKeyboardButton("🔍 Check Status", callback_data=f"status_{utr}")],
            [InlineKeyboardButton("📞 Contact Support", url=SUPPORT_URL)]
        ]
        await update.message.reply_text(f"✅ Your UTR `{utr}` has been submitted.", parse_mode="Markdown",
                                        reply_markup=InlineKeyboardMarkup(keyboard))
        context.user_data["awaiting_utr"] = False
        user_txn_cache[utr] = "pending"

# --- Background Polling: Notify Users ---
async def poll_transactions(app: Application):
    while True:
        txns = load_transactions()
        for utr, info in txns.items():
            if utr not in user_txn_cache:
                user_txn_cache[utr] = info["status"]
            elif user_txn_cache[utr] != info["status"]:
                # Status changed → notify user
                chat_id = info["user_id"]
                status = info["status"]
                if status == "approved":
                    msg = "✅ Approved! You will receive your CC within 24 hours."
                elif status == "declined":
                    msg = "❌ Declined! Wrong UTR."
                else:
                    msg = "⌛ Your transaction is still pending."

                try:
                    await app.bot.send_message(chat_id, msg, reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📞 Contact Support", url=SUPPORT_URL)]
                    ]))
                except:
                    pass
                user_txn_cache[utr] = status
        await asyncio.sleep(15)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, capture_utr))
    app.job_queue.run_repeating(lambda ctx: asyncio.create_task(poll_transactions(app)), interval=20, first=5)
    app.run_polling()

if __name__ == "__main__":
    main()
