from sys import stdout
import os
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from autobahn.wamp.types import SubscribeOptions
from autobahn.asyncio.wamp import ApplicationSession
from core.ApplicationRunner import ApplicationRunner

from models.Chat import Chat
from models.Phone import Phone
from processors.ApiProcessor import ApiProcessor
from core.ChatsManager import ChatsManager
from core.PhonesManager import PhonesManager

from autobahn.asyncio.component import Component

async def update_chat(chat):
    if chat['isAvailable'] == False:
        if chat['id'] in ChatsManager():
            del ChatsManager()[chat['id']]
        
        return
    
    if chat['id'] in ChatsManager():
        logging.debug(f"Updating chat {chat['id']}.")
        
        chat = ChatsManager()[chat['id']].from_dict(chat)
    else:
        logging.debug(f"Setting up new chat {chat['id']}.")
        
        chat = Chat(chat)
        
        ChatsManager()[chat.id] = chat
        
    await chat.init()

async def update_chats():
    logging.debug("Getting chats...")
    
    chats = ApiProcessor().get('chat', { "isAvailable": True })
    
    for chat in chats:
        await update_chat(chat)
        
    logging.debug(f"Received {len(chats)} chats.")
    
async def update_phone(phone):
    if phone['isBanned'] == True:
        if phone['id'] in PhonesManager():
            del PhonesManager()[phone['id']]
        
        return
    
    if phone['id'] in PhonesManager():
        logging.debug(f"Updating phone {phone['id']}.")
        
        phone = PhonesManager()[phone['id']].from_dict(phone)
    else:
        logging.debug(f"Setting up new phone {phone['id']}.")
        
        phone = Phone(phone)
        
        PhonesManager()[phone.id] = phone
        
    await phone.init()

async def update_phones():
    logging.debug("Getting phones...")
    
    phones = ApiProcessor().get('phone', { "isBanned": False })
    
    for phone in phones:
        await update_phone(phone)
        
    logging.debug(f"Received {len(phones)} phones.")

class Component(ApplicationSession):
    async def onJoin(self, details):
        logging.info(f"session on_join: {details}")
        
        await update_phones()
        await update_chats()

        async def on_event(event):
            logging.debug(f"Got event on entity: {event['_']}")
            
            if event['_'] == 'TelegramPhone':
                await update_phone(event['entity'])
            elif event['_'] == 'TelegramChat':
                await update_chat(event['entity'])

        await self.subscribe(on_event, 'com.app.entity')
    
    def onDisconnect(self):
        asyncio.get_event_loop().stop()

if __name__ == '__main__':
    fh = RotatingFileHandler(filename='log/dev.log', maxBytes=1048576, backupCount=10)
    fh.setLevel(logging.INFO)

    sh = logging.StreamHandler(stdout)
    sh.setLevel(logging.DEBUG)

    logging.basicConfig(
        format="%(threadName)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s",
        datefmt='%H:%M:%S',
        handlers=[fh, sh],
        level=logging.DEBUG
    )
    
    runner = ApplicationRunner(os.environ['WEBSOCKET_URL'], os.environ['WEBSOCKET_REALM'])
    runner.run(Component)
