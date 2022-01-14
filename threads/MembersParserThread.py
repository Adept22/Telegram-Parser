import random
import threading
import asyncio
import logging
from unicodedata import name
from telethon import types

from utils import bcolors
from processors.ApiProcessor import ApiProcessor

class MembersParserThread(threading.Thread):
    def __init__(self, chat):
        threading.Thread.__init__(self, name=f'MembersParserThread-{chat.id}')
        
        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
        
    def save_member(self, user):
        member = {}
        
        members = ApiProcessor().get('member', { 'internalId': user.id })
        
        if len(members) > 0:
            logging.debug(f'Member \'{user.first_name}\' founded in API.')
            
            member = members[0]
        
        try: 
            logging.debug(f'Try to save member \'{user.first_name}\'')
            
            new_member = {
                'internalId': user.id,
                'username': user.username,
                'firstName': user.first_name,
                'lastName': user.last_name,
                'phone': user.phone
            }
            
            if member.get('id') != None:
                new_member['id'] = member['id']
            
            member = ApiProcessor().set('member', new_member)
        except Exception as ex:
            logging.error(f"Can\'t save chat {self.chat.id} member. Exception: {ex}.")

            raise Exception(f'Can\'t save member of chat {self.chat.id}')
        else:
            logging.info(f'Member \'{member["id"]}\' saved.')
        
        return member
        
    def save_chat_member(self, member):
        chat_member = {}
        
        chat_members = ApiProcessor().get('chat-member', { 'chat': { 'id': self.chat.id }, 'member': { 'id': member['id'] } })
        
        if len(chat_members) > 0:
            logging.debug(f"Chat-member {member['id']} founded in API.")
            
            chat_member = chat_members[0]
            
        try:
            logging.debug(f"Try to save chat-member: chat - {self.chat.id}, member - {member['id']}.")
            
            new_chat_member = {
                'chat': { 'id': self.chat.id }, 
                'member': { 'id': member['id'] } 
            }
            
            if chat_member.get('id') != None:
                new_chat_member['id'] = chat_member['id']
            
            chat_member = ApiProcessor().set('chat-member', new_chat_member)
        except Exception as ex:
            logging.error(f"Can\'t save chat-member chat: {self.chat.id} member: {member['id']}. Exception: {ex}.")

            raise Exception(f'Can\'t create chat-member entity. Exception: {ex}')
        else:
            logging.info(f'Chat member \'{chat_member["id"]}\' saved.')
        
        return chat_member
    
    def save_chat_member_role(self, participant, chat_member):
        chat_member_role = {}
        
        if isinstance(participant, types.ChannelParticipantAdmin):
            title = (participant.rank if participant.rank != None else 'Администратор')
            code = "admin"
        elif isinstance(participant, types.ChannelParticipantCreator):
            title = (participant.rank if participant.rank != None else 'Создатель')
            code = "creator"
        else:
            title = "Участник"
            code = "member"
            
        chat_member_roles = ApiProcessor().get('chat-member-role', { 'member': {'id': chat_member['id']}, 'title': title, 'code': code })
        
        if len(chat_member_roles) > 0:
            logging.debug(f"Chat-member-role for chat-member {chat_member['id']} founded in API.")
            
            chat_member_role = chat_member_roles[0]
            
        try:
            logging.debug(f"Try to save chat-member-role: chat - {self.chat.id}, chat-member - {chat_member['id']}.")
            
            new_chat_member_role = {
                'member': { 'id': chat_member['id'] }, 
                'title': title, 
                'code': code 
            }
            
            if chat_member_role.get('id') != None:
                new_chat_member_role['id'] = chat_member_role['id']
            
            chat_member_role = ApiProcessor().set('chat-member-role', new_chat_member_role)
        except Exception as ex:
            logging.error(f"Can\'t save chat-member-role: chat - {self.chat.id}, chat-member - {chat_member['id']}. Exception: {ex}.")
        
            raise Exception(f'Can\'t create chat-member-role entity. Exception: {ex}')
        else:
            logging.info(f'Chat member role \'{chat_member_role["id"]}\' saved.')
                    
        return chat_member_role
    
    async def async_run(self):
        for phone in self.chat.phones:
            logging.info(f'Recieving members from chat {self.chat.id}.')
            
            try:
                client = await phone.new_client(loop=self.loop)
                
                async for user in client.iter_participants(entity=types.PeerChannel(channel_id=self.chat.internal_id)):
                    logging.debug(f'Chat {self.chat.id}. Received user \'{user.first_name}\'')
                    
                    self.save_chat_member_role(user.participant, self.save_chat_member(self.save_member(user)))
                    
                    # TODO: Здесь должна быть выкачка аватарок
                    # async for photo in client.iter_profile_photos(types.PeerUser(user_id=user.id)):
                    #     pass
            except Exception as ex:
                logging.error(f"Can\'t get chat {self.chat.id} participants using phone {phone.id}. Exception: {ex}.")
                
                await asyncio.sleep(random.randint(2, 5))
                
                continue
            else:
                logging.info(f"Chat {self.chat.id} participants download success. Exit code 0.")
                
                break
        else:
            ApiProcessor().set('chat', { 'id': self.chat.id, 'isAvailable': False })
            
            raise Exception(f'Cannot get chat {self.chat.id} participants. Exit code 1.')
        
    def run(self):
        asyncio.run(self.async_run())