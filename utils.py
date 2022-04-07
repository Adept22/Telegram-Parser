import re
from errors.InvalidLinkError import InvalidLinkError

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

    matches = re.match(r'^(?:joinchat\/|\+)([-_.a-zA-Z0-9]+)$', link)

    hash = matches.group(1) if not matches is None else None

    channel = link if hash is None else None
    
    if (channel == None and hash == None) or (channel != None and hash != None):
        raise InvalidLinkError('Unexpected link')

    return channel, hash

def user_title(user):
    if user.username != None:
        return user.username
    elif user.first_name or user.last_name:
        return user.first_name or user.last_name
    else:
        return user.id