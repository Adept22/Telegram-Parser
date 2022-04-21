import multiprocessing, setproctitle, typing, asyncio, logging, telethon, telethon.sessions
import globalvars, entities

async def _phone_process(phone: 'entities.TypePhone'):
    client = telethon.TelegramClient(
        session=telethon.sessions.StringSession(phone.session), 
        api_id=globalvars.parser['api_id'], 
        api_hash=globalvars.parser['api_hash']
    )
        
    async def get_internal_id() -> 'int | None':
        try:
            return getattr(await client.get_me(), "id")
        except:
            pass
        
        return None
        
    async def send_code():
        try:
            logging.debug(f"Try to send code for {phone.id}.")
            
            sent = await client.send_code_request(phone=phone.number)
            
            logging.debug(f"Code sended for {phone.id}.")
            
            phone.code_hash = sent.phone_code_hash
        except telethon.errors.rpcerrorlist.FloodWaitError as ex:
            logging.warning(f"Flood exception for phone {phone.id}. Sleep {ex.seconds}.")
            
            await asyncio.sleep(ex.seconds)
            
            await send_code()

    if not client.is_connected():
        try:
            await client.connect()
        except OSError as ex:
            logging.critical(f"Unable to connect client of {phone.id}. Exception: {ex}")

            return

    while True:
        if not await client.is_user_authorized():
            if phone.code != None and phone.code_hash != None:
                logging.debug(f"Phone {phone.id} automatic try to sing in with code {phone.code}.")
    
                try:
                    await client.sign_in(phone.number, phone.code, phone_code_hash=phone.code_hash)
                except telethon.errors.RPCError as ex:
                    logging.error(f"Cannot authentificate phone {phone.id} with code {phone.code}. Exception: {ex}")
                    
                    phone.isVerified = False
                    phone.code = None
                    phone.code_hash = None
                    phone.save()

                    continue
                else:
                    break
            elif phone.code_hash == None:
                try:
                    await send_code()
                except telethon.errors.RPCError as ex:
                    logging.error(f"Unable to sent code for {phone.id}. Exception: {ex}")
                    
                    phone.session = None
                    phone.isBanned = True
                    phone.isVerified = False
                    phone.code = None
                    phone.code_hash = None
                    # phone.is_authorized = False
                    phone.save()
                    
                    return
            else:
                await asyncio.sleep(10)

                continue
        else:
            break
    
    phone.session = client.session.save()
    phone.isVerified = True
    phone.code = None
    phone.code_hash = None
            
    internal_id = await get_internal_id()
    
    if internal_id != None and phone.internalId != internal_id:
        phone.internalId = internal_id

    phone.save()

    logging.debug(f"Phone {phone.id} actually authorized.")


def phone_process(phone: 'entities.TypePhone'):
    asyncio.run(_phone_process(phone))
    