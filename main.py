import os
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from sys import stdout
from core.ChatsManager import ChatsManager

import globalvars
from models.ChatEntity import Chat
from models.PhoneEntity import Phone
from processors.ApiProcessor import ApiProcessor
from core.PhonesManager import PhonesManager

def set_chat(chat):
    if chat['isAvailable'] == False:
        if chat['id'] in ChatsManager():
            del ChatsManager()[chat['id']]

        return

    if chat['id'] in ChatsManager():
        logging.debug(f"Updating chat {chat['id']}.")

        ChatsManager()[chat['id']].from_dict(chat)
    else:
        logging.debug(f"Setting up new chat {chat['id']}.")

        ChatsManager()[chat['id']] = Chat(chat).run()

def get_all_chats(chats=[], start=0, limit=50):
    new_chats = ApiProcessor().get('telegram/chat', {"parser": {"id": os.environ['PARSER_ID']}, "isAvailable": True, "_start": start, "_limit": limit})

    if len(new_chats) > 0:
        chats += get_all_chats(new_chats, start+limit, limit)

    return chats

def get_chats():
    chats = get_all_chats(limit=20)

    logging.debug(f"Received {len(chats)} chats.")

    for chat in chats:
        set_chat(chat)

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
    phones = ApiProcessor().get('telegram/phone', { "parser": {"id": os.environ['PARSER_ID']}, "isBanned": False })

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
        format="%(threadName)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s:%(lineno)d %(message)s",
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
