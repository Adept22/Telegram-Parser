import asyncio
import logging
from autobahn.wamp.types import SubscribeOptions
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner

from models.Chat import Chat
from models.Phone import Phone
from core.ChatsManager import ChatsManager
from core.PhonesManager import PhonesManager
from processors.ApiProcessor import ApiProcessor

from autobahn.asyncio.component import Component

phones = PhonesManager()

async def update_phone(phone):
    print("")
    logging.debug("")
    
    if not phone['id'] in phones:
        phone = Phone(phone)
    else:
        phone = phones[phone['id']]
        
        print(f"Updating phone {phone.id}.")
        logging.debug(f"Updating phone {phone.id}.")
        
        phone.from_dict(phone)
        
    await phone.init()
    
    if await phone.client.is_user_authorized():
        phones[phone.id] = phone
    elif phones.get(phone.id) != None:
        del phones[phone.id]

async def update_phones():
    print("")
    logging.debug("")
    
    print("Getting phones...")
    logging.debug("Getting phones...")
    
    new_phones = ApiProcessor().get('phone')
    
    for _phone in new_phones:
        await update_phone(_phone)

class Component(ApplicationSession):
    async def onJoin(self, details):
        print("")
        logging.debug("")

        print(f"session on_join: {details}")
        logging.info(f"session on_join: {details}")
        
        await update_phones()

        async def on_event(event, details=None):
            print("")
            logging.debug("")
            
            print(f"Got event, publication ID {details.publication}, publisher {details.publisher}: {event}")
            logging.debug(f"Got event, publication ID {details.publication}, publisher {details.publisher}: {event}")
            
            if event['_'] == 'TelegramPhone':
                await update_phone(event['entity'])

        await self.subscribe(on_event, 'com.app.entity', options=SubscribeOptions(details_arg='details'))
    
    def onDisconnect(self):
        asyncio.get_event_loop().stop()


if __name__ == '__main__':
    logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.DEBUG, datefmt="%H:%M:%S")
    
    print("")
    logging.debug("")
    
    runner = ApplicationRunner(u"ws://chats_php_1:7016/ws", u"realm1")
    runner.run(Component)

