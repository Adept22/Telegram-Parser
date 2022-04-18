import multiprocessing, setproctitle, asyncio, typing, logging, telethon
import entities, exceptions, helpers

if typing.TYPE_CHECKING:
    from telethon import TelegramClient
    from telethon.events.chataction import ChatAction

class MembersProcess(multiprocessing.Process):
    def __init__(self, chat: 'entities.TypeChat'):
        multiprocessing.Process.__init__(self, name=f'MembersProcess-{chat.id}', daemon=True)

        setproctitle.setproctitle(self.name)
        
        self.media_path = f"./downloads/members"
        self.chat: 'entities.TypeChat' = chat
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

    async def handle_member(self, client, user):
        logging.debug(f"Chat {self.chat.title}. Received user '{helpers.user_title(user)}'")

        if user.is_self:
            return

        try:
            member = await self.get_member(client, user)
            chat_member = await self.get_chat_member(user.participant, member)
            chat_member_role = await self.get_chat_member_role(user.participant, chat_member)
        except exceptions.RequestException as ex:
            logging.error(f"Can't save user '{user.id}'. Exception {ex}")

            return
        else:
            logging.debug(f"Member {member.id} with role saved.")

            try:
                async for photo in client.iter_profile_photos(member.internalId):
                    photo: 'telethon.types.TypePhoto'

                    media = entities.MemberMedia(internalId=photo.id, member=member, date=photo.date.isoformat())

                    try:
                        media.save()
                    except exceptions.RequestException as ex:
                        logging.error(f"Can\'t save member {member.id} media. Exception: {ex}.")
                    else:
                        logging.info(f"Sucessfuly saved member {member.id} media.")

                        size = photo.sizes[-2]

                        try:
                            await media.upload(
                                client, 
                                telethon.types.InputPhotoFileLocation(
                                    id=photo.id,
                                    access_hash=photo.access_hash,
                                    file_reference=photo.file_reference,
                                    thumb_size=size.type
                                ), 
                                size.size
                            )
                        except exceptions.RequestException as ex:
                            logging.error(f"Can\'t upload member {member.id} media. Exception: {ex}.")
                        else:
                            logging.info(f"Sucessfuly uploaded member {member.id} media.")
            except telethon.errors.RPCError as ex:
                logging.error(f"Can't get member {member.id} media.")

    async def async_run(self):
        for phone in self.chat.phones:
            phone: 'entities.TypePhone'

            try:
                client = await phone.new_client(loop=self.loop)
            except exceptions.ClientNotAvailableError as ex:
                logging.critical(f"Phone {phone.id} client not available.")

                self.chat.phones.remove(phone)
                self.chat.save()
                
                continue

            async def handle_event(event: 'ChatAction.Event'):
                if event.user_added or event.user_joined:
                    async for user in event.get_users():
                        await self.handle_member(client, user)

            client.add_event_handler(handle_event, telethon.events.chataction.ChatAction(chats=self.chat.internalId))
            
            while True:
                try:
                    async for user in client.iter_participants(entity=self.chat.internalId, aggressive=True):
                        user: 'telethon.types.TypeUser'

                        await self.handle_member(client, user)
                    else:
                        logging.info(f"Chat \'{self.chat.id}\' participants download success.")
                except telethon.errors.FloodWaitError as ex:
                    logging.error(f"Telegram members request of chat {self.chat.id} must wait {ex.seconds} seconds.")

                    await asyncio.wait(ex.seconds)
                except telethon.errors.RPCError as ex:
                    logging.critical(f"Chat {self.chat.id} not available. Exception: {ex}")
                    
                    self.chat.isAvailable = False
                    self.chat.save()

                    break
        else:
            logging.error(f"Chat {self.chat.id} participants download failed.")
        
    def run(self):
        asyncio.run(self.async_run())