import threading
import asyncio
import logging
import os
from telethon import types, functions, errors
from errors.UniqueConstraintViolationError import UniqueConstraintViolationError

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

        try:
            member = ApiProcessor().set('telegram/member', new_member)
        except UniqueConstraintViolationError:
            members = ApiProcessor().get('telegram/member', { 'internalId': new_member['internalId'] })
            
            new_member['id'] = members[0]['id']

            member = ApiProcessor().set('telegram/member', new_member)
        
        return member
        
    def get_chat_member(self, participant, member):
        new_chat_member = {
            'chat': { 'id': self.chat.id }, 
            'member': member
        }

        if isinstance(participant, types.ChannelParticipant):
            new_chat_member['date'] = participant.date.isoformat()

        try:
            chat_member = ApiProcessor().set('telegram/chat-member', new_chat_member)
        except UniqueConstraintViolationError:
            chat_members = ApiProcessor().get('telegram/chat-member', { 'chat': { 'id': self.chat.id }, 'member': { 'id': member['id'] }})
            
            new_chat_member['id'] = chat_members[0]['id']

            chat_member = ApiProcessor().set('telegram/chat-member', new_chat_member)
        
        return chat_member
    
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
        
        try:
            chat_member_role = ApiProcessor().set('telegram/chat-member-role', new_chat_member_role)
        except UniqueConstraintViolationError:
            chat_member_roles = ApiProcessor().get('telegram/chat-member-role', { 
                'member': {'id': chat_member['id'] }, 
                'title': new_chat_member_role['title'],
                'code': new_chat_member_role['code']
            })
            
            chat_member_role = chat_member_roles[0]
                    
        return chat_member_role

    async def get_entity(self, client):
        try:
            return await client.get_entity(entity=types.PeerChannel(channel_id=self.chat.internal_id))
        except ValueError:
            return await client.get_entity(entity=types.PeerChat(chat_id=self.chat.internal_id))
    
    async def async_run(self):
        for phone in self.chat.phones:
            try:
                client = await phone.new_client(loop=self.loop)

                entity = await self.get_entity(client)

                async for user in client.iter_participants(entity=entity):
                    logging.debug(f"Chat {self.chat.title}. Received user '{user_title(user)}'")

                    if user.is_self:
                        continue

                    full_user = await client(functions.users.GetFullUserRequest(id=user.id))

                    try:
                        member = self.get_member(user, full_user)
                        chat_member = self.get_chat_member(user.participant, member)
                        chat_member_role = self.get_chat_member_role(user.participant, chat_member)
                    except Exception as ex:
                        logging.error(f"Can't save member '{user.first_name}' with role: chat - {self.chat.title}.")
                        logging.exception(ex)

                        continue
                    else:
                        logging.debug(f"Member '{user_title(user)}' with role saved.")

                        try:
                            async for photo in client.iter_profile_photos(user.id):
                                new_media = {
                                    'member': { "id": member['id'] }, 
                                    'internalId': photo.id,
                                    'date': photo.date.isoformat()
                                }

                                try:
                                    try:
                                        new_media = ApiProcessor().set('telegram/member-media', new_media)
                                    except UniqueConstraintViolationError:
                                        medias = ApiProcessor().get('telegram/member-media', { 'internalId': photo.id })

                                        if 'path' in medias[0] and medias[0]['path'] != None:
                                            logging.debug(f"Member {member['id']} media {medias[0]['id']} exist on server. Continue.")

                                            await asyncio.sleep(1)

                                            continue
                                        else:
                                            new_media['id'] = medias[0]['id']

                                            new_media = ApiProcessor().set('telegram/member-media', new_media)
                                except Exception as ex:
                                    logging.error(f"Can\'t save member {member['id']} media. Exception: {ex}.")
                                    logging.exception(ex)
                                else:
                                    logging.info(f"Sucessfuly saved member {member['id']} media.")

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
                                        try:
                                            ApiProcessor().chunked('telegram/member-media', new_media, path)
                                        except Exception as ex:
                                            logging.error(f"Can\'t upload member {member['id']} media.")
                                            logging.exception(ex)
                                        else:
                                            logging.info(f"Sucessfuly uploaded member {member['id']} media.")

                                            try:
                                                os.remove(path)
                                            except:
                                                pass
                                except Exception as ex:
                                    logging.error(f"Can\'t download member {member['id']} media. Exception: {ex}.")
                                    logging.exception(ex)
                                else:
                                    logging.info(f"Sucessfuly download member {member['id']} media.")
                        except Exception as ex:
                            logging.error(f"Can't get member {member['id']} media using phone {phone.id}.")
                            logging.exception(ex)
            except (
                errors.ChannelInvalidError,
                errors.ChannelPrivateError,
                errors.ChatAdminRequiredError
            ) as ex:
                logging.error(f"Chat {self.chat.id} not available.")
                logging.exception(ex)
                
                self.chat.is_available = False
            except Exception as ex:
                logging.error(f"Can\'t get chat {self.chat.title} participants using phone {phone.id}.")
                logging.exception(ex)

                self.chat.remove_phone(phone)
                
                continue
            else:
                logging.info(f"Chat \'{self.chat.title}\' participants download success.")
                
                break
        else:
            logging.error(f"Cannot get chat {self.chat.id} participants.")
        
    def run(self):
        self.chat.init_event.wait()
        
        asyncio.run(self.async_run())