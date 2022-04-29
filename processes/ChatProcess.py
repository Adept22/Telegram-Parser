import asyncio, logging, telethon, concurrent.futures
import typing
import entities, exceptions, helpers, threads, services

if typing.TYPE_CHECKING:
    from concurrent.futures import Future

async def _resolve_chat(chat: 'entities.TypeChat', chat_phone: 'entities.TypeChatPhone'):
    async with services.ChatPhoneClient(chat_phone) as client:
        while True:
            try:
                tg_chat = await client.get_entity(chat.link)
            except telethon.errors.FloodWaitError as ex:
                logging.warning(f"Chat resolve must wait {ex.seconds}.")

                await asyncio.sleep(ex.seconds)

                continue
            except (TypeError, KeyError, ValueError, telethon.errors.RPCError) as ex:
                raise exceptions.ChatNotAvailableError(str(ex))
            else:
                return tg_chat

def resolve_chat(chat: 'entities.TypeChat', chat_phone: 'entities.TypeChatPhone'):
    return asyncio.run(_resolve_chat(chat, chat_phone))

async def _chat_process(chat: 'entities.TypeChat'):
    chat_phones = helpers.get_all('telegram/chat-phone', { "chat": { "id": chat.id }})
    
    logging.debug(f"Received {len(chat_phones)} chat phones of chat {chat.id}.")

    chat_phones = {
        chat_phone["id"]: entities.ChatPhone(
            chat_phone["id"], 
            chat, 
            entities.Phone(**chat_phone["phone"]), 
            chat_phone["isUsing"]
        ) for chat_phone in chat_phones if chat_phone["phone"]["isBanned"] == False
    }

    resolve_executor = concurrent.futures.ThreadPoolExecutor()
    done, not_done = concurrent.futures.wait(
        {resolve_executor.submit(resolve_chat, chat, chat_phones[id]): id for id in chat_phones}, 
        return_when=concurrent.futures.FIRST_COMPLETED
    )

    try:
        tg_chat: 'telethon.types.TypeChat' = done.pop().result()
    except exceptions.ChatNotAvailableError as ex:
        logging.critical(f"Chat not available. Exception {ex}.")

        chat.isAvailable = False
        chat.save()

        resolve_executor.shutdown(False)

        return
    except Exception as ex:
        logging.exception(ex)
    else:
        if not isinstance(tg_chat, (telethon.types.Chat, telethon.types.Channel)):
            chat.delete()

            return

        internal_id = telethon.utils.get_peer_id(tg_chat)

        if chat._internalId != internal_id:
            chat.internalId = internal_id

        if chat.title != tg_chat.title:
            chat.title = tg_chat.title
            
        try:
            chat.save()
        except exceptions.UniqueConstraintViolationError:
            logging.critical(f"Chat with internal id {internal_id} exist.")

            chat.delete()
            
            return
            
    join_executor = concurrent.futures.ThreadPoolExecutor(len(chat_phones), f"JoinChat-{chat.id}")

    if sum([1 for id in chat_phones if chat_phones[id].isUsing]) < 3:
        fs = {}

        def _join(f):
            try:
                result: 'bool' = f.result()
            except exceptions.ChatNotAvailableError as ex:
                chat.isAvailable = False
                chat.save()

                join_executor.shutdown(False)

                return
            except Exception as ex:
                logging.exception(ex)
            else:
                if result:
                    chat_phones[fs[f]].isUsing = True
                    chat_phones[fs[f]].save()

                    chat.phones.append(chat_phones[fs[f]])
                            
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

    m_fs: 'list[Future]' = []

    executor = concurrent.futures.ThreadPoolExecutor(thread_name_prefix=f"Chat-{chat.id}")
    # executor.submit(threads.chat_info_thread, chat)
    m_fs.append(executor.submit(threads.members_thread, chat))
    m_fs.append(executor.submit(threads.messages_thread, chat))
    
    while True:
        await asyncio.sleep(30)

        if not chat.isAvailable or sum([1 for f in m_fs if f.done()]) == len(m_fs):
            join_executor.shutdown(False)
            executor.shutdown(False)

            return
        else:
            chat.update()

def chat_process(chat: 'dict'):
    asyncio.set_event_loop(asyncio.new_event_loop())
    
    asyncio.run(_chat_process(entities.Chat(**chat)))
    