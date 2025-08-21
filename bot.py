import logging, requests, json, asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ========= CONFIG =========
BOT_TOKEN = "8241360344:AAFP0_43PmJRCTa2mpv5F2q_XYixkRXTdYs"
GIST_ID = "426a9400569f40b6f4d664b74801a78a"
PART1 = "github_pat_11BQYPIPI0rMEipIqtHj9h_"
PART2 = "vmPF0bBNpQa1F46Er4SaZHWtvQbznPNohD9"
PART3 = "krhomlbKOPCYCJNUxpcAMUnh"
GITHUB_PAT = PART1 + PART2 + PART3
GIST_URL = f"https://api.github.com/gists/{GIST_ID}"
HEADERS = {"Authorization": f"token {GITHUB_PAT}"}
UPI_ID = "withonly.vinay@axl"
CCS_RAW_URL = "https://raw.githubusercontent.com/dark-2009/CC-Bot/main/ccs.txt"
# ==========================

logging.basicConfig(level=logging.INFO)

# --- Gist Helpers ---
def load_transactions():
    try:
        r = requests.get(GIST_URL, headers=HEADERS).json()
        files = r.get("files", {})
        content = files.get("transactions.json", {}).get("content", "{}")
        return json.loads(content)
    except Exception as e:
        print("Error loading txns:", e)
        return {}

def save_transactions(data):
    try:
        payload = {"files": {"transactions.json": {"content": json.dumps(data, indent=2)}}}
        requests.patch(GIST_URL, headers=HEADERS, json=payload)
    except Exception as e:
        print("Error saving txns:", e)

# --- CC Helpers ---
def fetch_ccs():
    try:
        resp = requests.get(CCS_RAW_URL)
        return resp.text.strip().splitlines()
    except:
        return []

def filter_cards(cards, ctype):
    result = []
    for line in cards:
        if "|" not in line:
            continue
        num = line.split("|")[0].strip()
        if ctype == "visa" and num.startswith("4"):
            result.append(line)
        elif ctype == "master" and num.startswith("5"):
            result.append(line)
        elif ctype == "amex" and (num.startswith("34") or num.startswith("37")):
            result.append(line)
    return result

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💳 Visa", callback_data="list_visa")],
        [InlineKeyboardButton("💳 Mastercard", callback_data="list_master")],
        [InlineKeyboardButton("💳 Amex", callback_data="list_amex")],
        [InlineKeyboardButton("🌟 VIP CCs", callback_data="vip_menu")]
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
            await query.edit_message_text("❌ No cards found in repo.")
            return

        text = "\n".join(filtered[:5])  # show first 5
        await query.edit_message_text(f"{ctype.upper()} cards:\n\n{text}")

    elif query.data == "vip_menu":
        keyboard = [
            [InlineKeyboardButton("Amex Platinum ($22)", callback_data="vip_Amex Platinum_22")],
            [InlineKeyboardButton("Visa Gold ($20)", callback_data="vip_Visa Gold_20")],
            [InlineKeyboardButton("Amex Gold ($20)", callback_data="vip_Amex Gold_20")],
            [InlineKeyboardButton("Master Platinum ($18)", callback_data="vip_Master Platinum_18")],
            [InlineKeyboardButton("Back", callback_data="back_menu")]
        ]
        await query.edit_message_text("🌟 VIP CCs 🌟\nSelect your option:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("vip_"):
        _, name, price = query.data.split("_")
        text = f"You selected {name} (${price})\nPay via UPI: {UPI_ID}"
        keyboard = [
            [InlineKeyboardButton("✅ Paid", callback_data=f"paid_{name}")],
            [InlineKeyboardButton("⬅️ Back", callback_data="vip_menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("paid_"):
        name = query.data.replace("paid_", "")
        context.user_data["waiting_utr"] = name
        await query.edit_message_text("Please enter your UTR below 👇")

    elif query.data == "back_menu":
        await start(query, context)

    elif query.data.startswith("check_"):
        utr = query.data.replace("check_", "")
        txns = load_transactions()
        if utr not in txns:
            await query.edit_message_text("❌ UTR not found.")
            return
        status = txns[utr]["status"]
        if status == "pending":
            msg = "⌛ Your transaction is pending."
        elif status == "approved":
            msg = "✅ Approved! You will receive your CC within 24 hours."
        else:
            msg = "❌ Declined. Wrong UTR."
        keyboard = [
            [InlineKeyboardButton("📞 Contact Support", url="https://t.me/alone120122")]
        ]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "waiting_utr" in context.user_data:
        utr = update.message.text.strip()
        user_id = update.message.chat_id
        name = context.user_data.pop("waiting_utr")

        txns = load_transactions()
        txns[utr] = {"user_id": user_id, "status": "pending", "cc_name": name}
        save_transactions(txns)

        keyboard = [
            [InlineKeyboardButton("⏳ Check Status", callback_data=f"check_{utr}")],
            [InlineKeyboardButton("📞 Contact Support", url="https://t.me/alone120122")]
        ]
        await update.message.reply_text(f"✅ Your UTR `{utr}` has been submitted.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def notify_user(app, utr, status):
    txns = load_transactions()
    if utr in txns:
        uid = txns[utr]["user_id"]
        if status == "approved":
            msg = "✅ Approved! You will receive your CC within 24 hours."
        else:
            msg = "❌ Declined. Wrong UTR."
        try:
            await app.bot.send_message(chat_id=uid, text=msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📞 Contact Support", url="https://t.me/alone120122")]]))
        except:
            pass

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    app.run_polling()

if __name__ == "__main__":
    main()
