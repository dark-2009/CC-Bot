import logging
import asyncio
import re
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command

# === CONFIG ===
BOT_TOKEN = "8241360344:AAFP0_43PmJRCTa2mpv5F2q_XYixkRXTdYs"
ADMIN_ID = 6800292901  # your chat id
CCS_FILE = "ccs.txt"   # make sure this file exists
UPI_ID = "withonly.vinay@axl"
UTR_LOG = "utr_log.txt"
SUPPORT_LINK = "https://t.me/Alone120122"  # replace with your support TG link

# === LOGGING ===
logging.basicConfig(level=logging.INFO)

# === INIT ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Store UTRs waiting for validation
waiting_for_utr = {}
user_latest_utr = {}

# === HELPERS ===
def detect_brand(card_number: str) -> str:
    if card_number.startswith("4"):
        return "visa"
    elif card_number.startswith("5"):
        return "mastercard"
    elif card_number.startswith("34") or card_number.startswith("37"):
        return "amex"
    return "unknown"


def parse_cards(brand: str) -> list[str]:
    try:
        with open(CCS_FILE, "r", encoding="utf-8") as f:
            blocks = f.read().split("-" * 40)

        results = []
        for block in blocks:
            block = block.strip()
            if not block:
                continue

            card_match = re.search(r"(\d{15,16}\|\d{2}\|\d{2}\|\d+)", block)
            card = card_match.group(1) if card_match else "Unknown"

            detected = detect_brand(card.split("|")[0]) if card != "Unknown" else "unknown"
            if detected == brand:
                results.append(block.strip())

        return results
    except Exception as e:
        return [f"⚠️ Error reading file: {e}"]


def get_page(data: list[str], page: int, page_size: int = 5):
    total_pages = (len(data) + page_size - 1) // page_size
    start = page * page_size
    end = start + page_size
    return data[start:end], total_pages


def log_transaction(user_id, product, utr, status="PENDING"):
    entry = (
        f"User {user_id} | Product: {product} | UTR: {utr}\n"
        f"Status: {status}\n"
        f"{'-'*40}\n"
    )
    with open(UTR_LOG, "a", encoding="utf-8") as f:
        f.write(entry)


def update_transaction_status(user_id, utr, new_status):
    if not os.path.exists(UTR_LOG):
        return False

    with open(UTR_LOG, "r", encoding="utf-8") as f:
        blocks = f.read().split("-" * 40)

    new_content = ""
    found = False
    for block in blocks:
        if not block.strip():
            continue
        if f"User {user_id}" in block and utr in block:
            found = True
            lines = block.strip().splitlines()
            for i, line in enumerate(lines):
                if line.startswith("Status:"):
                    lines[i] = f"Status: {new_status}"
            block = "\n".join(lines)
        new_content += block.strip() + "\n" + ("-" * 40) + "\n"

    if found:
        with open(UTR_LOG, "w", encoding="utf-8") as f:
            f.write(new_content)
    return found


def check_transaction_status(user_id, utr):
    if not os.path.exists(UTR_LOG):
        return "NOT_FOUND"

    with open(UTR_LOG, "r", encoding="utf-8") as f:
        content = f.read().split("-" * 40)

    for block in content:
        if f"User {user_id}" in block and utr in block:
            if "APPROVED" in block:
                return "APPROVED"
            elif "PENDING" in block:
                return "PENDING"
            elif "DECLINED" in block:
                return "DECLINED"
    return "NOT_FOUND"


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

    # Approve / Decline handling
    if query.data.startswith("admin_"):
        action, uid, utr = query.data.split("_")[1:]
        uid = int(uid)

        if action == "approve":
            updated = update_transaction_status(uid, utr, "APPROVED")
            if updated:
                await bot.send_message(uid, f"✅ Your transaction (UTR: {utr}) has been *APPROVED*.\nDelivery within 24 hours.", parse_mode="Markdown")
                await query.message.edit_text(f"✅ Approved UTR {utr} for User {uid}")
        elif action == "decline":
            updated = update_transaction_status(uid, utr, "DECLINED")
            if updated:
                await bot.send_message(uid, f"❌ Your transaction (UTR: {utr}) has been *DECLINED*.\nPlease contact support.", parse_mode="Markdown")
                await query.message.edit_text(f"❌ Declined UTR {utr} for User {uid}")
        return

    # (rest of your category / VIP code unchanged…)
    # Keep your existing category + product handlers here


# === MESSAGE HANDLER (UTR) ===
@dp.message()
async def handle_message(msg: types.Message):
    user_id = msg.from_user.id
    if user_id in waiting_for_utr:
        utr = msg.text.strip()
        if re.match(r"^[0-9A-Za-z]{6,}$", utr):
            product = waiting_for_utr.pop(user_id)
            user_latest_utr[user_id] = utr
            log_transaction(user_id, product, utr, "PENDING")

            # Notify admin with Approve/Decline buttons
            kb_admin = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_{user_id}_{utr}"),
                    InlineKeyboardButton("❌ Decline", callback_data=f"admin_decline_{user_id}_{utr}")
                ]
            ])

            await bot.send_message(
                ADMIN_ID,
                f"📢 New UTR Submitted\n"
                f"User: {user_id}\n"
                f"Product: {product}\n"
                f"UTR: {utr}\n"
                f"Status: PENDING",
                reply_markup=kb_admin
            )

            await msg.answer(f"🕒 UTR received for {product}.\n"
                             "Please wait for admin verification.")
        else:
            await msg.answer("❌ Invalid UTR format. Please try again.")


# === MAIN ===
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
