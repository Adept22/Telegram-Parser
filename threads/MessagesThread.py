import threading
import asyncio
import logging
from telethon import types, errors
from errors.UniqueConstraintViolationError import UniqueConstraintViolationError

from threads.MessageMediaThread import MessageMediaThread
from processors.ApiProcessor import ApiProcessor
from threads.KillableThread import KillableThread

class MessagesThread(KillableThread):
    def __init__(self, chat):
        threading.Thread.__init__(self, name=f"MessagesThread-{chat.id}")
        self.daemon = True
        
        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)

    def get_member(self, user):
        if isinstance(user, types.PeerUser):
            new_member = { 'internalId': user.id }

            try:
                member = ApiProcessor().set('telegram/member', new_member)
            except UniqueConstraintViolationError:
                members = ApiProcessor().get('telegram/member', new_member)
                
                member = members[0]
            
            return member
        
        return None

    def get_chat_member(self, member):
        new_chat_member = {
            'chat': { 'id': self.chat.id },
            'member': { 'id': member['id'] }
        }

        try:
            chat_member = ApiProcessor().set('telegram/chat-member', new_chat_member)
        except UniqueConstraintViolationError:
            members = ApiProcessor().get('telegram/chat-member', new_chat_member)
            
            chat_member = members[0]
        
        return chat_member
        
    def get_reply_to(self, reply_to):
        if reply_to != None:
            new_reply_to = {
                'internalId': reply_to.reply_to_msg_id,
                'chat': { 'id': self.chat.id }
            }

            messages = ApiProcessor().get('telegram/message', new_reply_to)

            if len(messages) > 0:
                new_reply_to['id'] = messages[0]['id']
                
            return new_reply_to

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

    async def get_entity(self, client):
        try:
            return await client.get_entity(entity=types.PeerChannel(channel_id=self.chat.internal_id))
        except ValueError:
            return await client.get_entity(entity=types.PeerChat(chat_id=self.chat.internal_id))

    async def async_run(self):
        for phone in self.chat.phones:
            logging.info(f"Recieving messages from chat {self.chat.id}.")
            
            try:
                client = await phone.new_client(loop=self.loop)
                
                new_message = { 'internalId': 0, 'groupedId': 0 }
                
                # messages = ApiProcessor().get('message', { 'chat': { 'id': self.chat.id }, '_limit': 1, '_sort': 'internalId', '_order': 'ASC' })
                
                # if len(messages) > 0:
                #     logging.info(f"Last message in API exist. Continue."")

                #     new_message = messages[0]

                entity = await self.get_entity(client)
                
                all_messages = await client.get_messages(entity=entity, limit=0, max_id=new_message['internalId'])

                logging.info(f"Chat {self.chat.id} total messages {all_messages.total}.")

                async for tg_message in client.iter_messages(entity=entity, max_id=new_message['internalId']):
                    logging.debug(f"Chat {self.chat.id}. Receive message {tg_message.id}/{all_messages.total}")
                    
                    if not isinstance(tg_message, types.Message):
                        continue
                    
                    try:
                        logging.debug(f"Saving message '{tg_message.id}' at '{tg_message.date}'")
                        
                        fwd_from_id, fwd_from_name = self.get_fwd(tg_message.fwd_from)

                        member = self.get_member(tg_message.from_id)

                        new_message = { 
                            'internalId': tg_message.id, 
                            'text': tg_message.message, 
                            'chat': { 'id': self.chat.id }, 
                            'member': self.get_chat_member(member),
                            'replyTo': self.get_reply_to(tg_message.reply_to), 
                            'isPinned': tg_message.pinned,     
                            'forwardedFromId': fwd_from_id, 
                            'forwardedFromName': fwd_from_name, 
                            'groupedId': tg_message.grouped_id, 
                            'date': tg_message.date.isoformat() 
                        }

                        try:
                            ApiProcessor().set('telegram/message', new_message)
                        except UniqueConstraintViolationError:
                            messages = ApiProcessor().get('telegram/message', { 'internalId': new_message['internalId'] })
                            
                            new_message['id'] = messages[0]['id']

                            ApiProcessor().set('telegram/message', new_message)
                    except Exception as ex:
                        logging.error(f"Can't save chat {self.chat.id} message.")
                        logging.exception(ex)
                    else:
                        logging.debug(f"Message '{new_message['id']}' at '{new_message['createdAt']}' saved.")

                        if tg_message.media != None:
                            meessage_media_thread = MessageMediaThread(phone, new_message, tg_message)
                            meessage_media_thread.start()
                else:
                    logging.info(f"Chat {self.chat.id} messages download success.")
            except (
                errors.ChannelInvalidError,
                errors.ChannelPrivateError,
                errors.ChatIdInvalidError,
                errors.PeerIdInvalidError
            ) as ex:
                logging.error(f"Chat {self.chat.id} not available.")
                logging.exception(ex)

                self.chat.is_available = False
            except Exception as ex:
                logging.error(f"Can\'t get chat {self.chat.id} messages using phone {phone.id}.")
                logging.exception(ex)

                self.chat.remove_phone(phone)
                
                continue
            else:
                break
        else:
            logging.error(f"Chat {self.chat.id} messages download failed.")
        
    def run(self):
        self.chat.init_event.wait()
        
        asyncio.run(self.async_run())