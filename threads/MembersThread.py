import asyncio, typing, logging, telethon, multiprocessing
import entities, exceptions, services, processes

if typing.TYPE_CHECKING:
    from telethon import TelegramClient
    from telethon.events.chataction import ChatAction

async def _members_thread(chat: 'entities.TypeChat'):
    async def get_member(client: 'TelegramClient', user: 'telethon.types.TypeUser') -> 'entities.TypeMember':
        member = entities.Member(internalId=user.id, username=user.username, firstName=user.first_name, lastName=user.last_name, phone=user.phone)

        await member.expand(client)

        return member.save()
        
    async def get_chat_member(participant: 'telethon.types.TypeChannelParticipant | telethon.types.TypeChatParticipant', member: 'entities.TypeMember') -> 'entities.TypeChatMember':
        chat_member = entities.ChatMember(chat=chat, member=member)

        await chat_member.expand(participant)

        return chat_member.save()
    
    async def get_chat_member_role(participant: 'telethon.types.TypeChannelParticipant | telethon.types.TypeChatParticipant', chat_member: 'entities.TypeChatMember') -> 'entities.TypeChatMemberRole':
        chat_member_role = entities.ChatMemberRole(member=chat_member)

        await chat_member_role.expand(participant)

        return chat_member_role.save()

    async def handle_member(chat_phone, client, user):
        if user.is_self:
            return

        try:
            member = await get_member(client, user)
            chat_member = await get_chat_member(user.participant, member)
            chat_member_role = await get_chat_member_role(user.participant, chat_member)
        except exceptions.RequestException as ex:
            logging.error(f"Can't save user '{user.id}'. Exception {ex}")

            return
        else:
            logging.info(f"User {user.id} with role saved. Member {member.id}.")

            multiprocessing.Process(target=processes.member_media_process, args=(chat_phone, member, user)).start()

    for chat_phone in chat.phones:
        chat_phone: 'entities.TypeChatPhone'

        async with services.ChatPhoneClient(chat_phone) as client:
            async def handle_event(event: 'ChatAction.Event'):
                if event.user_added or event.user_joined or event.user_left or event.user_kicked:
                    async for user in event.get_users():
                        await handle_member(chat_phone, client, user)


            client.add_event_handler(handle_event, telethon.events.chataction.ChatAction(chats=chat.internalId))

            while True:
                try:
                    async for user in client.iter_participants(entity=chat.internalId, aggressive=True):
                        user: 'telethon.types.TypeUser'

                        await handle_member(chat_phone, client, user)
                except telethon.errors.common.MultiError as ex:
                    await asyncio.sleep(30)

                    continue
                except (
                    telethon.errors.ChatAdminRequiredError,
                    telethon.errors.ChannelPrivateError,
                ) as ex:
                    logging.critical(f"Can't download participants. Exception: {ex}")
                except telethon.errors.FloodWaitError as ex:
                    logging.warning(f"Members request must wait {ex.seconds} seconds.")

                    await asyncio.sleep(ex.seconds)

                    continue
                except (KeyError, ValueError, telethon.errors.RPCError) as ex:
                    logging.critical(f"Chat not available. Exception: {ex}")
                    
                    chat.isAvailable = False
                    chat.save()
                else:
                    logging.info(f"Participants download success.")
                    
                return
    else:
        logging.error(f"Participants download failed.")

def members_thread(chat: 'entities.TypeChat'):
    asyncio.run(_members_thread(chat))
