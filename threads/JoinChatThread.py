import asyncio, logging, telethon
import entities, services

async def _join_chat_thread(loop, chat_phone: 'entities.TypeChatPhone'):
    chat = chat_phone.chat
    phone = chat_phone.phone

    # while True:
    async with services.ChatPhoneClient(chat_phone, loop=loop) as client:
        try:
            if chat.hash is None:
                updates = await client(telethon.functions.channels.JoinChannelRequest(chat.username))
                tg_chat: 'telethon.types.TypeChat' = updates.chats[0]
            else:
                try:
                    updates = await client(telethon.functions.messages.ImportChatInviteRequest(chat.hash))
                except telethon.errors.UserAlreadyParticipantError as ex:
                    invite = await client(telethon.functions.messages.CheckChatInviteRequest(chat.hash))
                    tg_chat = invite.chat if invite.chat else invite.channel
                else:
                    tg_chat = updates.chats[0]
        except telethon.errors.FloodWaitError as ex:
            logging.warning(f"Chat {chat.id} wiring for phone {phone.id} must wait {ex.seconds}.")

            # await asyncio.sleep(ex.seconds)

            # continue
        except(
            telethon.errors.ChannelsTooMuchError, 
            telethon.errors.SessionPasswordNeededError
        ) as ex:
            logging.error(f"Chat {chat.id} not available for phone {phone.id}. Exception {ex}")

            # chat_phone.isUsing = False
            # chat_phone.save()
        except (TypeError, KeyError, ValueError, telethon.errors.RPCError) as ex:
            logging.critical(f"Chat {chat.id} not available. Exception {ex}.")

            chat.isAvailable = False
            chat.save()
        else:
            logging.info(f"Phone {phone.id} succesfully wired with chat {chat.id}.")

            internal_id = telethon.utils.get_peer_id(tg_chat)

            if chat._internalId != internal_id:
                chat.internalId = internal_id

            if chat.title != tg_chat.title:
                chat.title = tg_chat.title

            if chat.date != tg_chat.date.isoformat():
                chat.date = tg_chat.date.isoformat()

            chat_phone.isUsing = True
            chat_phone.save()

            chat.phones.append(chat_phone)

def join_chat_thread(chat_phone: 'entities.TypeChatPhone'):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    with chat_phone.chat._join_lock:
        if len(chat_phone.chat.phones) >= 3:
            return

        asyncio.run(_join_chat_thread(loop, chat_phone))
