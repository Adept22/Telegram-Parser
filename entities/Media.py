import math, typing
from abc import ABC, abstractmethod
import telethon
from telethon.client import downloads

import entities
from services import ApiService

if typing.TYPE_CHECKING:
    from telethon import TelegramClient

class Media(ABC):
    @abstractmethod
    def serialize(self) -> 'entities.TypeMedia':
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> 'str':
        raise NotImplementedError

    async def upload(
        self, 
        client: 'TelegramClient', 
        tg_media, 
        file_size: 'int',
        extension: 'str'
    ) -> 'None':
        if not file_size or self.id == None:
            return

        media = ApiService().get(f'telegram/{self.name}', {"id": self.id})

        if media.get("path") != None:
            return

        chunk_number = 0
        chunk_size=downloads.MAX_CHUNK_SIZE
        total_chunks = math.ceil(file_size / chunk_size)

        async for chunk in client.iter_download(
            file=tg_media,
            chunk_size=chunk_size, 
            file_size=file_size
        ):
            ApiService()._chunk(
                f'telegram/{self.name}', 
                self.serialize(), 
                str(tg_media.id) + extension, 
                chunk, 
                chunk_number, 
                chunk_size, 
                total_chunks, 
                file_size
            )

            chunk_number += 1