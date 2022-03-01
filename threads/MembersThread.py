import random
import threading
import asyncio
import logging
from errors.ClientNotAvailableError import ClientNotAvailableError
import globalvars
import os
from telethon import types, functions, errors, sync

from processors.ApiProcessor import ApiProcessor
from utils import user_title
from threads.KillableThread import KillableThread

class MembersThread(KillableThread):
    def __init__(self, chat):
        threading.Thread.__init__(self, name=f'MembersThread-{chat.id}')
        self.daemon = True
        
        self.media_path = f"./downloads/members"
        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
        
    def get_member(self, user, full_user):
        new_member = {
            'internalId': user.id,
            'username': user.username,
            'firstName': user.first_name,
            'lastName': user.last_name,
            'phone': user.phone,
            'about': full_user.about
        }
        
        members = ApiProcessor().get('telegram/member', { 'internalId': new_member['internalId'] })
        
        if len(members) > 0:
            if members[0].get('id') != None:
                new_member['id'] = members[0]['id']
        
        return new_member
        
    def get_chat_member(self, member):
        new_chat_member = {
            'chat': { 'id': self.chat.id }, 
            'member': member
        }
        
        if new_chat_member['member'].get('id') != None:
            chat_members = ApiProcessor().get('telegram/chat-member', new_chat_member)
            
            if len(chat_members) > 0:
                if chat_members[0].get('id') != None:
                    new_chat_member['id'] = chat_members[0]['id']
        
        return new_chat_member
    
    def get_chat_member_role(self, participant, chat_member):
        new_chat_member_role = { 'member': chat_member }
        
        if isinstance(participant, types.ChannelParticipantAdmin):
            new_chat_member_role['title'] = (participant.rank if participant.rank != None else "Администратор")
            new_chat_member_role['code'] = "admin"
        elif isinstance(participant, types.ChannelParticipantCreator):
            new_chat_member_role['title'] = (participant.rank if participant.rank != None else "Создатель")
            new_chat_member_role['code'] = "creator"
        else:
            new_chat_member_role['title'] = "Участник"
            new_chat_member_role['code'] = "member"
        
        if new_chat_member_role['member'].get('id') != None:
            chat_member_roles = ApiProcessor().get('telegram/chat-member-role', new_chat_member_role)
            
            if len(chat_member_roles) > 0:
                if chat_member_roles[0].get('id') != None:
                    new_chat_member_role['id'] = chat_member_roles[0]['id']
                    
        return new_chat_member_role

    async def get_entity(self, client):
        try:
            return await client.get_entity(entity=types.PeerChannel(channel_id=self.chat.internal_id))
        except ValueError:
            return await client.get_entity(entity=types.PeerChat(chat_id=self.chat.internal_id))
    
    async def async_run(self):
        for phone in self.chat.phones:
            try:
                client:sync.TelegramClient = await phone.new_client(loop=self.loop)

                entity = await self.get_entity(client)

                async for user in client.iter_participants(entity=entity):
                    logging.debug(f"Chat {self.chat.title}. Received user '{user_title(user)}'")
                    
                    if user.id in globalvars.phones_tg_ids:
                        logging.debug(f"Chat {self.chat.id}. User '{user.first_name}' is our phone. Continue.")
                        
                        continue

                    full_user = await client(functions.users.GetFullUserRequest(id=user.id))

                    member = self.get_member(user, full_user)
                    chat_member = self.get_chat_member(member)
                    chat_member_role = self.get_chat_member_role(user.participant, chat_member)
                    
                    try:
                        chat_member_role = ApiProcessor().set('telegram/chat-member-role', chat_member_role) 
                    except Exception as ex:
                        logging.error(f"Can't save member '{user.first_name}' with role: chat - {self.chat.title}. Exception: {ex}.")

                        continue
                    else:
                        logging.debug(f"Member '{user_title(user)}' with role saved.")

                        member = chat_member_role['member']['member']

                        try:
                            async for photo in client.iter_profile_photos(user.id):
                                new_media = { 'internalId': photo.id }

                                medias = ApiProcessor().get('telegram/member-media', new_media)

                                if len(medias) > 0:
                                    new_media = medias[0]
                                
                                    if 'path' in new_media and new_media['path'] != None:
                                        logging.debug(f"Member {member['id']} media {new_media['id']} exist on server. Continue.")

                                        await asyncio.sleep(1)

                                        continue

                                def progress_callback(current, total):
                                    logging.debug(f"Member {member['id']} media downloaded {current} out of {total} bytes: {current / total:.2%}")

                                try:
                                    path = await client.download_media(
                                        message=photo,
                                        file=self.media_path + f"/{member['id']}/{photo.id}",
                                        thumb=photo.sizes[-2],
                                        progress_callback=progress_callback
                                    )

                                    if path != None:
                                        new_media = { 
                                            **new_media,
                                            'member': {"id": member['id']}, 
                                            'internalId': photo.id,
                                            'createdAt': photo.date.isoformat(),
                                        }
                                            
                                        new_media = ApiProcessor().set('telegram/member-media', new_media)

                                        try:
                                            ApiProcessor().upload('telegram/member-media', new_media, path)
                                        except Exception as ex:
                                            logging.error(f"Can\'t upload member {member['id']} media. Exception: {ex}.")
                                        else:
                                            logging.info(f"Sucessfuly uploaded member {member['id']} media.")

                                        try:
                                            os.remove(path)
                                        except:
                                            pass
                                except Exception as ex:
                                    logging.error(f"Can\'t save member {member['id']} media. Exception: {ex}.")
                                else:
                                    logging.info(f"Sucessfuly saved member {member['id']} media.")
                        except Exception as ex:
                            logging.error(f"Can't get member {member['id']} media using phone {phone.id}. Exception: {ex}.")
            except (
                errors.ChannelInvalidError,
                errors.ChannelPrivateError,
                errors.ChatAdminRequiredError
            ) as ex:
                logging.error(f"Chat {self.chat.id} not available. Exception: {ex}.")
                
                self.chat.is_available = False
            except ClientNotAvailableError as ex:
                logging.error(f"Phone {phone.id} not available for chat {self.chat.id}. Exception: {ex}.")

                self.chat.remove_phone(phone)
            except Exception as ex:
                logging.error(f"Can\'t get chat {self.chat.title} participants using phone {phone.number}. Exception: {ex}.")
                
                await asyncio.sleep(random.randint(2, 5))
                
                continue
            else:
                logging.info(f"Chat \'{self.chat.title}\' participants download success.")
                
                break
        else:
            logging.error(f"Cannot get chat {self.chat.id} participants.")
        
    def run(self):
        self.chat.init_event.wait()
        
        asyncio.run(self.async_run())