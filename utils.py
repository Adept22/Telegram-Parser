import re
import logging
import json
from errors.InvalidLinkError import InvalidLinkError
from datetime import datetime
from processors.ApiProcessor import ApiProcessor

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

def get_hash(link):
    if link is None:
        raise InvalidLinkError('Unexpected link')

    link = re.sub(r'https?:\/\/t\.me\/', '', link)

    matches = re.match(r'^(?:joinchat\/|\+)(\w+)$', link)

    hash = matches.group(1) if not matches is None else None

    channel = link if hash is None else None
    
    if (channel == None and hash == None) or (channel != None and hash != None):
        raise InvalidLinkError('Unexpected link')

    return channel, hash

class DateTimeEncoder(json.JSONEncoder):
    def default(self, item):
        if isinstance(item, datetime):
            return item.isoformat()
        if isinstance(item, bytes):
            return list(item)
        return json.JSONEncoder.default(self, item)

async def profile_media_process(client, entity, uuid, media_type):
    pathFolder = f'./uploads/{media_type}-media/{uuid}/'

    pathToFile = await client.download_profile_photo(
        entity=entity,
        file=f'{pathFolder}0',
        download_big=True
    )

    if pathToFile != None:
        ApiProcessor().set(f'{media_type}-media', { 
            media_type: { "id": uuid }, 
			'internalId': f'{entity.id}',
            'path': f'{pathFolder}/{re.split("/", pathToFile)[-1]}'
        })

    # async for photo in client.iter_profile_photos(types.PeerUser(user_id=user.id)):
    #     pass

async def get_media(client, media, uuid, media_type):
    pathFolder = f'./uploads/{media_type}-media/{uuid}/'

    pathToFile = await client.download_media(
        message=media,
        file=f'{pathFolder}/{media.id}',
        thumb=media.sizes[-2]
    )

    if pathToFile != None:
        ApiProcessor().set(f'{media_type}-media', { 
            media_type: { "id": uuid }, 
			'internalId': {f'{media.id}'},
            'path': f'{pathFolder}/{re.split("/", pathToFile)[-1]}'
        })


def user_title(user):
    if user.username != None:
        return user.username
    elif user.first_name or user.last_name:
        return user.first_name or user.last_name
    else:
        return user.id