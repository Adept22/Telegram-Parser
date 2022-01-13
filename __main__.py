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

async def update_chat(chat):
    print("")
    logging.debug("")
    
    if chat['id'] in ChatsManager():
        print(f"Chat {chat['id']} founded in manager. Updating...")
        logging.debug(f"Chat {chat['id']} founded in manager. Updating...")
        
        chat = ChatsManager()[chat['id']].from_dict(chat)
        
        await chat.init()
            
        if not chat.is_available:
            print(f"Chat {chat.id} actually not available and must be removed.")
            logging.debug(f"Chat {chat.id} actually not available and must be removed.")
            
            del ChatsManager()[chat.id]
    else:
        chat = await Chat(chat).init()
        
        if chat.is_available:
            ChatsManager()[chat.id] = chat

async def update_chats():
    print("")
    logging.debug("")
    
    print("Getting chats...")
    logging.debug("Getting chats...")
    
    chats = ApiProcessor().get('chat', { "isAvailable": True })
    
    for chat in chats:
        await update_chat(chat)
        
    print(f"Received {len(chats)} chats.")
    logging.debug(f"Received {len(chats)} chats.")
    
async def update_phone(phone):
    print("")
    logging.debug("")
    
    if phone['id'] in PhonesManager():
        phone = PhonesManager()[phone['id']].from_dict(phone)
        
        print(f"Updating phone {phone.id}.")
        logging.debug(f"Updating phone {phone.id}.")
        
        await phone.init()
    else:
        phone = await Phone(phone).init()
    
    if phone.session.save() == "" and phone.id in PhonesManager():
        print(f"Phone {phone.id} actually not authorized.")
        logging.debug(f"Phone {phone.id} actually not authorized.")
        
        del PhonesManager()[phone.id]
    elif phone.session.save() != "":
        print(f"Phone {phone.id} now starts to use.")
        logging.debug(f"Phone {phone.id} now starts to use.")
        
        PhonesManager()[phone.id] = phone

async def update_phones():
    print("")
    logging.debug("")
    
    print("Getting phones...")
    logging.debug("Getting phones...")
    
    phones = ApiProcessor().get('phone', { "isBanned": False })
    
    for phone in phones:
        await update_phone(phone)
        
    print(f"Received {len(phones)} phones.")
    logging.debug(f"Received {len(phones)} phones.")

class Component(ApplicationSession):
    async def onJoin(self, details):
        print("")
        logging.debug("")

        print(f"session on_join: {details}")
        logging.info(f"session on_join: {details}")
        
        await update_phones()
        await update_chats()

        async def on_event(event, details=None):
            print("")
            logging.debug("")
            
            print(f"Got event, publication ID {details.publication}, publisher {details.publisher}: {event}")
            logging.debug(f"Got event, publication ID {details.publication}, publisher {details.publisher}: {event}")
            
            if event['_'] == 'TelegramPhone':
                await update_phone(event['entity'])
            elif event['_'] == 'TelegramChat':
                await update_chat(event['entity'])

        await self.subscribe(on_event, 'com.app.entity', options=SubscribeOptions(details_arg='details'))
    
    def onDisconnect(self):
        asyncio.get_event_loop().stop()


if __name__ == '__main__':
    logging.basicConfig(format="%(asctime)s: %(message)s", level=logging.DEBUG, datefmt="%H:%M:%S")
    
    print("")
    logging.debug("")
    
    runner = ApplicationRunner(u"ws://chats-monitoring-api_php_1:7016/ws", u"realm1")
    runner.run(Component)

