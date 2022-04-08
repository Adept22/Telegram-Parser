
import logging
from abc import ABC, abstractmethod
import os
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

    async def upload(self, client, tg_media):
        def progress_callback(current, total):
            logging.debug(f"Member {self.entity.id} media downloaded {current} out of {total} bytes: {current / total:.2%}")

        path = await client.download_media(
            message=tg_media,
            file= f"{self.download_path}/{self.entity.id}/{tg_media.id}",
            thumb=tg_media.sizes[-2],
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