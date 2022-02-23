import os
import socket
from processors.ApiProcessor import ApiProcessor

def get_all_entities(entity, params={}, entities=[], start=0, limit=50):
    new_entities = ApiProcessor().get(entity, {**params, "_start": start, "_limit": limit})

    if len(new_entities) > 0:
        entities += get_all_entities(entity, params, new_entities, start+limit, limit)
    
    return entities

def init():
    global parser
    
    if "PARSER_ID" in os.environ:
        parser = ApiProcessor().get('telegram/parser', {'id': os.environ['PARSER_ID']})
        
        # if parser["host"]["localIp"] != socket.gethostbyname(socket.gethostname()):
        #     raise Exception("Can't start parser. Parser host local ip doesn't equal with current host local ip.")
        
        ApiProcessor().set('telegram/parser', {'id': parser['id'], 'status': 'running'})
    else:
        raise Exception("Can't start parser. Environment variable 'PARSER_ID' not set.")
    
    all_phones = get_all_entities('telegram/phone')
    global phones_tg_ids
    phones_tg_ids = [phone['internalId'] for phone in all_phones if phone.get('internalId') != None]
    
    all_chats = get_all_entities('telegram/chat')
    global chats_tg_ids
    chats_tg_ids = [chat['internalId'] for chat in all_chats if chat.get('internalId') != None]