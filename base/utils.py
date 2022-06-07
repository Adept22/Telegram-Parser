"""Utilities for tasks"""

import os
import random
import re
# import json
import urllib.parse
import requests
import telethon
from opentele.tl import TelegramClient as OpenteleClient
from opentele.api import API, APIData
from telethon.sessions import StringSession
from base import models
from base import exceptions


APIS = [
    API.TelegramDesktop,
    API.TelegramAndroid,
    API.TelegramAndroidX,
    API.TelegramIOS,
    API.TelegramMacOS,
]


class Singleton(type):
    """Metaclass for singletone pattern representation"""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """Returns class single instance"""
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class TelegramClient(OpenteleClient):
    """Extended telegram client"""

    def __init__(self, phone: 'models.TypePhone', *args, **kwargs):
        self.phone = phone

        if self.phone.api is None:
            self.phone.api = APIS[random.randint(0, len(APIS) - 1)].Generate().__dict__

            del self.phone.api["pid"]

            self.phone.save()

        super().__init__(
            *args,
            **kwargs,
            connection_retries=-1,
            retry_delay=5,
            session=StringSession(phone.session),
            api=APIData(**self.phone.api)
        )

    async def start(self):
        if not self.is_connected():
            await self.connect()

        if await self.get_me() is not None:
            return self

        raise exceptions.UnauthorizedError('Phone not authorized')


TypeTelegramClient = TelegramClient


class ApiService(metaclass=Singleton):
    """Service for working with API"""
    _cache = {}

    def _get(self, endpoint: 'str', id: 'str', force: 'bool' = False):
        if id not in self._cache or force:
            self._cache[id] = self.send("GET", endpoint, f"{id}/")

        return self._cache[id]

    def _filter(self, endpoint: 'str', **kwargs):
        result = self.send("GET", endpoint, "?" + urllib.parse.urlencode(kwargs))

        for entity in result["results"]:
            self._cache[entity["id"]] = entity

        return result

    def _create(self, endpoint: 'str', **kwargs):
        entity = self.send("POST", endpoint, "", body=kwargs)

        self._cache[entity["id"]] = entity

        return self._cache[entity["id"]]

    def _update(self, endpoint: 'str', id: 'str', **kwargs):
        self._cache[id] = self.send("PUT", endpoint, f"{id}/", body=kwargs)

        return self._cache[id]

    def get(self, endpoint: 'str', **kwargs) -> 'dict | list[dict]':
        """Get entity or list of entities"""

        if kwargs.get('id') is not None:
            return self._get(endpoint, kwargs['id'], kwargs.get("force", False))

        return self._filter(endpoint, **kwargs)

    def set(self, endpoint: 'str', **kwargs) -> 'dict':
        """Create or update entity"""

        if kwargs.get('id') is not None:
            return self._update(endpoint, kwargs.pop("id"), **kwargs)

        return self._create(endpoint, **kwargs)

    def delete(self, endpoint: 'str', id: 'str') -> 'None':
        """Delete entity"""

        self.send("DELETE", endpoint, f"{id}/")

        del self._cache[id]

    def check_chunk(self, endpoint: 'str', id: 'str', filename: 'str', chunk_number: 'int',
                    chunk_size: 'int' = 1048576) -> 'bool':
        """Check if chunk was uploaded on server"""

        try:
            self.send("GET", endpoint, f"{id}/chunk/",
                      params={"filename": filename, "chunkNumber": chunk_number, "chunkSize": chunk_size})
        except exceptions.RequestException as ex:
            if ex.code == 404:
                return False
            else:
                raise ex
        else:
            return True

    def chunk(self, endpoint: 'str', id: 'dict', filename: 'str', chunk: 'bytes', chunk_number: 'int',
              chunk_size: 'int', total_chunks: 'int', total_size: 'int') -> 'None':
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

            # try:
            #     _json = r.json()
            # except json.decoder.JSONDecodeError:
            #     content = r.text
            # else:
            #     content = _json.get("message", None)

            if r.status_code == 409:
                raise exceptions.UniqueConstraintViolationError(r.text)
            else:
                raise exceptions.RequestException(r.status_code, r.text)

        if r.status_code == 204:
            return None

        return r.json()


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
    """
    Parses the given username or channel access hash, given
    a string, username or URL. Returns a tuple consisting of
    both the stripped, lowercase username and whether it is
    a joinchat/ hash (in which case is not lowercase'd).

    Returns ``(None, False)`` if the ``username`` or link is not valid.
    """

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
