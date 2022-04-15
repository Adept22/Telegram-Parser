import asyncio
import logging
import re, typing, telethon

import entities, exceptions

if typing.TYPE_CHECKING:
    from telethon import TelegramClient

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
    internal_id, chat_type = telethon.utils.resolve_id(chat.internalId or 0)
    
    return chat_type

async def _get_entity(client: 'TelegramClient', entity) -> 'telethon.types.TypeChat':
    try:
        return await client.get_entity(entity)
    except telethon.errors.FloodWaitError as ex:
        logging.warning(f"FloodWaitError excepted. Sleep {ex.seconds}")

        await asyncio.sleep(ex.seconds)

        return await _get_entity(client, entity)
    except (KeyError, ValueError, telethon.errors.RPCError) as ex:
        raise exceptions.ChatNotAvailableError(str(ex))

async def get_entity(client: 'TelegramClient', chat: 'entities.TypeChat') -> 'telethon.types.TypeChat':
    errors = []

    if chat.internalId != None:
        try:
            return await _get_entity(client, telethon.types.PeerChannel(-(1000000000000 + chat.internalId)))
        except exceptions.ChatNotAvailableError as ex:
            errors.append(str(ex))

        try:
            return await _get_entity(client, telethon.types.PeerChat(-chat.internalId))
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