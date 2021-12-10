from config import API_ID, API_HASH, USERNAME
from telethon.sync import TelegramClient
from decorators.singleton import singleton

@singleton
class ClientFactory:
    def __init__(self):
        self.api_id = API_ID
        self.api_hash = API_HASH
        self.username = USERNAME
        self.client = TelegramClient(self.username, self.api_id, self.api_hash)
        self.client.start()

    def get_client(self):
        return self.client
