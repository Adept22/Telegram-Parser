import asyncio, logging, telethon
import entities, services
import exceptions

async def _join_chat_thread(chat_phone: 'entities.TypeChatPhone'):
    chat = chat_phone.chat
    phone = chat_phone.phone

    async with services.ChatPhoneClient(chat_phone) as client:
        while True:
            try:
                if chat.hash is None:
                    await client(telethon.functions.channels.JoinChannelRequest(chat.username))
                else:
                    try:
                        await client(telethon.functions.messages.ImportChatInviteRequest(chat.hash))
                    except telethon.errors.UserAlreadyParticipantError as ex:
                        await client(telethon.functions.messages.CheckChatInviteRequest(chat.hash))
            except telethon.errors.FloodWaitError as ex:
                logging.warning(f"Chat wiring for phone {phone.id} must wait {ex.seconds}.")

                await asyncio.sleep(ex.seconds)

                continue
            except(
                telethon.errors.ChannelsTooMuchError, 
                telethon.errors.SessionPasswordNeededError
            ) as ex:
                logging.error(f"Chat not available for phone {phone.id}. Exception {ex}")

                return False
            except (TypeError, KeyError, ValueError, telethon.errors.RPCError) as ex:
                logging.critical(f"Chat not available. Exception {ex}.")
                
                raise exceptions.ChatNotAvailableError(str(ex))
            else:
                return True

def join_chat_thread(chat_phone: 'entities.TypeChatPhone'):
    return asyncio.run(_join_chat_thread(chat_phone))