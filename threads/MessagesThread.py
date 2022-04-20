import re
import threading, typing, asyncio, logging, telethon
import requests
from requests import request
import entities, threads, exceptions, services

if typing.TYPE_CHECKING:
    from telethon import TelegramClient

async def _messages_thread(loop, chat: 'entities.TypeChat'):
    async def get_member(client: 'TelegramClient', user: 'telethon.types.TypePeer') -> 'entities.TypeMember':
        member = entities.Member(internalId=user.user_id)

        await member.expand(client)

        return member.save()
        
    async def get_chat_member(participant, member):
        chat_member = entities.ChatMember(chat=chat, member=member)

        await chat_member.expand(participant)

        return chat_member.save()
    
    async def get_chat_member_role(participant, chat_member):
        chat_member_role = entities.ChatMemberRole(member=chat_member)

        await chat_member_role.expand(participant)

        return chat_member_role.save()

    async def get_message_participant(client: 'TelegramClient', input_chat, input_sender: 'telethon.types.TypeInputPeer'):
        peer = telethon.utils.get_peer(chat.internalId or 0)

        try:
            if isinstance(peer, telethon.types.PeerChannel):
                participant: 'telethon.types.TypeChannelParticipant' = await client(
                    telethon.tl.functions.channels.GetParticipantRequest(input_chat, input_sender)
                )
                return participant.participant
            elif isinstance(peer, telethon.types.PeerChat):
                chat_full: 'telethon.types.TypeChatFull' = await client(telethon.tl.functions.messages.GetFullChatRequest(chat.internalId))
                participants = [p.participant for p in chat_full.participants if p.user_id == input_sender.user_id] \
                    if chat_full.participants.participants else []
                return participants[0] if len(participants) > 0 else None
        except telethon.errors.RPCError as ex:
            logging.warning(f"Can't get participant data for {input_sender.user_id} with chat {chat.internalId}. Exception: {ex}.")

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
    
    def handle_links(message):
        for link in re.finditer(r't\.me\/(?:joinchat\/|\+)?[-_.a-zA-Z0-9]+', message):
            link = f"https://{link.group()}"

            try:
                services.ApiService().set(f'telegram/chat', { "link": link, "isAvailable": True })
            except Exception as ex:
                continue

    async def handle_message(chat_phone: 'entities.TypePhone', client: 'TelegramClient', tg_message: 'telethon.types.TypeMessage'):
        logging.debug(f"Chat {chat.id}. Receive message {tg_message.id}.")
        
        try:
            fwd_from_id, fwd_from_name = get_fwd(tg_message.fwd_from)

            if isinstance(tg_message.from_id, telethon.types.PeerUser):
                member = await get_member(client, tg_message.from_id)
                participant = await get_message_participant(client, tg_message.input_chat, tg_message.input_sender)
                chat_member = await get_chat_member(participant, member)
                chat_member_role = await get_chat_member_role(participant, chat_member)
            else:
                chat_member = None

            if tg_message.reply_to != None:
                reply_to = entities.Message(internalId=tg_message.reply_to.reply_to_msg_id, chat=chat)
                reply_to.save()
            else:
                reply_to = None

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
            logging.error(f"Can't save chat {chat.id} message {tg_message.id}. Exception {ex}")
        else:
            logging.debug(f"Message {message.id} saved.")
            
            if tg_message.media != None:
                thread = threading.Thread(target=threads.message_media_thread, args=(chat_phone, message, tg_message))
                thread.start()

            return message

        return None

    for chat_phone in chat.phones:
        chat_phone: 'entities.TypeChatPhone'

        logging.info(f"Recieving messages from chat {chat.id}.")

        try:
            client: 'TelegramClient' = await chat_phone.phone.new_client(loop=loop)
        except exceptions.ClientNotAvailableError as ex:
            logging.critical(f"Phone {chat_phone.id} client not available.")

            chat_phone.isUsing = False
            chat_phone.save()
            
            chat.phones.remove(chat_phone)
            
            continue

        async def handle_event(event):
            if not isinstance(tg_message, telethon.types.Message):
                return

            handle_links(event.message.message)
            
            # await handle_message(chat_phone.phone, client, event.message)

        client.add_event_handler(handle_event, telethon.events.NewMessage(chats=chat.internalId, incoming=True))

        while True:
            try:
                async for tg_message in client.iter_messages(entity=chat.internalId, max_id=0):
                    tg_message: 'telethon.types.TypeMessage'
        
                    if not isinstance(tg_message, telethon.types.Message):
                        continue

                    handle_links(tg_message.message)
            
                    # await handle_message(chat_phone, client, tg_message)
                else:
                    logging.info(f"Chat {chat.id} messages download success.")
            except telethon.errors.common.MultiError as ex:
                await asyncio.sleep(30)
            except telethon.errors.FloodWaitError as ex:
                logging.error(f"Telegram messages request of chat {chat.id} must wait {ex.seconds} seconds.")

                await asyncio.sleep(ex.seconds)
            except (KeyError, ValueError, telethon.errors.RPCError) as ex:
                logging.critical(f"Chat {chat.id} not available. Exception {ex}")

                chat.isAvailable = False
                chat.save()

                break
            else:
                logging.info(f"Chat \'{chat.id}\' messages download success.")
    else:
        logging.error(f"Chat {chat.id} messages download failed.")

async def messages_thread(chat: 'entities.TypeChat'):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    asyncio.run(_messages_thread(loop, chat))
