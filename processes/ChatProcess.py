import asyncio, logging, telethon, concurrent.futures
import entities, exceptions, helpers, threads
import services

async def _chat_process(chat: 'entities.TypeChat'):
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

    with concurrent.futures.ThreadPoolExecutor(thread_name_prefix=f"JoinChat-{chat.id}") as executor:
        fs = [executor.submit(threads.join_chat_thread, chat_phone) for chat_phone in chat_phones if not chat_phone.isUsing]

        def result_iterator():
            try:
                fs.reverse()
                while fs:
                    yield fs.pop().result()
            finally:
                for future in fs:
                    future.cancel()

        for result in result_iterator():
            if sum([1 for chat_phone in chat_phones if chat_phone.isUsing]) >= 3:
                break

        for future in fs:
            future.cancel()

    for chat_phone in (chat_phone for chat_phone in chat_phones if chat_phone.isUsing):
        async with services.ChatPhoneClient(chat_phone) as client:
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
    
    for chat_phone in (chat_phone for chat_phone in chat_phones if chat_phone.isUsing):
        """Appending using phones"""
        chat.phones.append(chat_phone)
        
    with concurrent.futures.ThreadPoolExecutor(thread_name_prefix="ChatExecutor-") as executor:
        # executor.submit(threads.chat_info_thread, chat)
        executor.submit(threads.members_thread, chat)
        executor.submit(threads.messages_thread, chat)

def chat_process(chat: 'entities.TypeChat'):
    asyncio.run(_chat_process(chat))
    