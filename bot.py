import random, json, io, logging, requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ---------------- CONFIG ----------------
BOT_TOKEN = "8241360344:AAFP0_43PmJRCTa2mpv5F2q_XYixkRXTdYs"  # <-- replace with your token
GIST_ID_CCS = "065082e31d1aed3b8d728dbd728fbc62"
GIST_ID_TXN = "426a9400569f40b6f4d664b74801a78a"
GITHUB_PAT = "github_pat_11BQYPIPI0boMKyo1ZCgKa_LMmfMm9vac" + "bpv1upw9PQ1mT7l2DQ3r24JDeTOOz1o5ePTEH7RT4RE861P9f"
HEADERS = {"Authorization": f"token {GITHUB_PAT}"}

GIST_URL_CCS = f"https://api.github.com/gists/{GIST_ID_CCS}"
GIST_URL_TXN = f"https://api.github.com/gists/{GIST_ID_TXN}"
UPI_ID = "withonly.vinay@axl"
SUPPORT_LINK = "https://t.me/alone120122"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- HELPERS ----------------
def fetch_ccs():
    """Fetch CCs from ccs.json gist."""
    try:
        r = requests.get(GIST_URL_CCS, headers=HEADERS).json()
        files = r.get("files", {})
        content = files.get("ccs.json", {}).get("content", "[]")
        data = json.loads(content)
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"fetch_ccs error: {e}")
        return []

def filter_cards(cards, brand):
    results = []
    for card in cards:
        number = card.get("number","")
        if brand=="visa" and number.startswith("4"): results.append(card)
        elif brand=="master" and number.startswith("5"): results.append(card)
        elif brand=="amex" and number.startswith(("34","37")): results.append(card)
    return results

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

# ---------------- CC GENERATOR ----------------
class CCGenerator:
    def get_bin_info(self, bin_number):
        first_digit = bin_number[0]
        if first_digit=="3": return {"brand":"Amex","length":15}
        if first_digit=="4": return {"brand":"Visa","length":16}
        if first_digit=="5": return {"brand":"Mastercard","length":16}
        return {"brand":"Unknown","length":16}

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
        card = partial + str(check)
        exp = f"{random.randint(1,12):02d}|{str(random.randint(25,30))}"
        cvv = str(random.randint(100,999)) if info["brand"]!="Amex" else str(random.randint(1000,9999))
        return f"{card}|{exp}|{cvv} ({info['brand']})"

generator = CCGenerator()
user_states = {}

# ---------------- BOT HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💳 Visa", callback_data="free_visa")],
        [InlineKeyboardButton("💳 Mastercard", callback_data="free_master")],
        [InlineKeyboardButton("💳 Amex", callback_data="free_amex")],
        [InlineKeyboardButton("⚡ CC-GEN", callback_data="ccgen")],
        [InlineKeyboardButton("🌟 VIP CCs", callback_data="vip_menu")]
    ]
    await update.message.reply_text("Choose an option:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    cards = fetch_ccs()

    # Free CCs
    if data.startswith("free_"):
        brand = data.replace("free_","")
        filtered = filter_cards(cards, brand)
        if not filtered:
            await query.edit_message_text("❌ No cards found.")
            return
        text = "\n".join([f"{c['number']} | {c.get('exp','??')} | {c.get('cvv','??')}" for c in filtered[:5]])
        await query.edit_message_text(f"Here are some {brand.upper()} cards:\n{text}")

    # VIP CCs
    elif data=="vip_menu":
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
            [InlineKeyboardButton("Back", callback_data="back_main")]
        ]
        await query.edit_message_text(vip_text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("vip_"):
        await query.edit_message_text(f"You selected {data.replace('vip_','').title()}\nPay via UPI: {UPI_ID}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Paid", callback_data=f"utr_{data}")]]))

    elif data.startswith("utr_"):
        user_states[user_id] = {"awaiting":"utr"}
        await query.edit_message_text("Please enter your UTR below 👇")

    elif data=="back_main":
        await start(query, context)

    # CC Generator
    elif data=="ccgen":
        keyboard = [
            [InlineKeyboardButton("Upload BIN file", callback_data="upload_bin")],
            [InlineKeyboardButton("I don't have BIN", callback_data="manual_bin")],
        ]
        await query.edit_message_text("Choose BIN input method:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data=="upload_bin":
        user_states[user_id] = {"awaiting":"file"}
        await query.edit_message_text("Send me your BIN file (.txt)")

    elif data=="manual_bin":
        user_states[user_id] = {"awaiting":"bin"}
        await query.edit_message_text("Enter your BIN manually (6-9 digits)")

    elif data.startswith("choose_brand_"):
        brand = data.split("_")[-1]
        user_states[user_id]["brand"]=brand
        user_states[user_id]["awaiting"]="qty_buttons"
        # Quantity buttons
        keyboard = [
            [InlineKeyboardButton("5", callback_data="qty_5"),
             InlineKeyboardButton("10", callback_data="qty_10")],
            [InlineKeyboardButton("20", callback_data="qty_20"),
             InlineKeyboardButton("50", callback_data="qty_50")],
            [InlineKeyboardButton("100", callback_data="qty_100")]
        ]
        await query.edit_message_text("Select how many CCs to generate per BIN:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("qty_") and user_states.get(user_id,{}).get("awaiting")=="qty_buttons":
        qty = int(data.split("_")[1])
        bins = user_states[user_id].get("bins",[])
        brand = user_states[user_id].get("brand")
        results = []
        for b in bins:
            for _ in range(qty):
                card = generator.generate_card(b)
                # ensure card matches selected brand
                if brand=="visa" and card.startswith("4"): results.append(card)
                elif brand=="master" and card.startswith("5"): results.append(card)
                elif brand=="amex" and card.startswith(("34","37")): results.append(card)
        output_text = "\n".join(results)
        # If too long, send as file
        if len(results)>50:
            bio = io.BytesIO(output_text.encode()); bio.name="ccgen.txt"
            await query.message.reply_document(document=bio)
        else:
            await query.edit_message_text(output_text)
        user_states.pop(user_id,None)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    state = user_states.get(user_id,{})

    # UTR submission
    if state.get("awaiting")=="utr":
        utr = update.message.text.strip()
        txns = load_transactions()
        txns[utr]={"user_id":user_id,"status":"pending"}
        save_transactions(txns)
        await update.message.reply_text(f"✅ Your UTR `{utr}` has been submitted.", parse_mode="Markdown")
        user_states.pop(user_id,None)
        return

    # Manual BIN
    if state.get("awaiting")=="bin":
        bin_number = update.message.text.strip()
        if not (bin_number.isdigit() and 6<=len(bin_number)<=9):
            await update.message.reply_text("❌ Invalid BIN. Try again:")
            return
        user_states[user_id]["bins"]=[bin_number]
        keyboard = [
            [InlineKeyboardButton("Visa", callback_data="choose_brand_visa")],
            [InlineKeyboardButton("Mastercard", callback_data="choose_brand_master")],
            [InlineKeyboardButton("Amex", callback_data="choose_brand_amex")]
        ]
        await update.message.reply_text("Choose which brand to generate:", reply_markup=InlineKeyboardMarkup(keyboard))
        user_states[user_id]["awaiting"]="brand"
        return

    # File BIN upload
    if state.get("awaiting")=="file" and update.message.document:
        file = await update.message.document.get_file()
        content = await file.download_as_bytearray()
        bins = [line.decode().strip() for line in content.splitlines() if line.strip().isdigit()]
        if not bins:
            await update.message.reply_text("❌ No valid BINs found in file.")
            return
        user_states[user_id]["bins"]=bins
        keyboard = [
            [InlineKeyboardButton("Visa", callback_data="choose_brand_visa")],
            [InlineKeyboardButton("Mastercard", callback_data="choose_brand_master")],
            [InlineKeyboardButton("Amex", callback_data="choose_brand_amex")]
        ]
        await update.message.reply_text("Choose which brand to generate:", reply_markup=InlineKeyboardMarkup(keyboard))
        user_states[user_id]["awaiting"]="brand"
        return

# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_text))
    app.run_polling()

if __name__=="__main__":
    main()
