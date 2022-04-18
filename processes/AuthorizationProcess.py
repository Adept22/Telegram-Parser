import multiprocessing, asyncio, setproctitle, logging, telethon, telethon.sessions
import globalvars, entities

class AuthorizationProcess(multiprocessing.Process):
    def __init__(self, phone: 'entities.TypePhone', manager):
        multiprocessing.Process.__init__(self, name=f'AuthorizationProcess-{phone.id}', daemon=True)

        setproctitle.setproctitle(self.name)
        
        self.phone = phone
        self.manager = manager
        
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
        
        self.client = telethon.TelegramClient(
            session=telethon.sessions.StringSession(self.phone.session), 
            api_id=globalvars.parser['api_id'], 
            api_hash=globalvars.parser['api_hash'], 
            loop=self.loop
        )
        
    async def get_internal_id(self) -> 'int | None':
        try:
            return getattr(await self.client.get_me(), "id")
        except:
            pass
        
        return None
        
    async def send_code(self):
        try:
            logging.debug(f"Try to send code for {self.phone.id}.")
            
            sent = await self.client.send_code_request(phone=self.phone.number)
            
            logging.debug(f"Code sended for {self.phone.id}.")
            
            self.phone.code_hash = sent.phone_code_hash
        except telethon.errors.rpcerrorlist.FloodWaitError as ex:
            logging.error(f"Flood exception for phone {self.phone.id}. Sleep {ex.seconds}.")
            
            await asyncio.sleep(ex.seconds)
            
            await self.send_code()

    async def async_run(self):
        if not self.client.is_connected():
            try:
                await self.client.connect()
            except OSError as ex:
                logging.critical(f"Unable to connect client of {self.phone.id}. Exception: {ex}")

                return

        while True:
            if not await self.client.is_user_authorized():
                if self.phone.code != None and self.phone.code_hash != None:
                    logging.debug(f"Phone {self.phone.id} automatic try to sing in with code {self.phone.code}.")
        
                    try:
                        await self.client.sign_in(self.phone.number, self.phone.code, phone_code_hash=self.phone.code_hash)
                    except telethon.errors.RPCError as ex:
                        logging.error(f"Cannot authentificate phone {self.phone.id} with code {self.phone.code}. Exception: {ex}")
                        
                        self.phone.isVerified = False
                        self.phone.code = None
                        self.phone.code_hash = None
                        self.phone.save()

                        continue
                    else:
                        break
                elif self.phone.code_hash == None:
                    try:
                        await self.send_code()
                    except telethon.errors.RPCError as ex:
                        logging.error(f"Unable to sent code for {self.phone.id}. Exception: {ex}")
                        
                        self.phone.session = None
                        self.phone.isBanned = True
                        self.phone.isVerified = False
                        self.phone.code = None
                        self.phone.code_hash = None
                        self.phone.is_authorized = False

                        self.phone.save()
                        
                        return
                else:
                    await asyncio.sleep(10)

                    continue
            else:
                break
        
        self.phone.session = self.client.session.save()
        self.phone.isVerified = True
        self.phone.code = None
        self.phone.code_hash = None
        self.phone.is_authorized = True
                
        internal_id = await self.get_internal_id()
        
        if internal_id != None and self.phone.internalId != internal_id:
            self.phone.internalId = internal_id

        self.phone.save()

        self.manager[self.phone.id] = self.phone

        logging.debug(f"Phone in manager {len(self.manager)}.")
        logging.debug(f"Phone {self.phone.id} actually authorized.")
        
    def run(self):
        asyncio.run(self.async_run())
