from processors.ApiProcessor import ApiProcessor

def get_all_entities(entity, params={}, entities=[], start=0, limit=50):
    new_entities = ApiProcessor().get(entity, {**params, "_start": start, "_limit": limit})

    if len(new_entities) > 0:
        entities += get_all_entities(entity, params, new_entities, start+limit, limit)
    
    return entities

def init():
    all_phones = get_all_entities('phone')
    global phones_tg_ids
    phones_tg_ids = [phone['internalId'] for phone in all_phones if phone.get('internalId') != None]
    
    all_chats = get_all_entities('chat')
    global chats_tg_ids
    chats_tg_ids = [chat['internalId'] for chat in all_chats if chat.get('internalId') != None]