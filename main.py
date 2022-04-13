import os
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from sys import stdout

import globalvars, entities
from services import ApiService, PhonesManager, ChatsManager

def set_chat(chat: 'dict') -> None:
    if chat['isAvailable'] == False:
        if chat['id'] in ChatsManager():
            del ChatsManager()[chat['id']]

        return

    if chat['id'] in ChatsManager():
        logging.debug(f"Updating chat {chat['id']}.")

        ChatsManager()[chat['id']].deserialize(chat)
    else:
        logging.debug(f"Setting up new chat {chat['id']}.")

        ChatsManager()[chat['id']] = entities.Chat(**chat).run()

def get_all_chats(chats: 'list' = [], start: 'int' = 0, limit: 'int' = 50) -> 'list[dict]':
    new_chats = ApiService().get('telegram/chat', {"parser": {"id": os.environ['PARSER_ID']}, "isAvailable": True, "_start": start, "_limit": limit})

    if len(new_chats) > 0:
        chats += get_all_chats(new_chats, start + limit, limit)

    return chats

def get_chats() -> None:
    chats = get_all_chats(limit=20)

    logging.debug(f"Received {len(chats)} chats.")

    for chat in chats:
        set_chat(chat)

def set_phone(phone: 'dict') -> None:
    if phone['isBanned'] == True:
        if phone['id'] in PhonesManager():
            del PhonesManager()[phone['id']]

        return

    if phone['id'] in PhonesManager():
        logging.debug(f"Updating phone {phone['id']}.")

        PhonesManager()[phone['id']].deserialize(phone)
    else:
        logging.debug(f"Setting up new phone {phone['id']}.")

        PhonesManager()[phone['id']] = entities.Phone(**phone).run()

def get_phones() -> None:
    phones = ApiService().get('telegram/phone', { "parser": {"id": os.environ['PARSER_ID']}, "isBanned": False })

    logging.debug(f"Received {len(phones)} phones.")

    for phone in phones:
        set_phone(phone)

if __name__ == '__main__':
    globalvars.init()

    eh = RotatingFileHandler(filename='log/error.log', maxBytes=1048576, backupCount=10)
    eh.setLevel(logging.WARNING)

    fh = RotatingFileHandler(filename='log/app.log', maxBytes=1048576, backupCount=5)
    fh.setLevel(logging.INFO)

    sh = logging.StreamHandler(stdout)
    sh.setLevel(logging.DEBUG)

    logging.basicConfig(
        format="%(process)s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s:%(lineno)d %(message)s",
        datefmt='%d.%m.%Y %H:%M:%S',
        handlers=[eh, fh, sh],
        level=logging.DEBUG
    )

    logging.getLogger('asyncio').setLevel(logging.CRITICAL)
    logging.getLogger('telethon').setLevel(logging.CRITICAL)
    logging.getLogger('requests').setLevel(logging.CRITICAL)
    logging.getLogger('urllib3').setLevel(logging.CRITICAL)

    while True:
        get_phones()
        get_chats()

        asyncio.run(asyncio.sleep(60))
