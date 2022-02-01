from processors.ApiProcessor import ApiProcessor

def init():
    all_phones = ApiProcessor().get('phone')
    global phones_tg_ids
    phones_tg_ids = [phone['internalId'] for phone in all_phones if phone.get('internalId') != None]
    
    all_chats = ApiProcessor().get('chat')
    global chats_tg_ids
    chats_tg_ids = [chat['internalId'] for chat in all_chats if chat.get('internalId') != None]