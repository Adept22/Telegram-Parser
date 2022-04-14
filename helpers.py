import re, typing, telethon

import entities, exceptions

if typing.TYPE_CHECKING:
    from telethon import TelegramClient

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def get_hash(link: 'str') -> 'tuple[str | None, str | None]':
    if link is None:
        raise exceptions.InvalidLinkError('Unexpected link')

    link = re.sub(r'https?:\/\/t\.me\/', '', link)

    matches = re.match(r'^(?:joinchat\/|\+)([-_.a-zA-Z0-9]+)$', link)

    hash = matches.group(1) if not matches is None else None

    channel = link if hash is None else None
    
    if (channel == None and hash == None) or (channel != None and hash != None):
        raise exceptions.InvalidLinkError('Unexpected link')

    return channel, hash

def user_title(user: 'telethon.types.TypeUser'):
    if user.username != None:
        return user.username
    elif user.first_name or user.last_name:
        return user.first_name or user.last_name
    else:
        return user.id

def get_type(chat: 'telethon.types.TypeChat'):
    if isinstance(chat, telethon.types.Channel):
        return 'channel'
    elif isinstance(chat, telethon.types.Chat):
        return 'chat'

    return None

async def get_entity(client: 'TelegramClient', chat: 'entities.TypeChat') -> 'telethon.types.TypeChat':
    try:
        if chat.type != None:
            return await client.get_entity(chat.internalId)
        elif chat.internalId != None:
            try:
                return await client.get_entity(telethon.types.PeerChannel(-(1000000000000 + chat.internalId)))
            except (KeyError, ValueError, telethon.errors.RPCError) as ex:
                try:
                    return await client.get_entity(telethon.types.PeerChat(-chat.internalId))
                except (KeyError, ValueError, telethon.errors.RPCError) as ex:
                    pass
        
        if chat.username != None:
            return await client.get_entity(chat.username)
        elif chat.hash != None:
            return await client.get_entity(chat.hash)
        else:
            return await client.get_entity(chat.link)
    except (KeyError, ValueError, telethon.errors.RPCError) as ex:
        raise exceptions.ChatNotAvailableError(ex)