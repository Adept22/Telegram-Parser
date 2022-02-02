
import random
import threading
import asyncio
import logging
import globalvars
from telethon import types
import re
import os.path

from processors.ApiProcessor import ApiProcessor
from utils import bcolors, user_title, formated_date

class ChatParserThread(threading.Thread):
    def __init__(self, chat):
        threading.Thread.__init__(self, name=f'ChatParserThread-{chat.id}')
        
        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
        
    def get_member(self, user):
        new_member = {
            'internalId': user.id,
            'username': user.username,
            'firstName': user.first_name,
            'lastName': user.last_name,
            'phone': user.phone
        }
        
        members = ApiProcessor().get('member', { 'internalId': user.id })
        
        if len(members) > 0:
            logging.debug(f'Member \'{user.first_name}\' exists in API.')
            
            if members[0].get('id') != None:
                new_member['id'] = members[0].get('id')
        
        return new_member
        
    def get_chat_member(self, member):
        new_chat_member = {
            'chat': { 'id': self.chat.id }, 
            'member': member
        }
        
        if new_chat_member['member'].get('id') != None:
            chat_members = ApiProcessor().get('chat-member', new_chat_member)
            
            if len(chat_members) > 0:
                if chat_members[0].get('id') != None:
                    new_chat_member['id'] = chat_members[0]['id']
        
        return new_chat_member
    
    def get_chat_member_role(self, participant, chat_member):
        new_chat_member_role = { 'member': chat_member }
        
        if isinstance(participant, types.ChannelParticipantAdmin):
            new_chat_member_role["title"] = (participant.rank if participant.rank != None else 'Администратор')
            new_chat_member_role["code"] = "admin"
        elif isinstance(participant, types.ChannelParticipantCreator):
            new_chat_member_role["title"] = (participant.rank if participant.rank != None else 'Создатель')
            new_chat_member_role["code"] = "creator"
        else:
            new_chat_member_role["title"] = "Участник"
            new_chat_member_role["code"] = "member"
        
        if new_chat_member_role['member'].get('id') != None:
            chat_member_roles = ApiProcessor().get('chat-member-role', new_chat_member_role)
            
            if len(chat_member_roles) > 0:
                if chat_member_roles[0].get('id') != None:
                    new_chat_member_role['id'] = chat_member_roles[0]['id']
                    
        return new_chat_member_role

    def get_api_member(self, peer_from):
        if isinstance(peer_from, types.PeerUser):
            members = ApiProcessor().get('member', { 'internalId': peer_from.user_id })
            
            if len(members) > 0:
                chat_members = ApiProcessor().get('chat-member', { 'chat': { 'id': self.chat.id }, 'member': { 'id': members[0]['id'] } })
                
                if len(chat_members) > 0:
                    return chat_members[0]
                
        return None
    
    # def get_reply_to(self, reply_to):
    #     if reply_to != None:
    #         reply_to_msgs = ApiProcessor().get('message', { 'internalId': reply_to.reply_to_msg_id })
            
    #         if len(reply_to_msgs) > 0:
    #             return reply_to_msgs[0]
            
    #     return None
    
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
            logging.info(f'{bcolors.OKGREEN} Recieving members from chat {self.chat.title}.{bcolors.ENDC}')
            
            try:
                client = await phone.new_client(loop=self.loop)
                chatEntity = types.PeerChannel(channel_id=self.chat.internal_id)
                members_uuis_list = []

                # api_chat_members = ApiProcessor().get('chat-member', {'chat': {'id': self.chat.id}})

                users = await client.get_participants(chatEntity)

                for user in users:
                    logging.debug(f'Chat {self.chat.title}. Received user \'{user_title(user)}\'')
                    
                    if user.id in globalvars.phones_tg_ids:
                        logging.debug(f'Chat {self.chat.id}. User \'{user.first_name}\' is our phone. Continue.')
                        
                        continue
                    
                    chat_member_role = self.get_chat_member_role(user.participant, self.get_chat_member(self.get_member(user)))

                    if (chat_member_role.get('id')):
                        member_uuis_item = {
                            chat_member_role['member']['member']['internalId']: chat_member_role['id']
                        }

                    members_uuis_list.append(member_uuis_item)

                    try:
                        member = chat_member_role
                        # chat_member_role = ApiProcessor().set('chat-member-role', chat_member_role) 
                    except Exception as ex:
                        logging.error(f"{bcolors.FAIL} Can\'t save member \'{user.first_name}\' with role: chat - {self.chat.title}. Exception: {ex}.{bcolors.ENDC}")

                        continue
                    
                    logging.debug(f"Member \'{user_title(user)}\' with role saved.")

                    member = chat_member_role['member']['member']

                last_message = { 'internalId': 0, 'groupedId': 0 }
                
                messages = ApiProcessor().get('message', { 'chat': { 'id': self.chat.id }, '_limit': 1, '_sort': 'internalId', '_order': 'ASC' })
                
                if len(messages) > 0:
                    logging.info(f'Last message in API exist. Continue.')

                    last_message = messages[0]
                
                index = 0

                messages_pack = await client.get_messages(
                    entity=chatEntity, 
                    limit=3000,
                    reverse=True
                )

                messages_total = messages_pack.total

                logging.info(f'Chat {self.chat.id} total messages {messages_pack.total}.')

                # while (index <= messages_total):
                for message in messages_pack:
                    index += 1
                    
                    logging.debug(f'Chat {self.chat.id}. Receive message {index}/{messages_total}')
                    
                    if not isinstance(message, types.Message):
                        continue
                    
                    if isinstance(message.peer_id, types.PeerUser):
                        if message.peer_id.user_id in globalvars.phones_tg_ids:
                            logging.debug(f'Chat {self.chat.id}. Message {index} is our phone message. Continue.')
                            
                            continue
                    
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
                            'member': self.get_api_member(message.from_id), 
                            # 'replyTo': self.get_reply_to(message.reply_to), 
                            'replyInternalId': message.reply_to_msg_id, 
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

                    # messages_pack = await client.get_messages(
                    #     entity=chatEntity, 
                    #     limit=3000,
                    #     reverse=True,
                    #     min_id=index
                    # )

            except Exception as ex:
                logging.error(f"Can\'t get chat {self.chat.id} messages using phone {phone.id}. Exception: {ex}.")
        else:
            logging.error(f'Cannot get chat {self.chat.id} participants. Exit code 1.')
        
            ApiProcessor().set('chat', { 'id': self.chat.id, 'isAvailable': False })
            
        self.chat.chat_parser_thread = None
        self.messages_parser_thread = None


        
    def run(self):
        asyncio.run(self.async_run())
