import re
import os
import requests
import json
import telethon
from telethon.sessions import StringSession
import urllib.parse
import base.models as models
import base.exceptions as exceptions

class Singleton(type):
    """Metaclass for singletone pattern representation"""
    _instances = {}

    def __call__(cls, *args, **kwargs):
        """Returns class single instance"""
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class TelegramClient(telethon.TelegramClient):
    """Extended telegram client"""

    def __init__(self, phone: 'models.TypePhone', *args, **kwargs):
        self.phone = phone

        super(TelegramClient, self).__init__(*args, **kwargs, connection_retries=-1, retry_delay=5,
                                             session=StringSession(phone.session), api_id=phone.parser.api_id,
                                             api_hash=phone.parser.api_hash)

    async def start(self):
        from base.exceptions import UnauthorizedError

        if not self.is_connected():
            await self.connect()

        if await self.is_user_authorized() and await self.get_me() is not None:
            return self
        else:
            raise UnauthorizedError(f'Phone not authorized')

    async def __aenter__(self):
        return await self.start()


class ApiService(metaclass=Singleton):
    """Service for working with API"""
    _cache = {}

    def get(self, endpoint: 'str', **kwargs) -> 'dict | list[dict]':
        """Get entity or list of entities"""

        path = kwargs['id'] + "/" if kwargs.get('id') is not None else "?" + urllib.parse.urlencode(kwargs)

        return self.send("GET", endpoint, path, kwargs)

    def set(self, endpoint: 'str', **kwargs) -> 'dict':
        """Create or update entity"""
        method = 'PUT' if kwargs.get('id') is not None else 'POST'
        path = kwargs['id'] + "/" if kwargs.get('id') is not None else ""

        return self.send(method, endpoint, path, kwargs)

    def delete(self, endpoint: 'str', id: 'str') -> 'None':
        """Delete entity"""
        return self.send("DELETE", endpoint, f"{id}/")

    def check_chunk(self, endpoint: 'str', id: 'str', filename: 'str', chunk_number: 'int',
                     chunk_size: 'int' = 1048576) -> 'bool':
        """Check if chunk was uploaded on server"""
        try:
            self.send(
                "GET", 
                endpoint, 
                f"{id}/chunk/",
                params={"filename": filename, "chunkNumber": chunk_number, "chunkSize": chunk_size}
            )
        except exceptions.RequestException as ex:
            if ex.code == 404:
                return False
            else:
                raise ex
        else:
            return True

    def chunk(self, endpoint: 'str', id: 'dict', filename: 'str', chunk: 'bytes', chunk_number: 'int', chunk_size: 'int',
              total_chunks: 'int', total_size: 'int') -> 'None':
        """Send chunk on server"""
        if self.check_chunk(endpoint, id, filename, chunk_number, chunk_size):
            return

        return self.send("POST", endpoint, f"{id}/chunk/",
                         params={"filename": filename, "chunkNumber": chunk_number, "totalChunks": total_chunks,
                                 "totalSize": total_size}, files={"chunk": chunk})

    def send(self, method: 'str', endpoint: 'str', path: 'str', body: 'dict' = None, params: 'dict' = None,
             files: 'dict' = None) -> 'dict | list[dict] | None':
        """Send request to API"""
        try:
            r = requests.request(
                method,
                os.environ['API_URL'] + f"/telegram/{endpoint}/{path}",
                headers={"Accept": "application/json"},
                json=body,
                params=params,
                files=files,
                verify=False
            )
        except requests.exceptions.ConnectionError as ex:
            raise exceptions.RequestException(500, str(ex))

        try:
            r.raise_for_status()
        except requests.exceptions.RequestException as ex:
            r: 'requests.Response | None' = ex.response

            try:
                _json = r.json()
            except json.decoder.JSONDecodeError:
                content = r.text
            else:
                content = _json.get("message", None)

            if r.status_code == 409:
                raise exceptions.UniqueConstraintViolationError(content)
            else:
                raise exceptions.RequestException(r.status_code, content)

        if r.status_code == 204:
            return None

        return r.json()

class CacheService(object, metaclass=Singleton):
    _cache = {}

    def get_cache(self, entity: 'models.TypeEntity'):
        if entity.id is not None:
            if entity.id in self._cache:
                return self._cache[entity.id]

        return None

    def set_cache(self, entity: 'models.TypeEntity'):
        pass

LINK_RE = re.compile(
    r'(?:@|(?:https?:\/\/)?(?:www\.)?(?:telegram\.(?:me|dog)|t\.me)\/(?:@|joinchat\/|\+)?|'
    r'tg:\/\/(?:join|resolve)\?(?:invite=|domain=))'
    r'(?:[a-zA-Z0-9_.-](?:(?!__)\w){3,30}[a-zA-Z0-9_.-]|'
    r'gif|vid|pic|bing|wiki|imdb|bold|vote|like|coub)',
    re.IGNORECASE
)

HTTP_RE = re.compile(r'^(?:@|(?:https?://)?(?:www\.)?(?:telegram\.(?:me|dog)|t\.me))/(\+|joinchat/)?')

TG_RE = re.compile(r'^tg://(?:(join)|resolve)\?(?:invite|domain)=')


def parse_username(link: 'str') -> 'tuple[str | None, str | None]':
    link = link.strip()

    m = re.match(HTTP_RE, link) or re.match(TG_RE, link)

    if m:
        link = link[m.end():]
        is_invite = bool(m.group(1))

        if is_invite:
            return link, True
        else:
            link = link.rstrip('/')

    if telethon.utils.VALID_USERNAME_RE.match(link):
        return link.lower(), False
    else:
        return None, False

