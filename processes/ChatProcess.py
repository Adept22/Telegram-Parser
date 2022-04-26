import asyncio, logging, telethon, concurrent.futures
import entities, exceptions, helpers, threads

async def _chat_process(chat: 'entities.TypeChat'):
    chat_phones = helpers.get_all('telegram/chat-phone', { "chat": { "id": chat.id }})
    
    logging.debug(f"Received {len(chat_phones)} chat phones of chat {chat.id}.")

    chat_phones = {
        chat_phone["id"]: entities.ChatPhone(
            chat_phone["id"], 
            chat, 
            entities.Phone(**chat_phone["phone"]), 
            chat_phone["isUsing"]
        ) for chat_phone in chat_phones
    }

    if sum([1 for id in chat_phones if chat_phones[id].isUsing]) < 3:
        fs = {}
        join_executor = concurrent.futures.ThreadPoolExecutor(len(chat_phones), f"JoinChat-{chat.id}")

        def _join(f):
            try:
                result: 'telethon.types.TypeChat | bool' = f.result()
            except exceptions.ChatNotAvailableError as ex:
                chat.isAvailable = False
                chat.save()

                join_executor.shutdown(False)
            except Exception as ex:
                logging.exception(ex)
            else:
                if isinstance(result, (telethon.types.Channel, telethon.types.Chat)):
                    chat_phones[fs[f]].isUsing = True
                    chat_phones[fs[f]].save()

                    chat.phones.append(chat_phones[fs[f]])

                    internal_id = telethon.utils.get_peer_id(result)

                    if chat._internalId != internal_id:
                        chat.internalId = internal_id
                        
                        try:
                            chat.save()
                        except exceptions.UniqueConstraintViolationError:
                            logging.critical(f"Chat with internal id {internal_id} exist.")

                            for chat_phone in chat_phones:
                                chat_phone.delete()

                            chat.delete()

                            return
                            
            if sum([1 for id in chat_phones if chat_phones[id].isUsing]) >= 3:
                join_executor.shutdown(False)

        for id in chat_phones:
            if not chat_phones[id].isUsing:
                f = join_executor.submit(threads.join_chat_thread, chat_phones[id])
                f.add_done_callback(_join)

                fs[f] = id
    
    for id in chat_phones:
        """Appending using phones"""
        if chat_phones[id].isUsing:
            chat.phones.append(chat_phones[id])
        else:
            del chat_phones[id]

    executor = concurrent.futures.ThreadPoolExecutor(thread_name_prefix=f"Chat-{chat.id}")
    # executor.submit(threads.chat_info_thread, chat)
    executor.submit(threads.members_thread, chat)
    executor.submit(threads.messages_thread, chat)

    while True:
        await asyncio.sleep(30)

        if not chat.isAvailable:
            executor.shutdown(False)

            return
        else:
            chat.update()

def chat_process(chat: 'dict'):
    asyncio.run(_chat_process(entities.Chat(**chat)))
    