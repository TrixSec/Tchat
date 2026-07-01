print("relay.py loaded")

import asyncio
import aiohttp

BOT_TOKEN = "8728310235:AAFNjzvK-O_Tuo2QJ0DqJWUMcTm5Zo3rQ-8"
CHAT_ID = "-1003941220457"  

async def send_to_telegram(text: str):
    print("send_to_telegram called:", text)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                print("Telegram Status:", response.status)
                print("Telegram Response:", await response.text())
    except Exception as e:
        print("Telegram relay error:", e)

async def start_telegram_polling(on_message_callback):
    """
    Long-polls the Telegram API for new messages in the group.
    """
    offset = None
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    
    print("Started Telegram listener...")
    while True:
        try:
            params = {"timeout": 30, "allowed_updates": ["message"]}
            if offset:
                params["offset"] = offset

            timeout = aiohttp.ClientTimeout(total=40)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("ok"):
                            for update in data.get("result", []):
                                offset = update["update_id"] + 1
                                if "message" in update and "text" in update["message"]:
                                    msg = update["message"]
                                    chat_id = str(msg.get("chat", {}).get("id"))
                                    chat_type = msg.get("chat", {}).get("type")
                                    if chat_id == CHAT_ID:
                                        sender = msg.get("from", {}).get("first_name", "Unknown")
                                        text = msg["text"]
                                        await on_message_callback(sender, text)
                                    elif chat_type == "private":
                                        text = msg["text"]
                                        await send_to_telegram(text)
        except asyncio.CancelledError:
            print("Telegram listener cancelled.")
            break
        except Exception as e:
            print(f"Telegram polling error: {e}")
            await asyncio.sleep(5)