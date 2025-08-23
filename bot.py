import logging, random, json, asyncio, io
import requests
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)

# ---------------- CONFIG ----------------
BOT_TOKEN = "8241360344:AAFP0_43PmJRCTa2mpv5F2q_XYixkRXTdYs"

# Gist IDs
GIST_ID_CCS = "065082e31d1aed3b8d728dbd728fbc62"   # Free CCs gist (ccs.json)
GIST_ID_TXN = "426a9400569f40b6f4d664b74801a78a"   # Transactions gist

# Split PAT into 3 parts for safety
GITHUB_PAT = "github_pat_" + "11BQYPIPI0" + "boMKyo1ZCgKa_LMmfMm9vacbpv1upw9PQ1mT7l2DQ3r24JDeTOOz1o5ePTEH7RT4RE861P9f"
HEADERS = {"Authorization": f"token {GITHUB_PAT}"}

# URLs
GIST_URL_CCS = f"https://api.github.com/gists/{GIST_ID_CCS}"
GIST_URL_TXN = f"https://api.github.com/gists/{GIST_ID_TXN}"

UPI_ID = "withonly.vinay@axl"

logging.basicConfig(level=logging.INFO)

# ============ Helpers ============
def load_transactions():
    r = requests.get(GIST_URL_TXN, headers=HEADERS).json()
    files = r.get("files", {})
    return json.loads(files.get("transactions.json", {}).get("content", "{}"))

def save_transactions(data):
    payload = {"files": {"transactions.json": {"content": json.dumps(data, indent=2)}}}
    requests.patch(GIST_URL_TXN, headers=HEADERS, json=payload)

def fetch_ccs():
    r = requests.get(GIST_URL_CCS, headers=HEADERS).json()
    files = r.get("files", {})
    content = files.get("ccs.json", {}).get("content", "")
    return content.splitlines()

def filter_cards(cards, brand):
    results = []
    current = []
    for line in cards:
        if line.startswith("Card:"):
            if current: 
                block = "\n".join(current)
                num = current[0].split()[1].split("|")[0]
                if brand=="visa" and num.startswith("4"): results.append(block)
                elif brand=="master" and num.startswith("5"): results.append(block)
                elif brand=="amex" and num.startswith(("34","37")): results.append(block)
                current = []
        if line.strip(): current.append(line)
    return results

# ============ CC Generator ============
class CCGenerator:
    def luhn_checksum(self, card_number):
        def digits_of(n): return [int(d) for d in str(n)]
        digits = digits_of(card_number)
        odd, even = digits[-1::-2], digits[-2::-2]
        checksum = sum(odd)
        for d in even: checksum += sum(digits_of(d*2))
        return checksum % 10

    def calculate_luhn(self, partial):
        c = self.luhn_checksum(int(partial)*10)
        return c if c==0 else 10-c

    def generate_card(self, bin_number):
        length = 16 if not bin_number.startswith("3") else 15
        need = length - len(bin_number) - 1
        acc = ''.join([str(random.randint(0,9)) for _ in range(need)])
        partial = bin_number + acc
        check = self.calculate_luhn(partial)
        card = partial + str(check)
        exp = f"{random.randint(1,12):02d}|{str(random.randint(25,30))}"
        cvv = str(random.randint(100,999))
        return f"{card}|{exp}|{cvv}"

generator = CCGenerator()
user_states = {}

# ============ Handlers ============
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

    data = query.data
    cards = fetch_ccs()

    # ----- Free CCs -----
    if data.startswith("free_"):
        brand = data.replace("free_","")
        filtered = filter_cards(cards, brand)
        if not filtered:
            await query.edit_message_text("❌ No cards found. (Check gist ccs.json)")
            return
        text = "\n\n".join(filtered[:5])
        await query.edit_message_text(f"Here are some {brand.upper()} cards:\n\n{text}")

    # ----- VIP CCs -----
    elif data=="vip_menu":
        vip_text = """
🌟 VIP CCs 🌟  

💎 Very Premium (Balance up to 250 - 400$ ):  
- Amex Platinum: $22  
- Visa Gold: $20  
- Amex Gold: $20  
- Mastercard Platinum: $18  

✨ Good Category (Balance up to 100 - 150$):  
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
        await query.edit_message_text(
            f"You selected {data.replace('vip_','').title()}\nPay via UPI: {UPI_ID}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Paid", callback_data=f"utr_{data}")],
                [InlineKeyboardButton("⬅️ Back", callback_data="vip_menu")]
            ])
        )

    elif data.startswith("utr_"):
        user_states[query.from_user.id] = {"awaiting":"utr"}
        await query.edit_message_text("Please enter your UTR below 👇")

    elif data=="back_main":
        await start(query, context)

    # ----- CC-GEN -----
    elif data=="ccgen":
        user_states[query.from_user.id] = {"awaiting":"bin"}
        await query.edit_message_text("Enter BIN (6-9 digits):")

    elif data.startswith("format_"):
        fmt = data.split("_")[1]
        state = user_states.get(query.from_user.id,{})
        bin_list = state.get("bin_list", [])
        qty = state.get("qty",1)
        results = [generator.generate_card(b) for b in bin_list for _ in range(qty)]
        output = "\n".join(results)
        if len(output)>4000:
            bio = io.BytesIO(output.encode()); bio.name=f"ccgen.{fmt}"
            await query.message.reply_document(bio)
        else:
            await query.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    state = user_states.get(uid,{})

    if state.get("awaiting")=="utr":
        utr = update.message.text.strip()
        txns = load_transactions()
        txns[utr]={"user_id":uid,"status":"pending"}
        save_transactions(txns)
        kb = [
            [InlineKeyboardButton("🔄 Check Status", callback_data=f"check_{utr}")],
            [InlineKeyboardButton("📞 Support", url="https://t.me/alone120122")]
        ]
        await update.message.reply_text(
            f"✅ Your UTR `{utr}` has been submitted.",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)
        )
        user_states.pop(uid,None)

    elif state.get("awaiting")=="bin":
        bin_number = update.message.text.strip()
        if not (bin_number.isdigit() and 6<=len(bin_number)<=9):
            await update.message.reply_text("Invalid BIN. Try again:")
            return
        state["bin_list"]=[bin_number]; state["awaiting"]="qty"
        user_states[uid]=state
        await update.message.reply_text("BIN accepted. Enter quantity (1-20):")

    elif state.get("awaiting")=="qty":
        qty = update.message.text.strip()
        if not qty.isdigit() or not (1<=int(qty)<=20):
            await update.message.reply_text("Invalid qty. Try again:")
            return
        state["qty"]=int(qty); state["awaiting"]="format"
        user_states[uid]=state
        kb=[
            [InlineKeyboardButton("Plain",callback_data="format_plain")],
            [InlineKeyboardButton("JSON",callback_data="format_json")]
        ]
        await update.message.reply_text("Choose output format:",reply_markup=InlineKeyboardMarkup(kb))

    else:
        await update.message.reply_text("Use buttons to interact.")

async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer()
    utr=query.data.split("_")[1]
    txns=load_transactions()
    if utr not in txns:
        await query.edit_message_text("❌ UTR not found."); return
    status=txns[utr]["status"]
    if status=="pending":
        kb=[
            [InlineKeyboardButton("🔄 Check Again",callback_data=f"check_{utr}")],
            [InlineKeyboardButton("📞 Support",url="https://t.me/alone120122")]
        ]
        await query.edit_message_text("⌛ Pending. Please wait.",reply_markup=InlineKeyboardMarkup(kb))
    elif status=="approved":
        await query.edit_message_text("✅ Approved! You will receive your CC within 24 hours.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📞 Support",url="https://t.me/alone120122")]]))
    else:
        await query.edit_message_text("❌ Declined! Wrong UTR.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📞 Support",url="https://t.me/alone120122")]]))

# ============ MAIN ============
def main():
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(handle_buttons,pattern="^(free_|vip_|utr_|back_main|ccgen|format_).*$"))
    app.add_handler(CallbackQueryHandler(check_status,pattern="^check_.*$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__=="__main__":
    main()
