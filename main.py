import os, sys, multiprocessing, asyncio, logging, colorlog
from logging.handlers import RotatingFileHandler

import globalvars, entities, processes, helpers

processes_manager = {}

def run(type, cls, process, pool, filter = {}) -> None:
    if type not in processes_manager:
        processes_manager[type] = {}

    entities = helpers.get_all(type, {**filter, "parser": {"id": os.environ['PARSER_ID']}})

    logging.debug(f"Received {len(entities)} of {type}.")

    # with pool:
    #     futures = {entity["id"]: pool.submit(process, cls(**entity)) for entity in entities if entity["id"] not in processes_manager[type]}

    #     processes_manager[type] = {**processes_manager[type], **futures}

    entities = [cls(**entity) for entity in entities if entity["id"] not in processes_manager[type]]

    logging.debug(f"New entities {len(entities)} of {type}.")

    for entity in entities:
        processes_manager[type][entity.id] = multiprocessing.Process(target=process, args=(entity, ), daemon=True, name=f"{type}-{entity.id}")
        processes_manager[type][entity.id].start()

    # pool.map_async(process, new_entities)

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
    chats_pool = multiprocessing.Pool()

    while True:
        run('telegram/phone', entities.Phone, processes.phone_process, phones_pool)
        run('telegram/chat', entities.Chat, processes.chat_process, chats_pool, {"isAvailable": True})
        
        asyncio.run(asyncio.sleep(60))
