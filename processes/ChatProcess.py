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

    with concurrent.futures.ThreadPoolExecutor(50, f"JoinChat-{chat.id}") as executor:
        fs = {executor.submit(threads.join_chat_thread, chat_phones[id]): id for id in chat_phones if not chat_phones[id].isUsing}

        for f in concurrent.futures.as_completed(fs):
            try:
                result: 'telethon.types.TypeChat | bool' = f.result()
            except exceptions.ChatNotAvailableError as ex:
                for f in fs:
                    f.cancel()

                chat.isAvailable = False
                chat.save()

                return
            except Exception as ex:
                logging.exception(ex)
            else:
                if result == False:
                    chat_phones[fs[f]].isUsing = False
                else:
                    chat_phones[fs[f]].isUsing = True

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

                chat_phones[fs[f]].save()

                if sum([1 for id in chat_phones if chat_phones[id].isUsing]) >= 3:
                    break

        for f in fs:
            f.cancel()
    
    for id in chat_phones:
        """Appending using phones"""
        if chat_phones[id].isUsing:
            chat.phones.append(chat_phones[id])
        else:
            del chat_phones[id]
        
    with concurrent.futures.ThreadPoolExecutor(thread_name_prefix=f"Chat-{chat.id}") as executor:
        # executor.submit(threads.chat_info_thread, chat)
        executor.submit(threads.members_thread, chat)
        executor.submit(threads.messages_thread, chat)

def chat_process(chat: 'dict'):
    asyncio.run(_chat_process(entities.Chat(**chat)))
    