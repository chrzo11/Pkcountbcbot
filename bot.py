#main.py

import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram import idle
from pyrogram.errors import MessageNotModified

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import requests

from config import API_ID, API_HASH, BOT_TOKEN

app = Client("balance_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


user_data = {}


async def send_final_message(client: Client, temp_message: Message, text: str):
    """
    Sends the final result message and safely deletes the temporary status message.
    """
    await client.send_message(chat_id=temp_message.chat.id, text=text)
    try:
        await temp_message.delete()
    except MessageNotModified:
        pass


async def get_balance(client: Client, user_id: int, number_input: str, temp_message: Message):
    """
    Handles the entire process of logging in and checking the balance for a single account.
    The username is constructed from a hardcoded prefix and the user's number input.
    The password is hardcoded directly.
    """
    username = f"Gtmrhk{number_input}"
    password = "956683hH"
    
    display_name = f"Account #{number_input}"

    if not user_data.get(user_id, {}).get('active', True):
        await temp_message.edit_text(f"🛑 **Cancelled:** Processing for `{display_name}` was stopped by user.")
        return

    try:
        await temp_message.edit_text(f"⏳ **Processing:** `{display_name}`\nStarting browser...")

        options = webdriver.ChromeOptions()
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument(f"user-agent={user_agent}")

        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 15)
        join_now_url = "https://playkaro365.com/join-now"
        driver.get(join_now_url)

        await temp_message.edit_text(f"⏳ **Processing:** `{display_name}`\nPage loaded. Fetching token...")

        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//meta[@name='csrf-token']")))
            csrf_token = driver.find_element(By.XPATH, "//meta[@name='csrf-token']").get_attribute("content")
            browser_cookies = driver.get_cookies()
        except (TimeoutException, NoSuchElementException):
            error_text = f"❌ **Error for `{display_name}`:**\nCould not find CSRF token. The website might be down or changed."
            await send_final_message(client, temp_message, error_text)
            return
        finally:
            driver.quit()

        if not browser_cookies:
            error_text = f"❌ **Error for `{display_name}`:**\nCould not get browser cookies. Anti-bot measures may be active."
            await send_final_message(client, temp_message, error_text)
            return

    except Exception as e:
        error_text = f"❌ **Error for `{display_name}`:**\nFailed during browser setup. Details: {e}"
        await send_final_message(client, temp_message, error_text)
        return

    await temp_message.edit_text(f"⏳ **Processing:** `{display_name}`\nGot token. Attempting API login...")

    session = requests.Session()
    for cookie in browser_cookies:
        session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

    login_url = "https://playkaro365.com/api2/v2/login"
    login_payload = {'email': username, 'password': password, 'remember_me': 'true'}
    login_headers = {
        'User-Agent': user_agent, 'Accept': 'application/json, text/plain, */*', 'X-Csrf-Token': csrf_token,
        'X-Requested-With': 'XMLHttpRequest', 'Referer': join_now_url, 'Origin': 'https://playkaro365.com'
    }

    try:
        login_response = session.post(login_url, headers=login_headers, data=login_payload)
        login_response.raise_for_status()
        login_data = login_response.json()

        if login_data.get('status') != 'success' and 'Login Success' not in login_data.get('message', ''):
            reason = login_data.get('message', "Invalid credentials or login issue.")
            error_text = f"❌ **Login Failed for `{display_name}`:**\nReason: `{reason}`"
            await send_final_message(client, temp_message, error_text)
            return

    except requests.exceptions.RequestException as e:
        error_text = f"❌ **Error for `{display_name}`:**\nAPI login request failed. Details: {e}"
        await send_final_message(client, temp_message, error_text)
        return

    await temp_message.edit_text(f"✅ **Login Successful for `{display_name}`!**\nFetching balance...")

    try:
        balance_url = "https://playkaro365.com/api/getBalance"
        balance_response = session.post(balance_url, headers=login_headers)
        balance_response.raise_for_status()
        balance_data = balance_response.json()

        balance_info = balance_data.get('balance', {})
        main_balance = round(float(balance_info.get('main_balance', 0)))
        exposure = balance_info.get('exposure', 'N/A')

        result_text = (
            f"👤 **Account:** `{display_name}`\n"
            f"💰 **Main Balance:** `{main_balance}`\n"
            f"⚖️ **Exposure:** `{exposure}`"
        )
        await send_final_message(client, temp_message, result_text)

    except Exception as e:
        error_text = f"❌ **Error for `{display_name}`:**\nCould not fetch balance after login. Details: {e}"
        await send_final_message(client, temp_message, error_text)


@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Handles the /start command."""
    user_id = message.from_user.id
    user_data[user_id] = {'active': False}

    start_text = (
        "👋 **Welcome to the Balance Checker Bot!**\n\n"
        "Click the button below to check account balances."
    )
    start_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚖️ Check Balance", callback_data="check_balance_start")]
    ])
    await message.reply_text(start_text, reply_markup=start_button)


@app.on_message(filters.command("cancel"))
async def cancel_command(client: Client, message: Message):
    """Handles the /cancel command to stop any ongoing process."""
    user_id = message.from_user.id
    if user_data.get(user_id, {}).get('active'):
        user_data[user_id]['active'] = False
        await message.reply_text("🛑 **Process Cancelled!** The bot will stop after the current check is finished.")
    else:
        await message.reply_text("👍 There is no active process to cancel.")


@app.on_callback_query(filters.regex("check_balance_start"))
async def ask_for_numbers(client: Client, callback_query):
    """Asks the user for the account numbers after they click the button."""
    user_id = callback_query.from_user.id
    user_data[user_id] = {'step': 'awaiting_numbers', 'active': False}
    
    await callback_query.message.edit_text(
        "🔢 **Enter Account Number(s)**\n\n"
        "Please send the account number(s) you want to check.\n"
        "You can enter multiple numbers separated by a comma (`,`).\n\n"
        "**Examples:**\n"
        "➡️ Just `5`\n"
        "➡️ `7, 8, 9, 57`"
    )
    await callback_query.answer()


@app.on_message(filters.private & ~filters.command(["start", "cancel"]))
async def handle_number_input(client: Client, message: Message):
    """Handles the user's message containing the account number(s)."""
    user_id = message.from_user.id
    
    if user_data.get(user_id, {}).get('step') != 'awaiting_numbers':
        await start_command(client, message)
        return

    raw_input = message.text
    numbers_list = [num.strip() for num in raw_input.split(',') if num.strip().isdigit()]
    
    if not numbers_list:
        await message.reply_text("⚠️ **Invalid Input.** Please provide at least one valid number.")
        return
        
    user_data[user_id]['active'] = True
    user_data[user_id]['step'] = 'processing'

    total_accounts = len(numbers_list)
    await message.reply_text(
        f"✅ **Queued {total_accounts} account(s).**\n"
        f"Processing will begin now.\n\n"
        f"You can type /cancel to stop at any time."
    )

    for i, number_input in enumerate(numbers_list):
        if not user_data.get(user_id, {}).get('active', False):
            await message.reply_text("🏁 **Process stopped by user.**")
            break

        temp_status_message = await message.reply_text(f"▶️ Starting check for Account #{number_input} ({i+1}/{total_accounts})...")
        
        try:
            await get_balance(client, user_id, number_input, temp_status_message)
        except Exception as e:
            error_text = f"🚨 **Critical Error for Account #{number_input}:** {e}"
            await send_final_message(client, temp_status_message, error_text)
        
        await asyncio.sleep(2)
    else:
        await message.reply_text("🏁 **All accounts processed!**\nUse /start to begin a new session.")

    user_data[user_id] = {'active': False}


print("Bot is starting with settings from .env file...")
app.start()
print("Bot has started successfully!")

idle()
print("Bot is stopping...")
app.stop()
