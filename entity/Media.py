from abc import ABC, abstractmethod
import math
from telethon import sync, client as telegramclient
from processors.ApiProcessor import ApiProcessor

class Media(ABC):
    def __init__(self) -> None:
        pass

    @abstractmethod
    def serialize(self):
        pass

    @property
    @abstractmethod
    def name(self):
        pass

    async def upload(self, client: 'sync.TelegramClient', tg_media, file_size):
        body = self.serialize()
        chunk_number = 0
        chunk_size=telegramclient.downloads.MAX_CHUNK_SIZE
        total_chunks = math.ceil(file_size / chunk_size)
        
        async for chunk in client.iter_download(
            file=tg_media, 
            chunk_size=chunk_size, 
            file_size=file_size
        ):
            ApiProcessor()._chunk(f'telegram/{self.name}-media', body, str(tg_media.id), chunk, chunk_number, chunk_size, total_chunks, file_size)

            chunk_number += 1