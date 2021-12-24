import re

def get_hash(link):
    if link is None:
        raise Exception('Unexpected link')

    link = re.sub(r'https?:\/\/t\.me\/', '', link)

    matches = re.match(r'(?:joinchat\/|\+)(\w{16})', link)

    hash = matches.group(1) if not matches is None else None

    link = link if hash is None else None

    return link, hash