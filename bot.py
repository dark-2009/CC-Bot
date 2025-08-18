import logging
import asyncio
import re
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from aiogram.filters import Command

# === CONFIG ===
BOT_TOKEN = "8241360344:AAFP0_43PmJRCTa2mpv5F2q_XYixkRXTdYs"   # ⚠️ Replace with your token
CCS_FILE = "ccs.txt"
QR_IMAGE = "qr_placeholder.png"       # put your QR code image file here

# === LOGGING ===
logging.basicConfig(level=logging.INFO)

# === INIT ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Store pagination states and VIP UTR states
pagination_state = {}
waiting_for_utr = {}

# === HELPERS ===
def parse_cards(brand: str) -> list[str]:
    """Parse ccs.txt, filter by brand, normalize output, return list of cards."""
    try:
        with open(CCS_FILE, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

        results = []
        buffer = []
        for line in lines:
            if not line.strip():
                continue
            buffer.append(line.strip())
            # if multiline entry ends, flush
            if "Time:" in line or "Time:" in line.upper():
                block = " ".join(buffer)
                buffer = []

                # Extract card number
                card_match = re.search(r"(\d{15,16}\|\d{2}\|\d{2}\|\d+)", block)
                card = card_match.group(1) if card_match else "Unknown"

                # Extract BIN
                bin_match = re.search(r"BIN[:\- ]+(\d+)", block, re.IGNORECASE)
                bin_code = bin_match.group(1) if bin_match else card[:6]

                # Extract Bank
                bank_match = re.search(r"Bank[:\- ]+([^|]+)", block, re.IGNORECASE)
                bank = bank_match.group(1).strip() if bank_match else "N/A"

                # Extract Brand
                brand_match = re.search(r"Brand[:\- ]+([^|]+)", block, re.IGNORECASE)
                brand_name = brand_match.group(1).strip() if brand_match else "Unknown"

                # Extract Country
                country_match = re.search(r"Country[:\- ]+([^|]+)", block, re.IGNORECASE)
                country = country_match.group(1).strip() if country_match else "N/A"

                # Extract Status
                status = "Approved ✅" if "Approved" in block else "Unknown"

                # Extract Time
                time_match = re.search(r"Time[: ]+([0-9.]+s)", block, re.IGNORECASE)
                time_taken = time_match.group(1) if time_match else "N/A"

                formatted = (
                    f"💳 Card: {card}\n"
                    f"BIN: {bin_code} | Bank: {bank}\n"
                    f"Brand: {brand_name} | Country: {country}\n"
                    f"Status: {status} | Time: {time_taken}"
                )
                if brand.lower() in formatted.lower():
                    results.append(formatted)

        return results
    except Exception as e:
        return [f"⚠️ Error parsing file: {e}"]

def get_page(data: list[str], page: int, page_size: int = 5):
    """Return paginated slice and total pages."""
    total_pages = (len(data) + page_size - 1) // page_size
    start = page * page_size
    end = start + page_size
    return data[start:end], total_pages

# === COMMAND HANDLERS ===
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("👋 Welcome! Use /listcc to view available categories.")

@dp.message(Command("listcc"))
async def listcc_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Mastercard", callback_data="cat_mastercard_0")],
        [InlineKeyboardButton(text="💳 Visa", callback_data="cat_visa_0")],
        [InlineKeyboardButton(text="💳 American Express", callback_data="cat_amex_0")],
        [InlineKeyboardButton(text="🌟 VIP CCs", callback_data="cat_vip")]
    ])
    await message.answer("📂 Choose a category:", reply_markup=kb)

# === CALLBACK HANDLERS ===
@dp.callback_query()
async def handle_callback(query: types.CallbackQuery):
    user_id = query.from_user.id

    # Handle categories with pagination
    if query.data.startswith("cat_") and not query.data.endswith("vip"):
        _, brand, page_str = query.data.split("_")
        page = int(page_str)

        results = parse_cards(brand)
        if not results:
            await query.message.answer(f"❌ No {brand.title()} cards found.")
            return

        pagination_state[user_id] = {"brand": brand, "page": page, "results": results}

        cards, total_pages = get_page(results, page, 5)
        text = f"📊 Found {len(results)} {brand.title()} cards\n\n" + "\n\n".join(cards)

        buttons = []
        if page > 0:
            buttons.append(InlineKeyboardButton("⏮ Prev", callback_data=f"cat_{brand}_{page-1}"))
        if page < total_pages - 1:
            buttons.append(InlineKeyboardButton("Next ⏭", callback_data=f"cat_{brand}_{page+1}"))

        kb = InlineKeyboardMarkup(inline_keyboard=[buttons] if buttons else [])
        await query.message.edit_text(text, reply_markup=kb)

    # Handle VIP menu
    elif query.data == "cat_vip":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Amex Platinum - $22", callback_data="vip_amex_platinum")],
            [InlineKeyboardButton(text="💎 Visa Gold - $20", callback_data="vip_visa_gold")],
            [InlineKeyboardButton(text="💎 Amex Gold - $20", callback_data="vip_amex_gold")],
            [InlineKeyboardButton(text="💎 Mastercard Platinum - $18", callback_data="vip_mc_platinum")],
            [InlineKeyboardButton(text="✨ Mastercard (10$)", callback_data="vip_mc_basic")],
            [InlineKeyboardButton(text="✨ Visa (10$)", callback_data="vip_visa_basic")],
            [InlineKeyboardButton(text="✨ Amex (10$)", callback_data="vip_amex_basic")]
        ])
        text = (
            "🌟 *VIP Category*\n\n"
            "Very Premium (Balance up to 20-30k INR):\n"
            "- Amex Platinum: $22\n"
            "- Visa Gold: $20\n"
            "- Amex Gold: $20\n"
            "- Mastercard Platinum: $18\n\n"
            "Good Category (Balance up to 10k INR):\n"
            "- Mastercard: $10\n"
            "- Visa: $10\n"
            "- Amex: $10"
        )
        await query.message.answer_photo(InputFile(QR_IMAGE), caption=text, reply_markup=kb, parse_mode="Markdown")

    # VIP product selection
    elif query.data.startswith("vip_"):
        product = query.data.replace("vip_", "").replace("_", " ").title()
        waiting_for_utr[user_id] = product
        await query.message.answer(f"✅ You selected: {product}\n\nPlease send your UTR number here:")

# === MESSAGE HANDLER (UTR) ===
@dp.message()
async def handle_message(msg: types.Message):
    user_id = msg.from_user.id
    if user_id in waiting_for_utr:
        utr = msg.text.strip()
        if re.match(r"^[0-9A-Za-z]{6,}$", utr):  # basic validation
            product = waiting_for_utr.pop(user_id)
            await msg.answer(f"🕒 UTR received for {product}. Please wait up to 24 hours for verification.\n"
                             "Your CC will be delivered to this chat once verified ✅")
        else:
            await msg.answer("❌ Invalid UTR format. Please try again.")

# === MAIN ===
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
