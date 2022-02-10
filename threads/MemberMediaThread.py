import os
from pydoc import cli
import threading
import asyncio
import logging

from telethon import types

from processors.ApiProcessor import ApiProcessor

class MemberMediaThread(threading.Thread):
    def __init__(self, phone, member, tg_user):
        threading.Thread.__init__(self, name=f"MemberMediaThread-{member['id']}")
        
        self.media_path = f"./uploads/member/{member['id']}"

        self.phone = phone
        self.member = member
        self.tg_user = tg_user

        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)

    async def async_run(self):
        try:
            client = await self.phone.new_client(loop=self.loop)

            async for photo in client.iter_profile_photos(
                types.InputPeerUser(user_id=self.tg_user.id, access_hash=self.tg_user.access_hash)
            ):
                new_media = { 'internalId': photo.id }

                medias = ApiProcessor().get('member-media', new_media)

                if len(medias) > 0:
                    new_media = medias[0]

                    if os.path.exists(new_media['path']):
                        logging.debug(f"Member {self.member['id']} media {new_media['id']} exist. Continue.")
                    
                        await asyncio.sleep(1)

                        continue

                try:
                    def progress_callback(current, total):
                        logging.debug(f"Member {self.member['id']} media downloaded {current} out of {total} bytes: {current / total:.2%}")

                    path = await client.download_media(
                        message=photo,
                        file=f"{self.media_path}/{photo.id}",
                        # TODO: здесь надо проверить как обрабатываются видео
                        thumb=photo.sizes[-2],
                        progress_callback=progress_callback
                    )

                    if path != None:
                        new_media = { 
                            **new_media,
                            'member': {"id": self.member['id']}, 
                            'internalId': photo.id,
                            'createdAt': photo.date.isoformat(),
                            'path': path[2:]
                        }
                            
                        ApiProcessor().set('member-media', new_media)
                except Exception as ex:
                    logging.error(f"Can\'t save member {self.member['id']} media. Exception: {ex}.")
                else:
                    logging.info(f"Sucessfuly saved member {self.member['id']} media.")
        except Exception as ex:
            logging.error(f"Can't get member {self.member['id']} media using phone {self.phone.id}. Exception: {ex}.")

    def run(self):
        asyncio.run(self.async_run())
