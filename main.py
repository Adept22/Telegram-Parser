import os, sys, asyncio, logging, colorlog
from logging.handlers import RotatingFileHandler

import globalvars, entities, processes, helpers

def set_chat(chat: 'dict') -> None:
    if len(globalvars.manager_chats) > 0:
        if chat['id'] in globalvars.manager_chats:
            if chat['isAvailable'] == False:
                del globalvars.manager_chats[chat['id']]
            else:
                globalvars.manager_chats[chat['id']].deserialize(chat)

            return

    chat_process = processes.ChatProcess(entities.Chat(**chat))
    chat_process.start()

def get_chats() -> None:
    chats = helpers.get_all('telegram/chat', {"parser": {"id": os.environ['PARSER_ID']}, "isAvailable": True})

    logging.debug(f"Received {len(chats)} chats.")

    for chat in chats:
        set_chat(chat)

def set_phone(phone: 'dict') -> None:
    if len(globalvars.manager_phones) > 0:
        if phone['id'] in globalvars.manager_phones:
            if phone['isBanned'] == True:
                del globalvars.manager_phones[phone['id']]
            else:
                globalvars.manager_phones[phone['id']].deserialize(phone)

            return
    
    phone_process = processes.PhoneProcess(entities.Phone(**phone))
    phone_process.start()

def get_phones() -> None:
    phones = helpers.get_all('telegram/phone', {"parser": {"id": os.environ['PARSER_ID']}})

    logging.debug(f"Received {len(phones)} phones.")

    for phone in phones:
        set_phone(phone)

if __name__ == '__main__':
    globalvars.init()

    datefmt = "%d.%m.%Y %H:%M:%S"
    # format = "%(processName)s:%(process)d %(asctime)s %(levelname)s %(filename)s:%(funcName)s:%(lineno)d %(message)s"
    format = "%(threadName)s %(asctime)s %(levelname)s %(message)s"

    eh = RotatingFileHandler(filename='log/error.log', maxBytes=1048576, backupCount=10)
    eh.setLevel(logging.WARNING)

    fh = RotatingFileHandler(filename='log/app.log', maxBytes=1048576, backupCount=5)
    fh.setLevel(logging.INFO)

    sh = logging.StreamHandler(sys.stdout)
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
