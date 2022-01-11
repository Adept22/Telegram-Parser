import random
import logging
import threading
import asyncio
from telethon import types, events

from processors.ApiProcessor import ApiProcessor
from utils import bcolors

class MessagesParserThread(threading.Thread):
    def __init__(self, chat):
        print(f"Creating chat {chat.id} messages parsing thread...")
        logging.debug(f"Creating chat {chat.id} messages parsing thread...")
        
        threading.Thread.__init__(self)
        
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
    
    async def async_run(self):
        for phone in self.chat.phones:
            print(f'Try to recieve messages from chat {self.chat.id}.')
            logging.debug(f'Try to recieve messages from chat {self.chat.id}.')
            
            try:
                client = await phone.new_client(loop=self.loop)
                
                last_message = { 'internalId': 0 }
                
                messages = ApiProcessor().get('message', { 'chat': { 'id': self.chat.id }, '_limit': 1, '_sort': 'internalId', '_order': 'DESC' })
                
                if len(messages) > 0:
                    last_message = messages[0]
                
                index = 1
                all_messages = await client.get_messages(
                    types.PeerChannel(channel_id=self.chat.internal_id), 
                    0, 
                    offset_id=last_message['internalId']
                )
                
                async for message in client.iter_messages(
                    entity=types.PeerChannel(channel_id=self.chat.internal_id), 
                    offset_id=last_message['internalId']
                ):
                    if not isinstance(message, types.Message):
                        continue
                    
                    print(f'Chat {self.chat.id}. Received message \'{message.id}\' at \'{message.date}\'. {index}/{all_messages.total}')
                    logging.debug(f'Chat {self.chat.id}. Received message \'{message.id}\' at \'{message.date}\'. {index}/{all_messages.total}')
                    
                    messages = ApiProcessor().get('message', { 'internalId': message.id, 'chat': { "id": self.chat.id } })
                    
                    if len(messages) > 0:
                        print(f'Chat {self.chat.id}. Message {messages[0]}. Message exist. Continue.')
                        logging.debug(f'Chat {self.chat.id}. Message {messages[0]}. Message exist. Continue.')
                        
                        continue
                    
                    try: 
                        print(f'Try to save message \'{message.id}\' at \'{message.date}\'')
                        logging.debug(f'Try to save message \'{message.id}\' at \'{message.date}\'')
                        
                        fwd_from_id, fwd_from_name = self.get_fwd(message.fwd_from)
                        
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
                        print(f"{bcolors.FAIL}Can\'t save chat {self.chat.id} message. Exception: {ex}.{bcolors.ENDC}")
                        logging.error(f"Can\'t save chat {self.chat.id} message. Exception: {ex}.")
                    # else:
                    #     if message.media != None:
                    #         message_media_thread = MessageMediaThread(self, message)
                    #         message_media_thread.setDaemon(True)
                    #         message_media_thread.start()
                            
                    # TODO: Здесь должна быть выкачка вложений
                    
                    index += 1
            except Exception as ex:
                print(f"{bcolors.FAIL}Can\'t get chat {self.chat.id} messages using phone {phone.id}. Exception: {ex}.{bcolors.ENDC}")
                logging.error(f"Can\'t get chat {self.chat.id} messages using phone {phone.id}. Exception: {ex}.")
                
                await asyncio.sleep(random.randint(2, 5))
                
                continue
            else:
                break
        else:
            ApiProcessor().set('chat', { 'id': self.chat.id, 'isAvailable': False })
            
            raise Exception(f'Chat {self.chat.id} messages download failed. Exit code 1.')
        
        print(f"{bcolors.OKGREEN}Chat {self.chat.id} messages download success. Exit code 0.{bcolors.ENDC}")
        logging.info(f"Chat {self.chat.id} messages download success. Exit code 0.")

        
    def run(self):
        asyncio.run(self.async_run())