import aiohttp

async def verify_telegram_bot(token):
    """
    Verifies if a Telegram bot token is valid by hitting the getMe endpoint.
    Returns (success_bool, info_str)
    """
    if not token:
        return False, "Token is empty"
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("ok"):
                        bot_username = data["result"].get("username", "Bot")
                        return True, bot_username
                    return False, data.get("description", "Unknown error")
                return False, f"HTTP Error {resp.status}"
    except Exception as e:
        return False, str(e)
