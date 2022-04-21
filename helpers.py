import asyncio
import logging
import re, typing, telethon

import entities, exceptions
from services import ApiService

if typing.TYPE_CHECKING:
    from telethon import TelegramClient

def get_all(entity: 'str', body: 'dict', entities: 'list' = [], start: 'int' = 0, limit: 'int' = 50):
    new_entities = ApiService().get(entity, {**body, "_start": start, "_limit": limit})

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

async def _get_entity(client: 'TelegramClient', entity) -> 'telethon.types.TypeChat':
    try:
        return await client.get_entity(entity)
    # except telethon.errors.FloodWaitError as ex:
    #     logging.warning(f"FloodWaitError excepted. Sleep {ex.seconds}")

    #     await asyncio.sleep(ex.seconds)

    #     return await _get_entity(client, entity)
    except (KeyError, ValueError, telethon.errors.RPCError) as ex:
        raise exceptions.ChatNotAvailableError(str(ex))

async def get_entity(client: 'TelegramClient', chat: 'entities.TypeChat') -> 'telethon.types.TypeChat':
    errors = []

    if chat._internalId != None:
        if chat._internalId > 0:
            try:
                return await _get_entity(client, telethon.types.PeerChannel(channel_id=-(1000000000000 + chat._internalId)))
            except exceptions.ChatNotAvailableError as ex:
                errors.append(str(ex))

            try:
                return await _get_entity(client, telethon.types.PeerChat(chat_id=-chat._internalId))
            except exceptions.ChatNotAvailableError as ex:
                errors.append(str(ex))
        else:
            cls = telethon.utils.resolve_id(chat._internalId)[1]

            try:
                return await _get_entity(client, cls(chat._internalId))
            except exceptions.ChatNotAvailableError as ex:
                errors.append(str(ex))
        
    if chat.username != None:
        try:
            return await _get_entity(client, chat.username)
        except exceptions.ChatNotAvailableError as ex:
            errors.append(str(ex))

    try:
        return await _get_entity(client, chat.link)
    except exceptions.ChatNotAvailableError as ex:
        errors.append(str(ex))
    
    raise exceptions.ChatNotAvailableError(". ".join(errors))