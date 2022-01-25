import random
import threading
import asyncio
import logging
from sys import stdout
from telethon import types
import re
import os.path

from processors.ApiProcessor import ApiProcessor
from utils import profile_media_process, bcolors, user_title, formated_date

LOGFILE = 'log/dev.log'
logger = logging.getLogger("base_logger")
logger.setLevel(logging.INFO)

# create a console handler
print_format = logging.Formatter('%(threadName)-8s %(message)s')
console_handler = logging.StreamHandler(stdout)
console_handler.setFormatter(print_format)

# create a log file handler
log_format = logging.Formatter('[%(asctime)s] %(levelname)-8s %(name)-12s %(message)s')
file_handler = logging.FileHandler(LOGFILE)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(log_format)

#Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)


class MembersParserThread(threading.Thread):
    def __init__(self, chat):
        threading.Thread.__init__(self, name=f'MembersParserThread-{chat.id}')
        
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
            logger.debug(f'Member \'{user.first_name}\' exists in API.')
            
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
    
    async def async_run(self):
        for phone in self.chat.phones:
            logger.info(f'{bcolors.OKGREEN} Recieving members from chat {self.chat.title}.')
            
            try:
                client = await phone.new_client(loop=self.loop)

                async for user in client.iter_participants(entity=types.PeerChannel(channel_id=self.chat.internal_id)):
                    logger.debug(f'Chat {self.chat.title}. Received user \'{user_title(user)}\'')
                    
                    chat_member_role = self.get_chat_member_role(user.participant, self.get_chat_member(self.get_member(user)))
                    
                    try:
                        chat_member_role = ApiProcessor().set('chat-member-role', chat_member_role) 
                    except Exception as ex:
                        logger.error(f"{bcolors.FAIL} Can\'t save member \'{user.first_name}\' with role: chat - {self.chat.title}. Exception: {ex}.")

                        continue
                    
                    logger.debug(f"Member \'{user_title(user)}\' with role saved.")

                    member = chat_member_role['member']['member']

                    photos = await client.get_profile_photos(entity=types.PeerUser(user_id=user.id))
                    
                    for photo in photos:
                        saved_photo = { 'internalId': photo.id }

                        saved_photos = ApiProcessor().get('member-media', saved_photo)

                        if len(saved_photos) > 0:
                            saved_photo = saved_photos[0]

                            if os.path.exists(saved_photo['path']):
                                logging.debug(f'Chat {member["id"]}. Member-media {saved_photo["id"]} exist. Continue.')
                            
                                await asyncio.sleep(1)
                                continue

                        try:
                            path_folder = f'./uploads/member-media/{member["id"]}'

                            path_to_file = await client.download_media(
                                message=photo,
                                file=f'{path_folder}/{photo.id}',
                                # TODO: здесь надо проверить как обрабатываются видео
                                thumb=photo.sizes[-2]
                            )

                            if path_to_file != None:
                                new_photo = { 
                                    'id': saved_photo.get('id'),
                                    'member': member, 
                                    'internalId': photo.id,
                                    'createdAt': formated_date(photo.date),
                                    'path': f'{path_folder}/{re.split("/", path_to_file)[-1]}'
                                }

                                if 'id' in saved_photo:
                                    new_photo['id'] = saved_photo['id']
                                    
                                ApiProcessor().set('member-media', new_photo)

                        except Exception as ex:
                            logging.error(f"{bcolors.FAIL} Can\'t save member {member['id']} media. Exception: {ex}.")
                        else:
                            logging.info(f"{bcolors.OKGREEN} Sucessfuly saved member {member['id']} media!")
            except Exception as ex:
                # logger.error(f"{bcolors.FAIL} Can\'t get chat {self.chat.id} participants using phone {phone.id}. Exception: {ex}.")
                logger.error(f"{bcolors.FAIL} Can\'t get chat {self.chat.title} participants using phone {phone.number}. Exception: {ex}.")
                
                await asyncio.sleep(random.randint(2, 5))
                
                continue
            else:
                # logger.info(f"{bcolors.OKGREEN} Chat {self.chat.id} participants download success. Exit code 0.")
                logger.info(f"{bcolors.OKGREEN} 🏁 Chat \'{self.chat.title}\' participants download success. Exit code 0 🏁")
                
                break
        else:
            ApiProcessor().set('chat', { 'id': self.chat.id, 'isAvailable': False })
            
            # raise Exception(f'Cannot get chat {self.chat.id} participants. Exit code 1.')
            raise Exception(f'{bcolors.FAIL} Cannot get chat {self.chat.title} participants. Exit code 1.')
        
    def run(self):
        asyncio.run(self.async_run())
