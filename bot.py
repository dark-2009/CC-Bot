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
        [InlineKeyboardButton("💳 Visa", url="https://dark-2009.github.io/CC-Bot/Visa.txt")],
        [InlineKeyboardButton("💳 Mastercard", url="https://dark-2009.github.io/CC-Bot/Mastercard.txt")],
        [InlineKeyboardButton("💳 Amex", url="https://dark-2009.github.io/CC-Bot/Amex.txt")],
        [InlineKeyboardButton("⚡ CC-GEN", callback_data="ccgen")],
        [InlineKeyboardButton("🌟 VIP CCs", callback_data="vip_menu")]
    ]
    if hasattr(update, "callback_query"):
        newmsg = await update.callback_query.message.reply_text("Dashboard:", reply_markup=InlineKeyboardMarkup(keyboard))
        await update.callback_query.message.delete()
    else:
        await update.message.reply_text("Dashboard:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # Joining
    if data=="joined_channel":
        joined_users.add(user_id)
        await send_dashboard(query, context)
        return

    # VIP Menu
    if data=="vip_menu":
        vip_text = """
🌟 VIP CCs 🌟

💎 Very Premium:
- Amex Platinum: $22
- Visa Gold: $20
- Amex Gold: $20
- Mastercard Platinum: $18

✨ Good Category:
- Mastercard: $10
- Visa: $10
- Amex: $10
"""
        keyboard = [
            [InlineKeyboardButton("Amex Platinum $22", callback_data="vip_amex_plat")],
            [InlineKeyboardButton("Visa Gold $20", callback_data="vip_visa_gold")],
            [InlineKeyboardButton("Amex Gold $20", callback_data="vip_amex_gold")],
            [InlineKeyboardButton("Mastercard Platinum $18", callback_data="vip_mc_plat")],
            [InlineKeyboardButton("Mastercard $10", callback_data="vip_mc")],
            [InlineKeyboardButton("Visa $10", callback_data="vip_visa")],
            [InlineKeyboardButton("Amex $10", callback_data="vip_amex")],
            [InlineKeyboardButton("🏠 Back", callback_data="back_home")]
        ]
        newmsg = await query.message.reply_text(vip_text, reply_markup=InlineKeyboardMarkup(keyboard))
        await query.message.delete()
        return

    # VIP selection → Payment Method
    if data.startswith("vip_"):
        prices = {
            "vip_amex_plat":22, "vip_visa_gold":20, "vip_amex_gold":20, "vip_mc_plat":18,
            "vip_mc":10, "vip_visa":10, "vip_amex":10
        }
        price = prices.get(data, 0)
        user_states[user_id] = {"awaiting": "paymethod", "item": data, "price": price}
        keyboard = [
            [InlineKeyboardButton("💳 UPI (India)", callback_data="pay_upi")],
            [InlineKeyboardButton("🌍 Crypto (International)", callback_data="pay_crypto")],
            [InlineKeyboardButton("🏠 Back", callback_data="back_home")]
        ]
        newmsg = await query.message.reply_text("Choose Payment Method:", reply_markup=InlineKeyboardMarkup(keyboard))
        await query.message.delete()
        return

    # Payment - UPI
    if data=="pay_upi":
        st = user_states.get(user_id, {})
        price = st.get("price","?")
        keyboard = [
            [InlineKeyboardButton("✅ Paid", callback_data="utr_submit")],
            [InlineKeyboardButton("🏠 Back", callback_data="back_home")]
        ]
        newmsg = await query.message.reply_text(
            f"Send ₹{price*80} via UPI to:\n`{UPI_ID}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await query.message.delete()
        user_states[user_id]["awaiting"]="utr"
        return

    # Payment - Crypto
    if data=="pay_crypto":
        st = user_states.get(user_id, {})
        price = st.get("price","?")
        msg = (f"Send ${price} to any of the USDT addresses:\n\n"
               f"ERC-20: 0x7AF25Fa408a2f4152b2450535Ea7Ce13520b7A37\n\n"
               f"TRC-20: TGUSsmMDg2Dgn9zgSKeyPoQEmj9vMes6GV\n\n"
               f"BEP-20: 0x7AF25Fa408a2f4152b2450535Ea7Ce13520b7A37\n\n"
               f"SPL: UQFS1UuLrpVQBfo78a8nFQCzwEK7X6QipNXw1SVciQk")
        keyboard = [
            [InlineKeyboardButton("✅ Paid", callback_data="txhash_submit")],
            [InlineKeyboardButton("🏠 Back", callback_data="back_home")]
        ]
        newmsg = await query.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        await query.message.delete()
        user_states[user_id]["awaiting"]="txhash"
        return

    # UTR submit trigger
    if data=="utr_submit":
        user_states[user_id]["awaiting"]="utr_text"
        await query.message.reply_text("Please enter your UTR 👇")
        return

    # TxHash submit trigger
    if data=="txhash_submit":
        user_states[user_id]["awaiting"]="txhash_text"
        await query.message.reply_text("Please enter your Tx Hash 👇")
        return

    # Back Home
    if data=="back_home":
        await send_dashboard(query, context)
        return

    # CC-GEN
    if data=="ccgen":
        user_states[user_id]={"awaiting":"bin"}
        await query.message.reply_text("Enter BIN manually (6-9 digits) or send a .txt file with BINs")
        return

    # Quantity selection
    if data.startswith("qty_") and user_states.get(user_id,{}).get("awaiting")=="quantity":
        qty = int(data.split("_")[1])
        bins = user_states[user_id].get("bins",[])
        results=[]
        for b in bins:
            for _ in range(qty):
                results.append(generator.generate_card(b))
        output_text="\n".join(results)
        if len(results)>50:
            bio = io.BytesIO(output_text.encode()); bio.name="ccgen.txt"
            await query.message.reply_document(document=bio)
        else:
            await query.message.reply_text(output_text)
        user_states.pop(user_id,None)
        return

# ---------------- HANDLE TEXT ----------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    state = user_states.get(user_id, {})

    # UTR entry
    if state.get("awaiting")=="utr_text":
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

    # TxHash entry
    if state.get("awaiting")=="txhash_text":
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

    # Manual BIN
    if state.get("awaiting")=="bin":
        bin_number = update.message.text.strip()
        if not (bin_number.isdigit() and 6<=len(bin_number)<=9):
            await update.message.reply_text("❌ Invalid BIN. Try again:")
            return
        user_states[user_id]["bins"]=[bin_number]
        user_states[user_id]["awaiting"]="quantity"
        keyboard = [
            [InlineKeyboardButton("5", callback_data="qty_5"), InlineKeyboardButton("10", callback_data="qty_10")],
            [InlineKeyboardButton("20", callback_data="qty_20"), InlineKeyboardButton("50", callback_data="qty_50")],
            [InlineKeyboardButton("100", callback_data="qty_100")]
        ]
        await update.message.reply_text("Select how many CCs to generate:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # File BIN upload
    if update.message.document and state.get("awaiting")=="bin":
        file = await update.message.document.get_file()
        content = await file.download_as_bytearray()
        bins = [line.decode().strip() for line in content.splitlines() if line.strip().isdigit()]
        if not bins:
            await update.message.reply_text("❌ No valid BINs found in file.")
            return
        user_states[user_id]["bins"]=bins
        user_states[user_id]["awaiting"]="quantity"
        keyboard = [
            [InlineKeyboardButton("5", callback_data="qty_5"), InlineKeyboardButton("10", callback_data="qty_10")],
            [InlineKeyboardButton("20", callback_data="qty_20"), InlineKeyboardButton("50", callback_data="qty_50")],
            [InlineKeyboardButton("100", callback_data="qty_100")]
        ]
        await update.message.reply_text("Select how many CCs to generate:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

# ---------------- BACKGROUND TASK ----------------
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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_text))
    asyncio.create_task(notifier(app))
    app.run_polling()

if __name__=="__main__":
    main()
