import logging
import asyncio
import re
import os
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command

# === CONFIG ===
BOT_TOKEN = "8241360344:AAFP0_43PmJRCTa2mpv5F2q_XYixkRXTdYs"
ADMIN_ID = 6800292901  # your chat id
CCS_URL = "https://dark-2009.github.io/CC-Bot/ccs.txt"
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
    """Identify brand by card number prefix."""
    if card_number.startswith("4"):
        return "visa"
    elif card_number.startswith("5"):
        return "mastercard"
    elif card_number.startswith("34") or card_number.startswith("37"):
        return "amex"
    return "unknown"

async def fetch_cards():
    """Fetch cards from the URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(CCS_URL) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logging.error(f"Failed to fetch cards: HTTP {response.status}")
                    return None
    except Exception as e:
        logging.error(f"Error fetching cards: {e}")
        return None

def parse_cards(card_data: str, brand: str) -> list[str]:
    """Parse card data and filter by brand."""
    if not card_data:
        return ["⚠️ Error: No card data available"]
    
    try:
        lines = card_data.strip().split('\n')
        results = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Extract card number (first part before any separator)
            card_match = re.search(r'(\d{15,16})', line)
            if card_match:
                card_number = card_match.group(1)
                detected = detect_brand(card_number)
                if detected == brand:
                    results.append(line)
        
        return results if results else [f"❌ No {brand.title()} cards found"]
    except Exception as e:
        return [f"⚠️ Error parsing cards: {e}"]

def get_page(data: list[str], page: int, page_size: int = 5):
    """Return paginated slice and total pages."""
    total_pages = (len(data) + page_size - 1) // page_size
    start = page * page_size
    end = start + page_size
    return data[start:end], total_pages

def log_transaction(user_id, product, utr):
    """Save UTR to log file with PENDING status."""
    entry = (
        f"User {user_id} | Product: {product} | UTR: {utr}\n"
        f"Status: PENDING\n"
        f"{'-'*40}\n"
    )
    with open(UTR_LOG, "a", encoding="utf-8") as f:
        f.write(entry)

def update_transaction_status(user_id, utr, status):
    """Update transaction status in log file."""
    if not os.path.exists(UTR_LOG):
        return False
    
    with open(UTR_LOG, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Find and update the specific transaction
    pattern = f"User {user_id}.*?UTR: {utr}.*?Status: PENDING"
    replacement = f"User {user_id} | UTR: {utr}\nStatus: {status}"
    
    updated_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    with open(UTR_LOG, "w", encoding="utf-8") as f:
        f.write(updated_content)
    
    return True

def check_transaction_status(user_id, utr):
    """Check if UTR is approved in log file."""
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
    data = query.data

    # Handle categories with pagination
    if data.startswith("cat_") and not data.endswith("vip"):
        _, brand, page_str = data.split("_")
        page = int(page_str)

        # Fetch cards from URL
        card_data = await fetch_cards()
        if not card_data:
            await query.answer("❌ Failed to fetch cards. Please try again later.", show_alert=True)
            return

        results = parse_cards(card_data, brand)
        if not results or "❌ No" in results[0] or "⚠️ Error" in results[0]:
            await query.answer(results[0] if results else "No cards found", show_alert=True)
            return

        cards, total_pages = get_page(results, page, 5)
        text = f"📊 Found {len(results)} {brand.title()} cards\nPage {page+1}/{total_pages}\n\n" + "\n\n".join(cards[:10])  # Limit to 10 cards per page

        buttons = []
        if page > 0:
            buttons.append(InlineKeyboardButton("⏮ Prev", callback_data=f"cat_{brand}_{page-1}"))
        if page < total_pages - 1:
            buttons.append(InlineKeyboardButton("Next ⏭", callback_data=f"cat_{brand}_{page+1}"))

        nav_buttons = []
        if buttons:
            nav_buttons.append(buttons)
        nav_buttons.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="back_to_menu")])

        kb = InlineKeyboardMarkup(inline_keyboard=nav_buttons)
        
        try:
            await query.message.edit_text(text, reply_markup=kb)
        except Exception as e:
            # If message is too long, split it
            if "message is too long" in str(e):
                half = len(text) // 2
                await query.message.edit_text(text[:half], reply_markup=kb)
                await query.message.answer(text[half:])
            else:
                await query.answer("Error displaying cards", show_alert=True)

    # Handle VIP menu
    elif data == "cat_vip":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Amex Platinum - $22", callback_data="vip_amex_platinum")],
            [InlineKeyboardButton(text="💎 Visa Gold - $20", callback_data="vip_visa_gold")],
            [InlineKeyboardButton(text="💎 Amex Gold - $20", callback_data="vip_amex_gold")],
            [InlineKeyboardButton(text="💎 Mastercard Platinum - $18", callback_data="vip_mc_platinum")],
            [InlineKeyboardButton(text="✨ Mastercard (10$)", callback_data="vip_mc_basic")],
            [InlineKeyboardButton(text="✨ Visa (10$)", callback_data="vip_visa_basic")],
            [InlineKeyboardButton(text="✨ Amex (10$)", callback_data="vip_amex_basic")],
            [InlineKeyboardButton(text="🔙 Back to Categories", callback_data="back_to_menu")]
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
            "- Amex: $10\n\n"
            f"💰 *Pay to UPI ID:* `{UPI_ID}`"
        )
        try:
            await query.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
        except:
            await query.message.answer(text, reply_markup=kb, parse_mode="Markdown")

    # VIP product selection
    elif data.startswith("vip_"):
        product = data.replace("vip_", "").replace("_", " ").title()
        waiting_for_utr[user_id] = product
        await query.message.answer(f"✅ You selected: {product}\n\n"
                                   f"💰 Please pay to UPI ID: `{UPI_ID}`\n"
                                   "Then send your UTR number here:")

    # Back to categories
    elif data == "back_to_menu":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Mastercard", callback_data="cat_mastercard_0")],
            [InlineKeyboardButton(text="💳 Visa", callback_data="cat_visa_0")],
            [InlineKeyboardButton(text="💳 American Express", callback_data="cat_amex_0")],
            [InlineKeyboardButton(text="🌟 VIP CCs", callback_data="cat_vip")]
        ])
        try:
            await query.message.edit_text("📂 Choose a category:", reply_markup=kb)
        except:
            await query.message.answer("📂 Choose a category:", reply_markup=kb)

    # Validate Transaction
    elif data.startswith("validate_"):
        utr = data.replace("validate_", "")
        status = check_transaction_status(user_id, utr)

        if status == "APPROVED":
            await query.message.answer("✅ Your transaction is approved. You will get your CC within 24 hours.")
        elif status == "PENDING":
            await query.message.answer("⏳ Transaction still pending verification. Please wait.")
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton("📞 Contact Support", url=SUPPORT_LINK)]
            ])
            await query.message.answer("❌ Payment declined or not found. Please contact support.", reply_markup=kb)
    
    # Admin approval handling
    elif data.startswith("admin_approve_"):
        # Extract user_id and UTR from callback data
        parts = data.split("_")
        target_user_id = int(parts[2])
        utr = parts[3]
        
        # Update transaction status
        update_transaction_status(target_user_id, utr, "APPROVED")
        
        # Notify user
        try:
            await bot.send_message(
                target_user_id,
                f"✅ Your transaction with UTR {utr} has been approved!\n\n"
                "Your CC will be delivered within 24 hours. Thank you for your purchase!"
            )
        except Exception as e:
            logging.error(f"Failed to notify user {target_user_id}: {e}")
        
        # Confirm to admin
        await query.message.edit_text(
            f"✅ Transaction approved for user {target_user_id} (UTR: {utr}).\n"
            "User has been notified."
        )
    
    # Admin decline handling
    elif data.startswith("admin_decline_"):
        # Extract user_id and UTR from callback data
        parts = data.split("_")
        target_user_id = int(parts[2])
        utr = parts[3]
        
        # Update transaction status
        update_transaction_status(target_user_id, utr, "DECLINED")
        
        # Notify user
        try:
            await bot.send_message(
                target_user_id,
                f"❌ Your transaction with UTR {utr} has been declined.\n\n"
                "Please contact support if you believe this is an error."
            )
        except Exception as e:
            logging.error(f"Failed to notify user {target_user_id}: {e}")
        
        # Confirm to admin
        await query.message.edit_text(
            f"❌ Transaction declined for user {target_user_id} (UTR: {utr}).\n"
            "User has been notified."
        )
    
    await query.answer()

# === MESSAGE HANDLER (UTR) ===
@dp.message()
async def handle_message(msg: types.Message):
    user_id = msg.from_user.id
    text = msg.text.strip()
    
    if user_id in waiting_for_utr:
        utr = text
        if re.match(r"^[0-9A-Za-z]{6,}$", utr):
            product = waiting_for_utr.pop(user_id)
            user_latest_utr[user_id] = utr
            log_transaction(user_id, product, utr)

            # Notify admin with approve/decline buttons
            admin_kb = InlineKeyboardMarkup(inline_keyboard=[
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
                reply_markup=admin_kb
            )

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton("✅ Validate Transaction", callback_data=f"validate_{utr}")]
            ])

            await msg.answer(f"🕒 UTR received for {product}.\n"
                             "Please wait for verification.\n\n"
                             "Once you think it's verified, click below:", reply_markup=kb)
        else:
            await msg.answer("❌ Invalid UTR format. Please try again.")
    else:
        # If not waiting for UTR, just show the main menu
        await listcc_cmd(msg)

# === MAIN ===
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
