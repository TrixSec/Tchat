import asyncio
import aiohttp
import logging
# Anirudh branch test commit

class TelegramRelay:
    def __init__(self, message_callback):
        # Maps username -> { "token": token, "chat_id": chat_id }
        self.user_configs = {}
        # Maps token -> asyncio.Task
        self.active_pollers = {}
        # Callback function: message_callback(username, text) to post telegram messages to terminal chat
        self.message_callback = message_callback
        # Keep track of offsets to avoid double-processing Telegram updates: token -> last_update_id
        self.offsets = {}
        self.running = True

    def register_user(self, username, token, chat_id):
        """Registers a user's Telegram credentials and starts polling if needed."""
        if not token or not chat_id:
            return
            
        self.user_configs[username] = {
            "token": token,
            "chat_id": chat_id
        }
        
        # Start a polling task for this bot token if it is not already being polled
        if token not in self.active_pollers:
            task = asyncio.create_task(self._telegram_polling_loop(token))
            self.active_pollers[token] = task

    def get_user_config(self, username):
        return self.user_configs.get(username)

    async def send_offline_message(self, username, text):
        """Sends a message via Telegram to a user who is currently offline."""
        config = self.user_configs.get(username)
        if not config:
            return False
            
        token = config.get("token")
        chat_id = config.get("chat_id")
        if not token or not chat_id:
            return False
            
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("ok", False)
            return False
        except Exception as e:
            logging.error(f"Error sending Telegram notification to {username}: {e}")
            return False

    async def _telegram_polling_loop(self, token):
        """Background loop to poll Telegram updates for a specific bot token."""
        offset = 0
        self.offsets[token] = offset
        
        while self.running:
            try:
                url = f"https://api.telegram.org/bot{token}/getUpdates"
                params = {"timeout": 10}
                if offset > 0:
                    params["offset"] = offset
                    
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params, timeout=15) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("ok"):
                                for update in data.get("result", []):
                                    update_id = update["update_id"]
                                    offset = update_id + 1
                                    self.offsets[token] = offset
                                    
                                    # Process message
                                    message = update.get("message")
                                    if not message:
                                        continue
                                        
                                    chat_id = str(message["chat"]["id"])
                                    text = message.get("text")
                                    if not text:
                                        continue
                                        
                                    # Find user(s) matching this token and chat_id
                                    matched_users = []
                                    for user, cfg in self.user_configs.items():
                                        if cfg["token"] == token and str(cfg["chat_id"]) == chat_id:
                                            matched_users.append(user)
                                            
                                    for user in matched_users:
                                        # Trigger callback to push to terminal chat
                                        self.message_callback(user, text)
                        elif resp.status == 401:
                            # Unauthorized (invalid token) - stop polling for this token
                            logging.error(f"Invalid Telegram token: {token[:10]}... Stopping poll.")
                            break
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error and wait a bit before retrying
                await asyncio.sleep(5)
                continue
                
            await asyncio.sleep(1)

    def shutdown(self):
        """Stops all polling loops."""
        self.running = False
        for task in self.active_pollers.values():
            task.cancel()
