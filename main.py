import os
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from sys import stdout
from autobahn.asyncio.wamp import ApplicationSession
from core.ApplicationRunner import ApplicationRunner

import globalvars
from models.Phone import Phone
from processors.ApiProcessor import ApiProcessor
from core.PhonesManager import PhonesManager

from autobahn.asyncio.component import Component

from threads.ChatsThread import ChatsThread
    
def set_phone(phone):
    if phone['isBanned'] == True:
        if phone['id'] in PhonesManager():
            del PhonesManager()[phone['id']]
        
        return
    
    if phone['id'] in PhonesManager():
        logging.debug(f"Updating phone {phone['id']}.")
        
        PhonesManager()[phone['id']].from_dict(phone)
    else:
        logging.debug(f"Setting up new phone {phone['id']}.")

        PhonesManager()[phone['id']] = Phone(phone).run()

def get_phones():
    phones = ApiProcessor().get('phone', { "isBanned": False })

    logging.debug(f"Received {len(phones)} phones.")
    
    for phone in phones:
        set_phone(phone)

class Component(ApplicationSession):
    async def onJoin(self, details):
        logging.info(f"session on_join: {details}")
        
        get_phones()

        get_chats_thread = ChatsThread()
        get_chats_thread.setDaemon(True)
        get_chats_thread.start()

        async def on_event(event):
            logging.debug(f"Got event on entity: {event['_']}")
            
            if event['_'] == 'TelegramPhone':
                set_phone(event['entity'])
            elif event['_'] == 'TelegramChat':
                get_chats_thread.set_chat(event['entity'])

        await self.subscribe(on_event, 'com.app.entity')
    
    def onDisconnect(self):
        asyncio.get_event_loop().stop()

if __name__ == '__main__':
    globalvars.init()
    
    fh = RotatingFileHandler(filename='log/dev.log', maxBytes=1048576, backupCount=10)
    fh.setLevel(logging.INFO)

    sh = logging.StreamHandler(stdout)
    sh.setLevel(logging.DEBUG)

    logging.basicConfig(
        format="%(threadName)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s:%(lineno)d %(message)s",
        datefmt='%d.%m.%Y %H:%M:%S',
        handlers=[fh, sh],
        level=logging.DEBUG
    )
    
    logging.getLogger('asyncio').setLevel(logging.CRITICAL)
    logging.getLogger('telethon').setLevel(logging.CRITICAL)
    logging.getLogger('requests').setLevel(logging.CRITICAL)
    logging.getLogger('urllib3').setLevel(logging.CRITICAL)
    
    runner = ApplicationRunner(os.environ['WEBSOCKET_URL'], os.environ['WEBSOCKET_REALM'])
    runner.run(Component)
