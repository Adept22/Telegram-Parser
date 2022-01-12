import re
import json
from errors.InvalidLinkError import InvalidLinkError
from datetime import datetime

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