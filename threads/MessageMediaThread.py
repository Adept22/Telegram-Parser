import os
import threading
import asyncio
import logging
from telethon import types

from processors.ApiProcessor import ApiProcessor
from threads.KillableThread import KillableThread

class MessageMediaThread(KillableThread):
    def __init__(self, phone, message, tg_message):
        threading.Thread.__init__(self, name=f"MessageMediaThread-{message['id']}")
        self.daemon = True

        self.media_path = f"./downloads/chat/{message['chat']['id']}/messages/{message['id']}"
        
        self.phone = phone
        self.message = message
        self.tg_message = tg_message

        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
    
    async def file_download(self, client, media):
        new_media = { 'internalId': media.id }

        medias = ApiProcessor().get('telegram/message-media', new_media)

        if len(medias) > 0:
            new_media = medias[0]
                                
            if 'path' in new_media and new_media['path'] != None:
                logging.debug(f"Message {self.message['id']} media {new_media['id']} exist on server. Continue.")

                return

        def progress_callback(current, total):
            logging.debug(f"Message {self.message['id']} media downloaded {current} out of {total} bytes: {current / total:.2%}")

        try:
            path = await client.download_media(
                message=media,
                file=f"{self.media_path}/{media.id}",
                progress_callback=progress_callback
            )

            if path != None:
                new_media = {
                    **new_media,
                    'message': {"id": self.message['id']}, 
                    'date': media.date.isoformat()
                }

                new_media = ApiProcessor().set('telegram/message-media', new_media)

                try:
                    ApiProcessor().upload('telegram/message-media', new_media, path)
                except Exception as ex:
                    logging.error(f"Can\'t upload message {self.message['id']} media.")
                    logging.exception(ex)
                else:
                    logging.info(f"Sucessfuly uploaded message {self.message['id']} media.")
                
                    try:
                        os.remove(path)
                    except:
                        pass
        except Exception as ex:
            logging.error(f"Can't save message {self.message['id']} media.")
            logging.exception(ex)
        else:
            logging.info(f"Sucessfuly saved message {self.message['id']} media!")

    async def async_run(self):
        try:
            logging.debug(f"Try to save message '{self.message['id']}' media.")

            client = await self.phone.new_client(loop=self.loop)
            
            if isinstance(self.tg_message.media, types.MessageMediaPoll):
                pass
            elif isinstance(self.tg_message.media, types.MessageMediaVenue):
                pass
            elif isinstance(self.tg_message.media, types.MessageMediaContact):
                pass
            elif isinstance(self.tg_message.media, types.MessageMediaPhoto):
                await self.file_download(client, self.tg_message.photo)
            elif isinstance(self.tg_message.media, types.MessageMediaDocument):
                await self.file_download(client, self.tg_message.document)
        except Exception as ex:
            logging.error(f"Message {self.message['id']} media download failed.")
            logging.exception(ex)
        else:
            logging.info(f"Message {self.message['id']} media download success.")
        
    def run(self):
        asyncio.run(self.async_run())