from re import split 
import random
import threading
import asyncio
import logging
from telethon import types
from utils import bcolors, formated_date

from processors.ApiProcessor import ApiProcessor

class MessagesParserThread(threading.Thread):
    def __init__(self, chat):
        threading.Thread.__init__(self, name=f'MessagesParserThread-{chat.id}')
        
        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
        
    def get_member(self, peer_id):
        if isinstance(peer_id, types.PeerUser):
            members = ApiProcessor().get('member', { 'internalId': peer_id })
            
            if len(members) > 0:
                chat_members = ApiProcessor().get('chat-member', { 'chat': { 'id': self.chat.id }, 'member': { 'id': members[0]['id'] } })
                
                if len(chat_members) > 0:
                    return chat_members[0]
                
        return None
    
    def get_reply_to(self, reply_to):
        if reply_to != None:
            reply_to_msgs = ApiProcessor().get('message', { 'internalId': reply_to.reply_to_msg_id })
            
            if len(reply_to_msgs) > 0:
                return reply_to_msgs[0]
            
        return None
    
    def get_fwd(self, fwd_from):
        fwd_from_id = None
        fwd_from_name = None
        
        if fwd_from != None:
            if fwd_from.from_id != None:
                if type(fwd_from.from_id) == types.PeerChannel:
                    fwd_from_id = fwd_from.from_id.channel_id
                elif type(fwd_from.from_id) == types.PeerUser:
                    fwd_from_id = fwd_from.from_id.user_id
            
            if fwd_from.from_name != None:
                fwd_from_name = fwd_from.from_name
            else:
                fwd_from_name = "Неизвестно"
                
        return fwd_from_id, fwd_from_name

    async def download_media(self, client, last_message, message):
        def progress_callback(current, total):
            logging.debug(f'Message \'{last_message["id"]}\' media downloaded {current} out of {total} bytes: {current / total:.2%}')
        async def file_download():
            path = await client.download_media(
                message=message,
                file=f'./uploads/messages/{self.chat.id}/{last_message["id"]}/{message.id}',
                progress_callback=progress_callback
            )

            if path != None:
                media = ApiProcessor().set('message-media', { 
                    'message': { "id": last_message["id"] }, 
                    'path': f'/uploads/{self.chat.id}/{last_message["id"]}/{split("/", path)[-1]}', 
                })
        try:
            logging.debug(f'Try to save message \'{last_message["id"]}\' media.')
            
            if isinstance(message.media, types.MessageMediaPoll):
                pass
            elif isinstance(message.media, types.MessageMediaVenue):
                pass
            elif isinstance(message.media, types.MessageMediaContact):
                pass
            elif isinstance(message.media, types.MessageMediaPhoto):
                await file_download()
            elif isinstance(message.media, types.MessageMediaDocument):
                await file_download()

        except Exception as ex:
            logging.error(f"Can\'t save message {last_message['id']} media. Exception: {ex}.")

    async def async_run(self):
        for phone in self.chat.phones:
            logging.info(f'Recieving messages from chat {self.chat.id}.')
            
            try:
                client = await phone.new_client(loop=self.loop)
                
                last_message = { 'internalId': 0, 'groupedId': 0 }
                
                messages = ApiProcessor().get('message', { 'chat': { 'id': self.chat.id }, '_limit': 1, '_sort': 'internalId', '_order': 'ASC' })
                
                if len(messages) > 0:
                    logging.info(f'Last message in API exist. Continue.')

                    last_message = messages[0]
                
                index = 1
                entity = await client.get_entity(types.PeerChannel(channel_id=self.chat.internal_id))
                
                # try:
                #     photos = await client.get_profile_photos(entity)
                # except Exception as ex:
                #     logging.error(f"Can\'t get {self.chat.title} media list. Exception: {ex}.")
                # else:
                #     logging.info(f'{bcolors.OKGREEN} Sucessfuly saved channel {self.chat.title} media!{bcolors.ENDC}')
                
                # if photos:
                #     for photo in photos:
                #         savedPhotos = ApiProcessor().get('chat-media', { 'internalId': photo.id})
                        
                #         if len(savedPhotos) > 0:
                #             logging.debug(f'Chat {self.chat.id}. Chat-media {savedPhotos[0]} exist. Continue.')
                        
                #             continue

                #         try:
                #             pathFolder = f'./uploads/chat-media/{self.chat.id}'

                #             pathToFile = await client.download_media(
                #                 message=photo,
                #                 file=f'{pathFolder}/{photo.id}',
                #                 thumb=photo.sizes[-2]
                #             )

                #             if pathToFile != None:
                #                 ApiProcessor().set('chat-media', { 
                #                     'chat-media': { "id": self.chat.id }, 
                #                     'internalId': photo.id,
                #                     'createdAt': formated_date(photo.date),
                #                     'path': f'{pathFolder}/{split("/", pathToFile)[-1]}'
                #                 })

                #         except Exception as ex:
                #             logging.error(f"Can\'t save channel {self.chat} media. Exception: {ex}.")
                #         else:
                #             logging.info(f'{bcolors.OKGREEN} Sucessfuly saved channel {self.chat.title} media!{bcolors.ENDC}')

                all_messages = await client.get_messages(
                    entity=entity, 
                    limit=0,
                    max_id=last_message['internalId']
                )
                logging.info(f'Chat {self.chat.id} total messages {all_messages.total}.')

                async for message in client.iter_messages(
                    entity=entity,
                    max_id=last_message['internalId']
                ):
                    index += 1
                    
                    if not isinstance(message, types.Message):
                        continue
                    
                    logging.debug(f'Chat {self.chat.id}. Received message \'{message.id}\' at \'{message.date}\'. {index}/{all_messages.total}')
                    
                    messages = ApiProcessor().get('message', { 'internalId': message.id, 'chat': { "id": self.chat.id } })
                    
                    if len(messages) > 0:
                        logging.debug(f'Chat {self.chat.id}. Message {messages[0]["id"]} exist. Continue.')
                        
                        continue
                    
                    try: 
                        logging.debug(f'Saving message \'{message.id}\' at \'{message.date}\'')
                        
                        fwd_from_id, fwd_from_name = self.get_fwd(message.fwd_from)
                        
                        # if (message.grouped_id != last_message['groupedId']):
                        
                        last_message = ApiProcessor().set('message', { 
                            'internalId': message.id, 
                            'text': message.message, 
                            'chat': { "id": self.chat.id }, 
                            'member': self.get_member(message.peer_id), 
                            'replyTo': self.get_reply_to(message.reply_to), 
                            'isPinned': message.pinned, 
                            'forwardedFromId': fwd_from_id, 
                            'forwardedFromName': fwd_from_name, 
                            'groupedId': message.grouped_id, 
                            'createdAt': message.date.isoformat() 
                        })

                    except Exception as ex:
                        logging.error(f"Can\'t save chat {self.chat.id} message. Exception: {ex}.")
                    else:
                        logging.debug(f'Message \'{last_message["id"]}\' at \'{last_message["createdAt"]}\' saved.')
                        await self.download_media(
                            client=client,
                            last_message=last_message,
                            message=message
                        )
                else:
                    logging.info(f"🏁 Chat {self.chat.id} messages download success. Exit code 0 🏁")
            except Exception as ex:
                logging.error(f"Can\'t get chat {self.chat.id} messages using phone {phone.id}. Exception: {ex}.")
                
                await asyncio.sleep(random.randint(2, 5))
                
                continue
            else:
                break
        else:
            logging.error(f"Can\'t get chat {self.chat.id} messages.")

            ApiProcessor().set('chat', { 'id': self.chat.id, 'isAvailable': False })
            
            raise Exception(f'Chat {self.chat.id} messages download failed. Exit code 1.')
        
    def run(self):
        asyncio.run(self.async_run())