import os
import socket
from services import ApiService

def get_all_entities(entities: 'str', params: 'dict' = {}, entities: 'list' = [], start: 'int' = 0, limit: 'int' = 50) -> 'list[dict]':
    new_entities = ApiService().get(entities, {**params, "_start": start, "_limit": limit})

    if len(new_entities) > 0:
        entities += get_all_entities(entities, params, new_entities, start+limit, limit)
    
    return entities

def init():
    global parser
    
    if "PARSER_ID" in os.environ:
        parser = ApiService().get('telegram/parser', {'id': os.environ['PARSER_ID']})
        
        # if parser["host"]["localIp"] != socket.gethostbyname(socket.gethostname()):
        #     raise Exception("Can't start parser. Parser host local ip doesn't equal with current host local ip.")
        
        ApiService().set('telegram/parser', {'id': parser['id'], 'status': 'running'})
    else:
        raise Exception("Can't start parser. Environment variable 'PARSER_ID' not set.")