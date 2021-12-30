import os
import random
import logging
import threading
import asyncio
from telethon import functions, types

from processors.ApiProcessor import ApiProcessor
from utils.bcolors import bcolors
from models.User import User

class MembersParserThread(threading.Thread):
    def __init__(self, chat):
        print(f"Creating chat {chat.id} parsing thread...")
        logging.debug(f"Creating chat {chat.id} parsing thread...")
        
        threading.Thread.__init__(self)
        
        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
    
    async def async_run(self):
        for phone in self.chat.phones:
            print(f'Try to recieve members from chat {self.chat.id}.')
            logging.debug(f'Try to recieve members from chat {self.chat.id}.')
            
            try:
                client = await phone.new_client(loop=self.loop)
                
                async for user in client.iter_participants(types.PeerChannel(channel_id=self.chat.internal_id)):
                    print(f'Chat {self.chat.id}. Received user \'{user.first_name}\'')
                    logging.debug(f'Chat {self.chat.id}. Received user \'{user.first_name}\'')
                    
                    try: 
                        print(f'Try to save member \'{user.first_name}\'')
                        logging.debug(f'Try to save member \'{user.first_name}\'')
                        
                        member = ApiProcessor().set('member', { 
                            'internalId': user.id,
                            'username': user.username,
                            'firstName': user.first_name,
                            'lastName': user.last_name,
                            'phone': user.phone,
                        })
                    except Exception as ex:
                        print(f'Member \'{user.first_name}\' exist. Try to get from API.')
                        logging.debug(f'Member \'{user.first_name}\' exist. Try to get from API.')
                        
                        members = ApiProcessor().get('member', { 'internalId': user.id })
                        if len(members) > 0:
                            print(f'Member \'{user.first_name}\' founded in API.')
                            logging.debug(f'Member \'{user.first_name}\' founded in API.')
                            
                            member = members[0]
                        else:
                            print(f"{bcolors.FAIL}Can\'t save chat {self.chat.id} member. Exception: {ex}.{bcolors.ENDC}")
                            logging.error(f"Can\'t save chat {self.chat.id} member. Exception: {ex}.")

                            raise Exception(f'Can\'t save member of chat {self.chat.id}')
                    
                    try:
                        print(f"Try to save chat-member: chat - {self.chat.id}, member - {member['id']}.")
                        logging.debug(f"Try to save chat-member: chat - {self.chat.id}, member - {member['id']}.")
                        
                        chat_member = ApiProcessor().set('chat-member', { 
                            'chat': { 'id': self.chat.id }, 
                            'member': { 'id': member['id'] } 
                        })
                    except Exception as ex:
                        print(f"Chat-member {member['id']} exist. Try to get from API.")
                        logging.debug(f"Chat-member {member['id']} exist. Try to get from API.")
                        
                        chat_members = ApiProcessor().get('chat-member', { 'chat': { 'id': self.chat.id }, 'member': { 'id': member['id'] } })
                        
                        if len(chat_members) > 0:
                            print(f"Chat-member {member['id']} founded in API.")
                            logging.debug(f"Chat-member {member['id']} founded in API.")
                            
                            chat_member = chat_members[0]
                        else:
                            print(f"{bcolors.FAIL}Can\'t save chat-member chat: {self.chat.id} member: {member['id']}. Exception: {ex}.{bcolors.ENDC}")
                            logging.error(f"Can\'t save chat-member chat: {self.chat.id} member: {member['id']}. Exception: {ex}.")

                            raise Exception(f'cannot create chat-member entity. Exception: {ex}')
                    
                    participant = user.participant
                    try:
                        print(f"Try to save chat-member-role: chat - {self.chat.id}, member - {member['id']}.")
                        logging.debug(f"Try to save chat-member-role: chat - {self.chat.id}, member - {member['id']}.")

                        if isinstance(participant, types.ChannelParticipantAdmin):
                            ApiProcessor().set('chat-member-role', {'member': {'id': chat_member['id']}, 'title': (participant.rank if participant.rank != None else 'Администратор'), 'code': 'admin'})
                        elif isinstance(participant, types.ChannelParticipantCreator):
                            ApiProcessor().set('chat-member-role', {'member': {'id': chat_member['id']}, 'title': (participant.rank if participant.rank != None else 'Создатель'), 'code': 'creator'})
                        else:
                            ApiProcessor().set('chat-member-role', {'member': {'id': chat_member['id']}, 'title': 'Участник', 'code': 'member'})
                    except Exception as ex:
                        print(f"{bcolors.FAIL}Can\'t save chat-member-role: chat - {self.chat.id}, member - {member['id']}, chat-member - {chat_member['id']}. Exception: {ex}.{bcolors.ENDC}")
                        logging.error(f"Can\'t save chat-member-role: chat - {self.chat.id}, member - {member['id']}, chat-member - {chat_member['id']}. Exception: {ex}.")
                    
                    # TODO: Здесь должна быть выкачка аватарок
            except Exception as ex:
                print(f"{bcolors.FAIL}Can\'t get chat {self.chat.id} participants using phone {phone.id}. Exception: {ex}.{bcolors.ENDC}")
                logging.error(f"Can\'t get chat {self.chat.id} participants using phone {phone.id}. Exception: {ex}.")
                
                await asyncio.sleep(random.randint(2, 5))
                
                continue
            else:
                break
        else:
            ApiProcessor().set('chat', { 'id': self.chat.id, 'isAvailable': False })
            
            raise Exception(f'Cannot get chat {self.chat.id} participants. Exit.')
        
    def run(self):
        asyncio.run(self.async_run())