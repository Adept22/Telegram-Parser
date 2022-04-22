import multiprocessing
import os, sys, asyncio, logging, colorlog
from logging.handlers import RotatingFileHandler

import globalvars, processes, helpers

processes_manager = {}

def run(type, process, pool, filter = {}) -> None:
    entities = helpers.get_all(type, filter)

    logging.debug(f"Received {len(entities)} of {type}.")
    
    for entity in entities:
        if entity["id"] not in processes_manager:
            processes_manager[entity["id"]] = pool.apply_async(process, (entity, ))

if __name__ == '__main__':
    globalvars.init()

    datefmt = "%d.%m.%Y %H:%M:%S"
    # format = "%(processName)s:%(process)d %(asctime)s %(levelname)s %(filename)s:%(funcName)s:%(lineno)d %(message)s"
    format = "%(processName)s:%(threadName)s %(asctime)s %(levelname)s %(message)s"
    
    # eh = RotatingFileHandler(filename='log/error.log', maxBytes=1048576, backupCount=20)
    # eh.setLevel(logging.ERROR)

    # fh = RotatingFileHandler(filename='log/app.log', maxBytes=1048576, backupCount=20)
    # fh.setLevel(logging.INFO)

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(colorlog.ColoredFormatter("%(log_color)s" + format, datefmt))

    logging.basicConfig(datefmt=datefmt, format=format, handlers=[sh], level=logging.DEBUG)

    logging.getLogger('asyncio').setLevel(logging.CRITICAL)
    logging.getLogger('telethon').setLevel(logging.CRITICAL)
    logging.getLogger('requests').setLevel(logging.CRITICAL)
    logging.getLogger('urllib3').setLevel(logging.CRITICAL)

    phones_pool = multiprocessing.Pool()
    chats_pool = multiprocessing.Pool(100)

    while True:
        run('telegram/phone', processes.phone_process, phones_pool, {"parser": {"id": os.environ['PARSER_ID']}})
        run('telegram/chat', processes.chat_process, chats_pool, {"parser": {"id": os.environ['PARSER_ID']}, "isAvailable": True})
        
        asyncio.run(asyncio.sleep(60))
