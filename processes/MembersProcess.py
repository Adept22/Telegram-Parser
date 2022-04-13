import multiprocessing, asyncio, logging, telethon
import entities, exceptions
from utils import user_title

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from telethon import TelegramClient

class MembersProcess(multiprocessing.Process):
    def __init__(self, chat: 'entities.TypeChat'):
        multiprocessing.Process.__init__(self, name=f'MembersProcess-{chat.id}', daemon=True)
        
        self.media_path = f"./downloads/members"
        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
        
    async def get_member(self, client: 'TelegramClient', user: 'telethon.types.TypeUser') -> 'entities.TypeMember':
        member = entities.Member(internalId=user.id, username=user.username, firstName=user.first_name, lastName=user.last_name, phone=user.phone)

        await member.expand(client)

        return member.save()
        
    async def get_chat_member(self, participant: 'telethon.types.TypeChannelParticipant | telethon.types.TypeChatParticipant', member: 'entities.TypeMember') -> 'entities.TypeChatMember':
        chat_member = entities.ChatMember(chat=self.chat, member=member)

        await chat_member.expand(participant)

        return chat_member.save()
    
    async def get_chat_member_role(self, participant: 'telethon.types.TypeChannelParticipant | telethon.types.TypeChatParticipant', chat_member: 'entities.TypeChatMember') -> 'entities.TypeChatMemberRole':
        chat_member_role = entities.ChatMemberRole(member=chat_member)

        await chat_member_role.expand(participant)

        return chat_member_role.save()

    async def async_run(self):
        for phone in self.chat.phones:
            try:
                client = await phone.new_client(loop=self.loop)
            except exceptions.ClientNotAvailableError as ex:
                logging.error(f"Phone {phone.id} client not available.")
                logging.exception(ex)

                self.chat.remove_phone(phone)
                self.chat.save()
                
                continue

            try:
                tg_chat = await self.chat.get_tg_entity(client)
            except exceptions.ChatNotAvailableError as ex:
                logging.error(f"Can\'t get chat {self.chat.id} using phone {phone.id}.")
                logging.exception(ex)

                self.chat.isAvailable = False
                self.chat.save()

                break

            try:
                async for user in client.iter_participants(entity=tg_chat, aggressive=True):
                    user: 'telethon.types.TypeUser'

                    logging.debug(f"Chat {self.chat.title}. Received user '{user_title(user)}'")

                    if user.is_self:
                        continue

                    try:
                        member = await self.get_member(client, user)
                        chat_member = await self.get_chat_member(user.participant, member)
                        chat_member_role = await self.get_chat_member_role(user.participant, chat_member)
                    except Exception as ex:
                        logging.error(f"Can't save member '{member.internalId}' with role: chat - {self.chat.title}.")
                        logging.exception(ex)

                        continue
                    else:
                        logging.debug(f"Member {member.id} with role saved.")

                        try:
                            async for photo in client.iter_profile_photos(member.internalId):
                                photo: 'telethon.types.TypePhoto'

                                media = entities.MemberMedia(internalId=photo.id, member=member, date=photo.date.isoformat())

                                try:
                                    media.save()
                                except Exception as ex:
                                    logging.error(f"Can\'t save member {member.id} media. Exception: {ex}.")
                                    logging.exception(ex)
                                else:
                                    logging.info(f"Sucessfuly saved member {member.id} media.")

                                    try:
                                        await media.upload(client, photo, photo.sizes[-2])
                                    except Exception as ex:
                                        logging.error(f"Can\'t upload member {member.id} media.")
                                        logging.exception(ex)
                                    else:
                                        logging.info(f"Sucessfuly uploaded member {member.id} media.")
                        except Exception as ex:
                            logging.error(f"Can't get member {member.id} media using phone {phone.id}.")
                            logging.exception(ex)
            except (
                telethon.errors.ChannelInvalidError, 
                telethon.errors.ChannelPrivateError, 
                telethon.errors.ChatAdminRequiredError
            ) as ex:
                logging.error(f"Chat {self.chat.id} not available.")
                logging.exception(ex)
                
                self.chat.isAvailable = False
                self.chat.save()
            else:
                logging.info(f"Chat \'{self.chat.title}\' participants download success.")
                
            break
        else:
            logging.error(f"Cannot get chat {self.chat.id} participants.")
        
    def run(self):
        asyncio.run(self.async_run())