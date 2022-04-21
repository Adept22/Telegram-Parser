import asyncio, logging, telethon, concurrent.futures
import entities, exceptions, helpers, threads
import services

async def _chat_process(loop, chat: 'entities.TypeChat'):
    chat_phones = helpers.get_all('telegram/chat-phone', { "chat": { "id": chat.id }})
    
    logging.debug(f"Received {len(chat_phones)} of chat {chat.id}.")

    chat_phones = [
        entities.ChatPhone(
            chat_phone["id"], 
            chat, 
            entities.Phone(**chat_phone["phone"]), 
            chat_phone["isUsing"]
        ) for chat_phone in chat_phones
    ]
    
    using_phones = list(filter(lambda chat_phone: chat_phone.isUsing, chat_phones))

    for i, chat_phone in enumerate(using_phones):
        """Appending using phones"""
        chat.phones.append(chat_phone)

    if len(chat.phones) < 3 and len(chat_phones) > len(chat.phones):
        not_using_phones = list(filter(lambda chat_phone: not chat_phone.isUsing, chat_phones))

        for chat_phone in not_using_phones:
            chat_phone.join_chat()

    for chat_phone in chat.phones:
        async with services.ChatPhoneClient(chat_phone, loop=loop) as client:
            logging.debug(f"Try get TG entity of chat {chat.id} by chat phone {chat_phone.id}.")

            try:
                tg_chat = await helpers.get_entity(client, chat)
            except exceptions.ChatNotAvailableError as ex:
                logging.error(f"Can\'t get chat TG entity {chat.id} using chat phone {chat_phone.id}. Exception {ex}")

                chat_phone.isUsing = False
                chat_phone.save()

                continue

                # chat.isAvailable = False
                # chat.save()

                # return
            else:
                logging.debug(f"TG entity of chat {chat.id} received by chat phone {chat_phone.id}.")

                chat_phone.isUsing = True
                chat_phone.save()

                new_internal_id = telethon.utils.get_peer_id(tg_chat)
                
                if chat._internalId != new_internal_id:
                    logging.info(f"Chat {chat.id} internal id changed.")
                    
                    chat.internalId = new_internal_id

                    try:
                        chat.save()
                    except exceptions.UniqueConstraintViolationError:
                        logging.critical(f"Chat with internal id {new_internal_id} exist. Current chat {chat.id}")

                        for chat_phone in chat_phones:
                            chat_phone.delete()

                        chat.delete()

                        return

    for chat_phone in chat.phones:
        if not chat_phone.isUsing:
            chat.phones.remove(chat_phone)

    futures = []
    
    with concurrent.futures.ThreadPoolExecutor() as pool:
        # pool.submit(threads.chat_info_thread, chat)
        futures.append(pool.submit(threads.members_thread, chat))
        futures.append(pool.submit(threads.messages_thread, chat))
        
        concurrent.futures.wait(futures)

def chat_process(chat: 'entities.TypeChat'):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    asyncio.run(_chat_process(loop, chat))
    