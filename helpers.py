import asyncio
import re, telethon
import services, exceptions

def get_all(entity: 'str', body: 'dict', entities: 'list' = [], start: 'int' = 0, limit: 'int' = 50):
    new_entities = services.ApiService().get(entity, {**body, "_start": start, "_limit": limit})

    if len(new_entities) > 0:
        return get_all(entity, body, entities + new_entities, start + limit, limit)

    return entities

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
