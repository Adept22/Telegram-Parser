import re
from errors.InvalidLinkError import InvalidLinkError

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