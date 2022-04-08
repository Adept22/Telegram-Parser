
import logging
from abc import ABC, abstractmethod
import os
from telethon import sync
from processors.ApiProcessor import ApiProcessor

class Media(ABC):
    @property
    @abstractmethod
    def download_path(self):
        pass

    @property
    @abstractmethod
    def name(self):
        pass

    @property
    @abstractmethod
    def entity(self):
        pass

    async def upload(self, client: 'sync.TelegramClient', tg_media, thumb = None):
        def progress_callback(current, total):
            logging.debug(f"Member {self.entity.id} media downloaded {current} out of {total} bytes: {current / total:.2%}")

        path = await client.download_media(
            message=tg_media,
            file= f"{self.download_path}/{self.entity.id}/{tg_media.id}",
            thumb=thumb,
            progress_callback=progress_callback
        )

        if path != None:
            try:
                ApiProcessor().chunked(f'telegram/{self.name}-media', self.serialize(), path)
            except Exception as ex:
                raise ex
            else:
                try:
                    os.remove(path)
                except:
                    pass
        else:
            raise Exception(f"Can\'t download {self.name} {self.entity.id} media.")