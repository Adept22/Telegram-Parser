import os, asyncio, logging, colorlog
from logging.handlers import RotatingFileHandler
from sys import stdout

import globalvars, entities, services, helpers

def set_chat(chat: 'dict') -> None:
    if chat['isAvailable'] == False:
        if chat['id'] in services.ChatsManager():
            del services.ChatsManager()[chat['id']]

        return

    if chat['id'] in services.ChatsManager():
        services.ChatsManager()[chat['id']].deserialize(chat)()
    else:
        services.ChatsManager()[chat["id"]] = entities.Chat(**chat)()

def get_chats() -> None:
    chats = helpers.get_all('telegram/chat', {"parser": {"id": os.environ['PARSER_ID']}, "isAvailable": True})

    logging.debug(f"Received {len(chats)} chats.")

    for chat in chats:
        set_chat(chat)

    logging.debug(f'Chats in manager {len(services.ChatsManager().items())}')

def set_phone(phone: 'dict') -> None:
    if len(globalvars.PhonesManager) > 0:
        if phone['id'] in globalvars.PhonesManager:
            if phone['isBanned'] == True:
                del globalvars.PhonesManager[phone['id']]
            else:
                globalvars.PhonesManager[phone['id']].deserialize(phone)()

            return
    
    entities.Phone(**phone)()

def get_phones() -> None:
    phones = helpers.get_all('telegram/phone', {"parser": {"id": os.environ['PARSER_ID']}})

    logging.debug(f"Received {len(phones)} phones.")

    for phone in phones:
        set_phone(phone)

if __name__ == '__main__':
    globalvars.init()

    datefmt = "%d.%m.%Y %H:%M:%S"
    format = "%(processName)s:%(process)d %(asctime)s %(levelname)s %(filename)s:%(funcName)s:%(lineno)d %(message)s"

    eh = RotatingFileHandler(filename='log/error.log', maxBytes=1048576, backupCount=10)
    eh.setLevel(logging.WARNING)

    fh = RotatingFileHandler(filename='log/app.log', maxBytes=1048576, backupCount=5)
    fh.setLevel(logging.INFO)

    sh = logging.StreamHandler(stdout)
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(colorlog.ColoredFormatter("%(log_color)s" + format, datefmt))

    logging.basicConfig(datefmt=datefmt, format=format, handlers=[eh, fh, sh], level=logging.DEBUG)

    logging.getLogger('asyncio').setLevel(logging.CRITICAL)
    logging.getLogger('telethon').setLevel(logging.CRITICAL)
    logging.getLogger('requests').setLevel(logging.CRITICAL)
    logging.getLogger('urllib3').setLevel(logging.CRITICAL)

    get_phones()
    get_chats()

    while True:
        asyncio.run(asyncio.sleep(60))
