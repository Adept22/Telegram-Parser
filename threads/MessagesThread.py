import re, threading, typing, asyncio, logging, telethon
import entities, threads, exceptions, services

if typing.TYPE_CHECKING:
    from telethon import TelegramClient

async def _messages_thread(chat: 'entities.TypeChat'):
    async def set_member(client: 'TelegramClient', user: 'telethon.types.TypeUser') -> 'entities.TypeMember':
        member = entities.Member(internalId=user.id, username=user.username, firstName=user.first_name, lastName=user.last_name, phone=user.phone)

        await member.expand(client)

        return member.save()
        
    async def set_chat_member(participant, member):
        chat_member = entities.ChatMember(chat=chat, member=member)

        await chat_member.expand(participant)

        return chat_member.save()
    
    async def set_chat_member_role(participant, chat_member):
        chat_member_role = entities.ChatMemberRole(member=chat_member)

        await chat_member_role.expand(participant)

        return chat_member_role.save()

    async def get_message_participant(client: 'TelegramClient', peer_id, user):
        try:
            if isinstance(peer_id, telethon.types.PeerChannel):
                participant: 'telethon.types.TypeChannelParticipant' = await client(
                    telethon.tl.functions.channels.GetParticipantRequest(peer_id, user)
                )
                return participant.participant
            elif isinstance(peer_id, telethon.types.PeerChat):
                chat_full: 'telethon.types.TypeChatFull' = await client(telethon.tl.functions.messages.GetFullChatRequest(peer_id))
                participants = [p.participant for p in chat_full.participants if p.user_id == user.id] \
                    if chat_full.participants.participants else []
                return participants[0] if len(participants) > 0 else None
        except telethon.errors.RPCError as ex:
            logging.warning(f"Can't get participant data for {user.id}. Exception: {ex}.")

        return None
    
    def get_fwd(fwd_from: 'telethon.types.TypeMessageFwdHeader | None'):
        if fwd_from != None:
            fwd_from_id = None
        
            if fwd_from.from_id != None:
                if isinstance(fwd_from.from_id, telethon.types.PeerChannel):
                    fwd_from_id = fwd_from.from_id.channel_id
                elif isinstance(fwd_from.from_id, telethon.types.PeerUser):
                    fwd_from_id = fwd_from.from_id.user_id
            
            return fwd_from_id, fwd_from.from_name if fwd_from.from_name != None else "Неизвестно"
            
        return None, None
    
    async def handle_links(client, message):
        for link in re.finditer(r't\.me\/(?:joinchat\/|\+)?[-_.a-zA-Z0-9]+', message):
            link = f"https://{link.group()}"

            try:
                tg_entity = await client.get_entity(link)
            except:
                pass
            else:
                try:
                    if isinstance(tg_entity, (telethon.types.Channel, telethon.types.Chat)):
                        services.ApiService().set(f'telegram/chat', { "link": link, "internalId": tg_entity.id, "title": tg_entity.title, "isAvailable": False })
                    elif isinstance(tg_entity, telethon.types.User):
                        member = await set_member(client, tg_entity)

                        threading.Thread(target=threads.member_media_thread, args=(chat_phone, member, tg_entity)).start()
                except Exception as ex:
                    logging.info(f"Can't create new entity from link {link}. Exception {ex}")
                else:
                    logging.info(f"New entity from link {link} created.")

    async def handle_message(chat_phone: 'entities.TypePhone', client: 'TelegramClient', tg_message: 'telethon.types.TypeMessage'):
        try:
            fwd_from_id, fwd_from_name = get_fwd(tg_message.fwd_from)

            if isinstance(tg_message.from_id, telethon.types.PeerUser):
                user = await client.get_entity(tg_message.from_id)

                try:
                    member = await set_member(client, user)
                except exceptions.RequestException as ex:
                    logging.error(f"Can't save user '{user.id}'. Exception {ex}")
                else:
                    logging.info(f"Message {user.id} member saved.")

                    threading.Thread(target=threads.member_media_thread, args=(chat_phone, member, user)).start()

                try:
                    participant = await get_message_participant(client, tg_message.peer_id, user)
                    chat_member = await set_chat_member(participant, member)
                    chat_member_role = await set_chat_member_role(participant, chat_member)
                except exceptions.RequestException as ex:
                    logging.error(f"Can't save user '{user.id}' chat-member or chat-member-role. Exception {ex}")
                else:
                    logging.info(f"User {user.id} chat-member and chat-member-role saved.")
            else:
                chat_member = None

            if tg_message.reply_to != None:
                reply_to = entities.Message(internalId=tg_message.reply_to.reply_to_msg_id, chat=chat)
                reply_to.save()
            else:
                reply_to = None

            if tg_message.replies != None:
                try:
                    replies: 'telethon.types.messages.Messages' = await client(telethon.tl.functions.messages.GetRepliesRequest(tg_message.peer_id, tg_message.id, 0, None, 0, 0, 0, 0, 0))

                    for reply in replies.messages:
                        await handle_message(chat_phone, client, reply)
                except Exception as ex:
                    logging.exception(ex)

            message = entities.Message(
                internalId=tg_message.id, 
                text=tg_message.message, 
                chat=chat, 
                member=chat_member,
                replyTo=reply_to, 
                isPinned=tg_message.pinned,     
                forwardedFromId=fwd_from_id, 
                forwardedFromName=fwd_from_name, 
                groupedId=tg_message.grouped_id, 
                date=tg_message.date.isoformat() 
            )
            message.save()
        except exceptions.RequestException as ex:
            logging.error(f"Can't save message {tg_message.id}. Exception {ex}")
        else:
            logging.info(f"Message {message.id} saved.")
            
            # if tg_message.media != None:
            #     threading.Thread(target=threads.message_media_thread, args=(chat_phone, message, tg_message)).start()

    messages = services.ApiService().get('telegram/message', { "chat": { "id": chat.id }, "_limit": 1, "_order": "ASC", "_sort": "internalId" })

    max_id = messages[0]["internalId"] if len(messages) > 0 else 0

    for chat_phone in chat.phones:
        chat_phone: 'entities.TypeChatPhone'

        async with services.ChatPhoneClient(chat_phone) as client:
            async def handle_event(event):
                if not isinstance(tg_message, telethon.types.Message):
                    return

                await handle_links(client, event.message.message)
                
                await handle_message(chat_phone, client, event.message)

            client.add_event_handler(handle_event, telethon.events.NewMessage(chats=chat.internalId, incoming=True))

            while True:
                try:
                    async for tg_message in client.iter_messages(chat.internalId, 1000, max_id=max_id):
                        tg_message: 'telethon.types.TypeMessage'

                        if not isinstance(tg_message, telethon.types.Message):
                            continue

                        await handle_links(client, tg_message.message)

                        await handle_message(chat_phone, client, tg_message)
                    else:
                        logging.info(f"Messages download success.")
                except telethon.errors.common.MultiError as ex:
                    await asyncio.sleep(30)

                    continue
                except telethon.errors.FloodWaitError as ex:
                    logging.warning(f"Messages request must wait {ex.seconds} seconds.")

                    await asyncio.sleep(ex.seconds)

                    continue
                except (KeyError, ValueError, telethon.errors.RPCError) as ex:
                    logging.critical(f"Chat not available. Exception {ex}")

                    chat.isAvailable = False
                    chat.save()

                return
    else:
        logging.error(f"Messages download failed.")

def messages_thread(chat: 'entities.TypeChat'):
    asyncio.set_event_loop(asyncio.new_event_loop())

    asyncio.run(_messages_thread(chat))
