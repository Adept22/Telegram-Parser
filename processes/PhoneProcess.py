import asyncio, logging, telethon, telethon.sessions, names
import globalvars, entities

async def _phone_process(phone: 'entities.TypePhone'):
    client = telethon.TelegramClient(
        connection_retries=-1,
        retry_delay=5, 
        session=telethon.sessions.StringSession(phone.session), 
        api_id=globalvars.parser['api_id'], 
        api_hash=globalvars.parser['api_hash']
    )
    
    if not client.is_connected():
        try:
            await client.connect()
        except OSError as ex:
            logging.critical(f"Unable to connect client. Exception: {ex}")

            return

    while True:
        if not await client.is_user_authorized():
            try:
                if phone.code != None and phone.code_hash != None:
                    try:
                        await client.sign_in(phone.number, phone.code, phone_code_hash=phone.code_hash)
                    except telethon.errors.PhoneNumberUnoccupiedError:
                        logging.warning(f"Phone first use telegram.")

                        phone.firstName = names.get_first_name()
                        phone.lastName = names.get_last_name()

                        await client.sign_up(phone.code, phone.firstName, phone.lastName, phone_code_hash=phone.code_hash)
                    except (
                        telethon.errors.PhoneCodeEmptyError, 
                        telethon.errors.PhoneCodeExpiredError, 
                        telethon.errors.PhoneCodeHashEmptyError, 
                        telethon.errors.PhoneCodeInvalidError
                    ) as ex:
                        logging.warning(f"Code invalid. Exception {ex}")

                        phone.code = None
                        phone.code_hash = None
                        phone.save()

                        continue

                    phone.session = client.session.save()
                    phone.isVerified = True
                    phone.code = None
                    phone.code_hash = None
                    
                    internal_id = getattr(await client.get_me(), "id")
                    
                    if internal_id != None and phone.internalId != internal_id:
                        phone.internalId = internal_id

                    phone.save()

                    break
                elif phone.code_hash == None:
                    try:
                        sent = await client.send_code_request(phone=phone.number, force_sms=True)
                        
                        phone.code_hash = sent.phone_code_hash

                        logging.info(f"Code sended.")
                    except telethon.errors.rpcerrorlist.FloodWaitError as ex:
                        logging.warning(f"Flood exception. Sleep {ex.seconds}.")
                        
                        await asyncio.sleep(ex.seconds)

                        continue
                else:
                    await asyncio.sleep(10)

                    phone.update()
            except telethon.errors.RPCError as ex:
                logging.error(f"Cannot authentificate. Exception: {ex}")
                
                phone.session = None
                phone.isBanned = True
                phone.isVerified = False
                phone.code = None
                phone.code_hash = None
                phone.save()

                return
        else:
            break

    logging.info(f"Authorized.")

def phone_process(phone: 'dict'):
    asyncio.set_event_loop(asyncio.new_event_loop())
    
    return asyncio.run(_phone_process(entities.Phone(**phone)))
    