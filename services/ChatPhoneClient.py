import telethon, telethon.sessions
import globalvars, entities, exceptions

class ChatPhoneClient(telethon.TelegramClient):
    def __init__(self, chat_phone: 'entities.TypeChatPhone', *args, **kwargs):
        self.chat_phone = chat_phone

        super(ChatPhoneClient, self).__init__(
            *args, 
            **kwargs, 
            connection_retries=-1,
            retry_delay=5, 
            session=telethon.sessions.StringSession(self.chat_phone.phone.session), 
            api_id=globalvars.parser['api_id'], 
            api_hash=globalvars.parser['api_hash']
        )

    async def start(self):
        if not self.is_connected():
            await self.connect()

        if await self.is_user_authorized() and await self.get_me() != None:
            return self
        else:
            raise exceptions.ClientNotAvailableError(f'Phone {self.chat_phone.id} not authorized')
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type != None:
            self.chat_phone.isUsing = False
            self.chat_phone.save()
            
        return await super().__aexit__(exc_type, exc_val, exc_tb)