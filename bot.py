import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from aiogram.filters import Command
import re

# === CONFIG ===
BOT_TOKEN = "8241360344:AAFP0_43PmJRCTa2mpv5F2q_XYixkRXTdYs"   # ⬅️ replace with your real token
CCS_FILE = "ccs.txt"
QR_IMAGE = "qr_placeholder.png"  # put your QR code image file later

# === LOGGING ===
logging.basicConfig(level=logging.INFO)

# === INIT ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === HELPERS ===
def load_cards_by_brand(brand: str) -> str:
    """Parse ccs.txt and return all lines containing the brand (Visa/Mastercard/Amex)."""
    try:
        with open(CCS_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        filtered = [line.strip() for line in lines if brand.lower() in line.lower()]
        if not filtered:
            return f"❌ No {brand} cards found."
        return "\n".join(filtered[:30])  # send first 30 to avoid flooding
    except Exception as e:
        return f"⚠️ Error reading file: {e}"

# === COMMAND HANDLERS ===
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("👋 Welcome! Use /listcc to view available categories.")

@dp.message(Command("listcc"))
async def listcc_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Mastercard", callback_data="cat_mastercard")],
        [InlineKeyboardButton(text="💳 Visa", callback_data="cat_visa")],
        [InlineKeyboardButton(text="💳 American Express", callback_data="cat_amex")],
        [InlineKeyboardButton(text="🌟 VIP CCs", callback_data="cat_vip")]
    ])
    await message.answer("📂 Choose a category:", reply_markup=kb)

# === CALLBACK HANDLERS ===
@dp.callback_query()
async def handle_callback(query: types.CallbackQuery):
    if query.data == "cat_mastercard":
        result = load_cards_by_brand("mastercard")
        await query.message.answer(f"💳 Mastercard BINs:\n\n{result}")
    elif query.data == "cat_visa":
        result = load_cards_by_brand("visa")
        await query.message.answer(f"💳 Visa BINs:\n\n{result}")
    elif query.data == "cat_amex":
        result = load_cards_by_brand("amex")
        await query.message.answer(f"💳 American Express BINs:\n\n{result}")
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
        await query.message.answer(f"✅ You selected: {product}\n\nPlease send your UTR number here:")

        # Register next step for UTR input
        @dp.message()
        async def utr_handler(msg: types.Message):
            utr = msg.text.strip()
            if re.match(r"^[0-9A-Za-z]{6,}$", utr):  # basic validation
                await msg.answer("🕒 UTR received. Please wait up to 24 hours for verification.\n"
                                 "Your CC will be delivered to this chat once verified ✅")
            else:
                await msg.answer("❌ Invalid UTR format. Please try again.")

# === MAIN ===
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
