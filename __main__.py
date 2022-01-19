import os
import asyncio
import logging
from sys import stdout
# from logger import Logger
from autobahn.wamp.types import SubscribeOptions
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner

from models.Chat import Chat
from models.Phone import Phone
from processors.ApiProcessor import ApiProcessor
from core.ChatsManager import ChatsManager
from core.PhonesManager import PhonesManager

from autobahn.asyncio.component import Component

# fh = logging.FileHandler(filename='log/dev.log', mode='a')
# fh.setLevel(logging.INFO)

# sh = logging.StreamHandler(sys.stdout)
# sh.setLevel(logging.DEBUG)

# logging.basicConfig(
#     format="%(threadName)-8s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s",
#     datefmt='%H:%M:%S',
#     handlers=[fh, sh]
# )

LOGFILE = 'log/dev.log'
logger = logging.getLogger("base_logger")
logger.setLevel(logging.INFO)

# create a console handler
print_format = logging.Formatter('%(threadName)-8s %(message)s')
console_handler = logging.StreamHandler(stdout)
console_handler.setFormatter(print_format)

# create a log file handler
log_format = logging.Formatter('[%(asctime)s] %(levelname)-8s %(name)-12s %(message)s')
file_handler = logging.FileHandler(LOGFILE)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(log_format)

#Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

async def update_chat(chat):
    if chat['id'] in ChatsManager():
        logger.info(f"Chat {chat['id']} founded in manager. Updating...")
        
        chat = ChatsManager()[chat['id']].from_dict(chat)
        
        await chat.init()
            
        if not chat.is_available:
            logger.warning(f"Chat {chat.id} actually not available.")
            
            del ChatsManager()[chat.id]
    else:
        chat = await Chat(chat).init()
        
        if chat.is_available:
            ChatsManager()[chat.id] = chat

async def update_chats():
    logger.debug("Getting chats...")
    
    chats = ApiProcessor().get('chat', { "isAvailable": True })
    
    for chat in chats:
        await update_chat(chat)
        
    logger.debug(f"Received {len(chats)} chats.")
    
async def update_phone(phone):
    logger.debug("")
    
    if phone['id'] in PhonesManager():
        phone = PhonesManager()[phone['id']].from_dict(phone)
        
        logger.info(f"Updating phone {phone.id}.")
        
        await phone.init()
    else:
        phone = await Phone(phone).init()
        
    PhonesManager()[phone.id] = phone

async def update_phones():
    logger.debug("Getting phones...")
    
    phones = ApiProcessor().get('phone', { "isBanned": False })
    
    for phone in phones:
        await update_phone(phone)
        
    logger.debug(f"Received {len(phones)} phones.")

class Component(ApplicationSession):
    async def onJoin(self, details):
        logger.info(f"session on_join: {details}")
        
        await update_phones()
        await update_chats()

        async def on_event(event, details=None):
            logger.debug(f"Got event, publication ID {details.publication}, publisher {details.publisher}: {event}")
            
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
