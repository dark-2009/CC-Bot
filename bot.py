import random, json, io, logging, requests, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ---------------- CONFIG ----------------
BOT_TOKEN = "8241360344:AAFP0_43PmJRCTa2mpv5F2q_XYixkRXTdYs"
GIST_ID_TXN = "426a9400569f40b6f4d664b74801a78a"
GITHUB_PAT = ("github_pat_11BQYPIPI0boMKyo1ZCgKa_LMmfMm9vac"
              "bpv1upw9PQ1mT7l2DQ3r24JDeTOOz1o5ePTEH7RT4RE861P9f")
HEADERS = {"Authorization": f"token {GITHUB_PAT}"}

GIST_URL_TXN = f"https://api.github.com/gists/{GIST_ID_TXN}"
JOIN_CHANNEL = "https://t.me/fuckincarders"
SUPPORT_LINK = "https://t.me/alone120122"
UPI_ID = "withonly.vinay@axl"

user_states = {}
joined_users = set()

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
        first_digit = bin_number[0]
        return self.BIN_DATA.get(first_digit, {"brand":"Unknown","length":16,"bank":"Unknown","country":"US"})

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
        return (f"Card: {card_number} | {exp} |\n"
                f"CVV: {cvv}\n"
                f"BIN: {bin_number}\n"
                f"Bank: {info['bank']}\n"
                f"Brand: {info['brand']}\n"
                f"Country: {info['country']}\n"
                f"Status: Approved\n")

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

# ---------------- BOT HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in joined_users:
        await send_dashboard(update, context)
        return
    keyboard = [[InlineKeyboardButton("✅ I have joined", callback_data="joined_channel")]]
    await update.message.reply_text(
        f"Please join our channel to access the bot:\n{JOIN_CHANNEL}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def send_dashboard(update, context):
    keyboard = [
        [InlineKeyboardButton("💳 Free CCs", callback_data="free_cc")],
        [InlineKeyboardButton("⚡ CC-GEN", callback_data="ccgen")],
        [InlineKeyboardButton("🌟 VIP CCs", callback_data="vip_menu")]
    ]
    # Delete old msg if from button
    if hasattr(update, "callback_query"):
        await update.callback_query.message.delete()
        await update.callback_query.message.chat.send_message("Dashboard:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("Dashboard:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # Join channel confirmation
    if data=="joined_channel":
        joined_users.add(user_id)
        await query.message.delete()
        await query.message.chat.send_message("✅ Verified! You can now access the Dashboard.")
        await send_dashboard(query, context)
        return

    # Free CCs
    if data=="free_cc":
        keyboard = [
            [InlineKeyboardButton("💳 Visa", url="https://dark-2009.github.io/CC-Bot/Visa.txt")],
            [InlineKeyboardButton("💳 Mastercard", url="https://dark-2009.github.io/CC-Bot/Mastercard.txt")],
            [InlineKeyboardButton("💳 Amex", url="https://dark-2009.github.io/CC-Bot/Amex.txt")],
            [InlineKeyboardButton("🏠 Back to Home", callback_data="back_home")]
        ]
        await query.message.delete()
        await query.message.chat.send_message("Select Free CC:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # VIP CCs
    if data=="vip_menu":
        vip_text = (
"🌟 VIP CCs 🌟\n\n"
"💎 Very Premium:\n"
"- Amex Platinum: $22\n"
"- Visa Gold: $20\n"
"- Amex Gold: $20\n"
"- Mastercard Platinum: $18\n\n"
"✨ Good Category:\n"
"- 💳 Mastercard $10\n"
"- 💳 Visa $10\n"
"- 💳 Amex $10"
        )
        keyboard = [
            [InlineKeyboardButton("Amex Platinum $22", callback_data="vip_amex_plat")],
            [InlineKeyboardButton("Visa Gold $20", callback_data="vip_visa_gold")],
            [InlineKeyboardButton("Amex Gold $20", callback_data="vip_amex_gold")],
            [InlineKeyboardButton("Mastercard Platinum $18", callback_data="vip_mc_plat")],
            [InlineKeyboardButton("Mastercard $10", callback_data="vip_mc_good")],
            [InlineKeyboardButton("Visa $10", callback_data="vip_visa_good")],
            [InlineKeyboardButton("Amex $10", callback_data="vip_amex_good")],
            [InlineKeyboardButton("🏠 Back to Home", callback_data="back_home")]
        ]
        await query.message.delete()
        await query.message.chat.send_message(vip_text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # VIP item → choose payment method
    if data.startswith("vip_"):
        price = [s for s in data.split("_") if s.isdigit()]
        amount = price[0] if price else "Unknown"
        user_states[user_id] = {"awaiting":"vip_payment", "vip_item": data, "amount": amount}
        keyboard = [
            [InlineKeyboardButton("💵 UPI (India)", callback_data=f"pay_upi_{data}")],
            [InlineKeyboardButton("🌍 Crypto (International)", callback_data=f"pay_crypto_{data}")],
            [InlineKeyboardButton("🏠 Back to Home", callback_data="back_home")]
        ]
        await query.message.delete()
        await query.message.chat.send_message("Choose payment method:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # UPI method
    if data.startswith("pay_upi_"):
        item = data.replace("pay_upi_","")
        user_states[user_id]["method"]="upi"
        keyboard = [[InlineKeyboardButton("✅ Paid", callback_data=f"utr_{item}")]]
        await query.message.delete()
        await query.message.chat.send_message(
            f"You selected {item.replace('vip_','').replace('_',' ').title()}\nPay via UPI: {UPI_ID}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Crypto method
    if data.startswith("pay_crypto_"):
        item = data.replace("pay_crypto_","")
        user_states[user_id]["method"]="crypto"
        amt = user_states[user_id].get("amount","Unknown")
        keyboard = [[InlineKeyboardButton("✅ Paid", callback_data=f"txhash_{item}")]]
        await query.message.delete()
        await query.message.chat.send_message(
            f"Send the **${amt}** to any of the USDT addresses:\n\n"
            f"ERC-20: 0x7AF25Fa408a2f4152b2450535Ea7Ce13520b7A37\n"
            f"TRC-20: TGUSsmMDg2Dgn9zgSKeyPoQEmj9vMes6GV\n"
            f"BEP-20: 0x7AF25Fa408a2f4152b2450535Ea7Ce13520b7A37\n"
            f"SPL: UQFS1UuLrpVQBfo78a8nFQCzwEK7X6QipNXw1SVciQk",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Paid UPI → ask UTR
    if data.startswith("utr_"):
        user_states[user_id]["awaiting"]="utr"
        await query.message.delete()
        await query.message.chat.send_message("Please enter your UTR below 👇")
        return

    # Paid Crypto → ask Tx Hash
    if data.startswith("txhash_"):
        user_states[user_id]["awaiting"]="txhash"
        await query.message.delete()
        await query.message.chat.send_message("Please enter your Transaction Hash 👇")
        return

    # Check status
    if data.startswith("check_utr_"):
        utr = data.replace("check_utr_","")
        txns = load_transactions()
        status = txns.get(utr,{}).get("status","Not found")
        keyboard = [[InlineKeyboardButton("🆘 Contact Support", url=SUPPORT_LINK)]]
        await query.message.delete()
        await query.message.chat.send_message(f"Status for `{utr}`: **{status}**", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Back
    if data=="back_home":
        await send_dashboard(query, context)
        return

# ---------------- HANDLE TEXT ----------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    state = user_states.get(user_id, {})

    # UTR
    if state.get("awaiting")=="utr":
        utr = update.message.text.strip()
        txns = load_transactions()
        txns[utr] = {"user_id": user_id, "status": "pending", "method":"upi"}
        save_transactions(txns)
        keyboard = [
            [InlineKeyboardButton("📩 Check Status", callback_data=f"check_utr_{utr}")],
            [InlineKeyboardButton("🆘 Contact Support", url=SUPPORT_LINK)]
        ]
        await update.message.reply_text(
            f"✅ Your UTR `{utr}` has been submitted.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        user_states.pop(user_id,None)
        return

    # Crypto TxHash
    if state.get("awaiting")=="txhash":
        txid = update.message.text.strip()
        txns = load_transactions()
        txns[txid] = {"user_id": user_id, "status": "pending", "method":"crypto"}
        save_transactions(txns)
        keyboard = [
            [InlineKeyboardButton("📩 Check Status", callback_data=f"check_utr_{txid}")],
            [InlineKeyboardButton("🆘 Contact Support", url=SUPPORT_LINK)]
        ]
        await update.message.reply_text(
            f"✅ Your Tx Hash `{txid}` has been submitted.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        user_states.pop(user_id,None)
        return

# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("Dashboard", send_dashboard))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__=="__main__":
    main()
