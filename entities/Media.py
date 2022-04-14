import math
from abc import ABC, abstractmethod
from telethon.client import downloads

import entities
from services import ApiService

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from telethon import TelegramClient

class Media(ABC):
    @abstractmethod
    def serialize(self) -> 'entities.TypeMedia':
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> 'str':
        raise NotImplementedError

    async def upload(self, client: 'TelegramClient', tg_media, file_size: 'int') -> 'None':
        body = self.serialize()
        chunk_number = 0
        chunk_size=downloads.MAX_CHUNK_SIZE
        total_chunks = math.ceil(file_size / chunk_size)
        
        async for chunk in client.iter_download(
            file=tg_media, 
            chunk_size=chunk_size, 
            file_size=file_size
        ):
            ApiService()._chunk(f'telegram/{self.name}-media', body, str(tg_media.id), chunk, chunk_number, chunk_size, total_chunks, file_size)

            chunk_number += 1