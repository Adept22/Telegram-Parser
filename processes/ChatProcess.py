import asyncio, logging, telethon, concurrent.futures, typing
import entities, exceptions, helpers, threads
import services

if typing.TYPE_CHECKING:
    from concurrent.futures import Future

async def _chat_process(chat: 'entities.TypeChat'):
    join_fs: 'dict[str, Future]' = {}
    join_executor = concurrent.futures.ThreadPoolExecutor(len(chat_phones), f"JoinChat-{chat.id}")

    main_fs: 'dict[str, Future]' = {}
    main_executor = concurrent.futures.ThreadPoolExecutor(2, f"Chat-{chat.id}")

    while True:
        chat_phones = helpers.get_all('telegram/chat-phone', {"chat": {"id": chat.id}})
        
        logging.debug(f"Received {len(chat_phones)} chat phones of chat {chat.id}.")

        chat_phones = {
            chat_phone["id"]: entities.ChatPhone(
                chat_phone["id"], 
                chat, 
                entities.Phone(**chat_phone["phone"]), 
                chat_phone["isUsing"]
            ) for chat_phone in chat_phones \
                if chat_phone["phone"]["isBanned"] == False and chat_phone["phone"]["isVerified"] == True
        }

        if chat._internalId == None:
            for id in chat_phones:
                try:
                    async with services.ChatPhoneClient(chat_phones[id]) as client:
                        try:
                            if chat.hash:
                                await client(telethon.functions.messages.CheckChatInviteRequest(chat.hash))

                            tg_chat = await client.get_entity(chat.link)
                        except telethon.errors.ChannelPrivateError as ex:
                            logging.warning(f"Chat is private. Exception: {ex}.")

                            continue
                        except telethon.errors.FloodWaitError as ex:
                            logging.warning(f"Chat resolve must wait {ex.seconds}.")

                            continue
                        except (TypeError, KeyError, ValueError, telethon.errors.RPCError) as ex:
                            chat.isAvailable = False
                            chat.save()
                                
                            return
                        else:
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
                            else:
                                break
                except exceptions.ClientNotAvailableError as ex:
                    logging.error(f"Client not available.")
                except telethon.errors.UserDeactivatedBanError as ex:
                    logging.error(f"Phone is banned.")
                    
                    chat_phones[id].phone.isBanned = True
                    chat_phones[id].phone.save()
                    chat_phones[id].delete()

        chat_phones = {id: chat_phones[id] for id in chat_phones if not chat_phones[id].phone.isBanned}
        

        if sum([1 for id in chat_phones if chat_phones[id].isUsing]) < 3:
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
                        chat_phones[join_fs[f]].isUsing = True
                        chat_phones[join_fs[f]].save()

                        chat.phones.append(chat_phones[join_fs[f]])
                                
                if sum([1 for id in chat_phones if chat_phones[id].isUsing]) >= 3:
                    join_executor.shutdown(False)

            for id in chat_phones:
                if not chat_phones[id].isUsing and id not in join_fs.values():
                    join_f = join_executor.submit(threads.join_chat_thread, chat_phones[id])
                    join_f.add_done_callback(_join)

                    join_fs[join_f] = id
        
        for id in chat_phones:
            """Appending using phones"""
            if chat_phones[id].isUsing:
                chat.phones.append(chat_phones[id])

        def _complete(f):
            del main_fs[f]

        if 'members' not in main_fs.values():
            members_f = main_executor.submit(threads.members_thread, chat)
            members_f.add_done_callback(_complete)
            main_fs[members_f] = 'members'

        if 'messages' not in main_fs:
            messages_f = main_executor.submit(threads.messages_thread, chat)
            messages_f.add_done_callback(_complete)
            main_fs[messages_f] = 'messages'

        if not chat.isAvailable:
            join_executor.shutdown(False)
            main_executor.shutdown(False)

            return
        else:
            await asyncio.sleep(30)

            chat.update()

def chat_process(chat: 'dict'):
    asyncio.set_event_loop(asyncio.new_event_loop())
    
    asyncio.run(_chat_process(entities.Chat(**chat)))
