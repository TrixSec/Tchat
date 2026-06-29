import asyncio
import aiohttp

BOT_TOKEN = "8859384964:AAEzPkc6D-UYeM1YRoP7fCmNbnJpbwU76zo"
CHAT_ID = 8550654321

async def main():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": "Hello from TermChat!"
            }
        ) as response:
            print(await response.json())

asyncio.run(main())