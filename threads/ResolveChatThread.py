import asyncio, logging, telethon
import entities, services, exceptions

async def _resolve_chat_thread(chat: 'entities.TypeChat', chat_phone: 'entities.TypeChatPhone'):
    async with services.ChatPhoneClient(chat_phone) as client:
        while True:
            try:
                """
                Чекаем есть ли вообще что-то по ссылке-приглашению прежде 
                чем делать тяжелый запрос на получение сущности
                """
                if chat.hash:
                    await client(telethon.functions.messages.CheckChatInviteRequest(chat.hash))

                tg_chat = await client.get_entity(chat.link)
            except telethon.errors.FloodWaitError as ex:
                logging.warning(f"Chat resolve must wait {ex.seconds}.")

                await asyncio.sleep(ex.seconds)

                continue
            except (TypeError, KeyError, ValueError, telethon.errors.RPCError) as ex:
                raise exceptions.ChatNotAvailableError(str(ex))
            else:
                return tg_chat

def resolve_chat_thread(chat: 'entities.TypeChat', chat_phone: 'entities.TypeChatPhone'):
    asyncio.set_event_loop(asyncio.new_event_loop())

    return asyncio.run(_resolve_chat_thread(chat, chat_phone))