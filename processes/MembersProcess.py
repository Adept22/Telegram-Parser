import multiprocessing, asyncio, logging, telethon

from entity import Member, ChatMember, ChatMemberRole, MemberMedia
from utils import user_title

class MembersProcess(multiprocessing.Process):
    def __init__(self, chat):
        multiprocessing.Process.__init__(self, name=f'MembersProcess-{chat.id}', daemon=True)
        
        self.media_path = f"./downloads/members"
        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
        
    async def get_member(self, client, user):
        member = Member(**{
            'internalId': user.id,
            'username': user.username,
            'firstName': user.first_name,
            'lastName': user.last_name,
            'phone': user.phone
        })

        await member.expand(client)

        return member.save()
        
    async def get_chat_member(self, participant, member):
        chat_member = ChatMember(chat=self.chat, member=member)

        await chat_member.expand(participant)

        return chat_member.save()
    
    async def get_chat_member_role(self, participant, chat_member):
        chat_member_role = ChatMemberRole(member=chat_member)

        await chat_member_role.expand(participant)

        return chat_member_role.save()

    async def get_entity(self, client):
        try:
            return await client.get_entity(entity=telethon.types.PeerChannel(channel_id=self.chat.internal_id))
        except ValueError:
            return await client.get_entity(entity=telethon.types.PeerChat(chat_id=self.chat.internal_id))
    
    async def async_run(self):
        for phone in self.chat.phones:
            try:
                client: 'telethon.TelegramClient' = await phone.new_client(loop=self.loop)

                entity = await self.get_entity(client)

                async for user in client.iter_participants(entity=entity, aggressive=True):
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
                                try:
                                    media = MemberMedia(internalId=photo.id, member=member, date=photo.date.isoformat())
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
        asyncio.run(self.async_run())