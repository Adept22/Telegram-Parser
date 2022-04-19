import os, socket
from managers import ParserManager
import services

def get_all_entities(entity: 'str', params: 'dict' = {}, entities: 'list' = [], start: 'int' = 0, limit: 'int' = 50) -> 'list[dict]':
    new_entities = services.ApiService().get(entity, {**params, "_start": start, "_limit": limit})

    if len(new_entities) > 0:
        entities += get_all_entities(entity, params, new_entities, start+limit, limit)
    
    return entities

def init():
    global parser
    
    if "PARSER_ID" in os.environ:
        parser = services.ApiService().get('telegram/parser', {'id': os.environ['PARSER_ID']})
        
        # if parser["host"]["localIp"] != socket.gethostbyname(socket.gethostname()):
        #     raise Exception("Can't start parser. Parser host local ip doesn't equal with current host local ip.")
        
        services.ApiService().set('telegram/parser', {'id': parser['id'], 'status': 'running'})
    else:
        raise Exception("Can't start parser. Environment variable 'PARSER_ID' not set.")

    manager = ParserManager()
    manager.start()

    global manager_phones
    manager_phones = manager.phones()

    global manager_chats
    manager_chats = manager.chats()