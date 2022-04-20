import os, sys, typing, multiprocessing, asyncio, logging, colorlog
from logging.handlers import RotatingFileHandler

import globalvars, entities, processes, helpers

if typing.TYPE_CHECKING:
    from multiprocessing.pool import Pool

def set_chat(chat: 'dict', pool: 'Pool') -> None:
    if len(globalvars.manager_chats) > 0:
        if chat['id'] in globalvars.manager_chats:
            if chat['isAvailable'] == False:
                del globalvars.manager_chats[chat['id']]
            else:
                globalvars.manager_chats[chat['id']].deserialize(chat)

            return
        
    chat_process = processes.ChatProcess(
        entities.Chat(**chat), 
        globalvars.manager_phones, 
        globalvars.manager_chats,
        globalvars.phones_manager_condition
    )
    chat_process.start()

    # def callback(result):
    #     logging.info(result)
        
    # def error_callback(result):
    #     logging.error(result)

    # pool.apply_async(
    #     processes.ChatProcess, 
    #     (entities.Chat(**chat), globalvars.manager_phones, globalvars.manager_chats),
    #     callback,
    #     error_callback
    # )

def get_chats(pool: 'Pool') -> None:
    chats = helpers.get_all('telegram/chat', {"parser": {"id": os.environ['PARSER_ID']}, "isAvailable": True})

    logging.debug(f"Received {len(chats)} chats.")

    for chat in chats:
        set_chat(chat, pool)

def set_phone(phone: 'dict', pool: 'Pool') -> None:
    if len(globalvars.manager_phones) > 0:
        if phone['id'] in globalvars.manager_phones:
            if phone['isBanned'] == True:
                del globalvars.manager_phones[phone['id']]
            else:
                globalvars.manager_phones[phone['id']].deserialize(phone)

            return
    
    phone_process = processes.PhoneProcess(
        entities.Phone(**phone), 
        globalvars.manager_phones, 
        globalvars.phones_manager_condition
    )
    phone_process.start()

    # def callback(result):
    #     logging.info(result)
        
    # def error_callback(result):
    #     logging.error(result)

    # pool.apply_async(
    #     processes.PhoneProcess, 
    #     (entities.Phone(**phone), globalvars.manager_phones),
    #     callback,
    #     error_callback
    # )

def get_phones(pool: 'Pool') -> None:
    phones = helpers.get_all('telegram/phone', {"parser": {"id": os.environ['PARSER_ID']}})

    logging.debug(f"Received {len(phones)} phones.")

    for phone in phones:
        set_phone(phone, pool)

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

    with multiprocessing.Pool() as phones_pool:
        get_phones(phones_pool)

        phones_pool.close()

    with multiprocessing.Pool() as chats_pool:
        get_chats(chats_pool)

        phones_pool.close()
        phones_pool.join()

    while True:
        asyncio.run(asyncio.sleep(60))
