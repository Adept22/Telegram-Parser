from sys import stdout
import os
import asyncio
import logging
from autobahn.wamp.types import SubscribeOptions
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner

from models.Chat import Chat
from models.Phone import Phone
from processors.ApiProcessor import ApiProcessor
from core.ChatsManager import ChatsManager
from core.PhonesManager import PhonesManager

from autobahn.asyncio.component import Component

fh = logging.FileHandler(filename='log/dev.log', mode='a')
fh.setLevel(logging.INFO)

sh = logging.StreamHandler(stdout)
sh.setLevel(logging.DEBUG)

logging.basicConfig(
    format="%(threadName)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s",
    datefmt='%H:%M:%S',
    handlers=[fh, sh]
)

async def update_chat(chat):
    if chat['id'] in ChatsManager():
        logging.info(f"Chat {chat['id']} founded in manager. Updating...")
        
        chat = ChatsManager()[chat['id']].from_dict(chat)
        
        await chat.init()
            
        if not chat.is_available:
            logging.warning(f"Chat {chat.id} actually not available.")
            
            del ChatsManager()[chat.id]
    else:
        chat = await Chat(chat).init()
        
        if chat.is_available:
            ChatsManager()[chat.id] = chat

async def update_chats():
    logging.debug("Getting chats...")
    
    chats = ApiProcessor().get('chat')
    
    for chat in chats:
        await update_chat(chat)
        
    logging.debug(f"Received {len(chats)} chats.")
    
async def update_phone(phone):
    logging.debug("")
    
    if phone['id'] in PhonesManager():
        phone = PhonesManager()[phone['id']].from_dict(phone)
        
        logging.info(f"Updating phone {phone.id}.")
        
        await phone.init()
        
        if not await phone.client.is_user_authorized():
            logging.warning(f"Phone {phone.id} actually not authorized and must be removed.")
            
            del PhonesManager()[phone.id]
    else:
        phone = await Phone(phone).init()
        
        if await phone.client.is_user_authorized():
            logging.info(f"Phone {phone.id} now starts to use.")
            
            PhonesManager()[phone.id] = phone

async def update_phones():
    logging.debug("Getting phones...")
    
    phones = ApiProcessor().get('phone')
    
    for phone in phones:
        await update_phone(phone)
        
    logging.debug(f"Received {len(phones)} phones.")

class Component(ApplicationSession):
    async def onJoin(self, details):
        logging.info(f"session on_join: {details}")
        
        await update_phones()
        await update_chats()

        async def on_event(event, details=None):
            logging.debug(f"Got event, publication ID {details.publication}, publisher {details.publisher}: {event}")
            
            if event['_'] == 'TelegramPhone':
                await update_phone(event['entity'])
            elif event['_'] == 'TelegramChat':
                await update_chat(event['entity'])

        await self.subscribe(on_event, 'com.app.entity', options=SubscribeOptions(details_arg='details'))
    
    def onDisconnect(self):
        asyncio.get_event_loop().stop()

if __name__ == '__main__':
    runner = ApplicationRunner(os.environ['WEBSOCKET_URL'], os.environ['WEBSOCKET_REALM'])
    runner.run(Component)
