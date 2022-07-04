"""Utilities for tasks"""
import asyncio
import os
import random
import re
import math
import names
import urllib.parse
import requests
import telethon
from opentele.tl import TelegramClient as OpenteleClient
from opentele.api import API, APIData
from telethon import types, functions, hints
from telethon.sessions import StringSession
from telethon.client import downloads
from telethon.client.chats import _ParticipantsIter, _MAX_PARTICIPANTS_CHUNK_SIZE
from telethon.client.account import _TakeoutClient as _TelethonTakeoutClient
from . import models, exceptions, utils


class Singleton(type):
    """Metaclass for singletone pattern representation"""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """Returns class single instance"""
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class _TakeoutClient(_TelethonTakeoutClient):
    async def __aenter__(self):
        client = self.__client

        if client.session.takeout_id is None:
            client.session.takeout_id = (await client(self.__request)).id
        elif self.__request is not None:
            raise ValueError("Can't send a takeout request while another "
                             "takeout for the current session still not been finished yet.")

        client.phone.takeout = True
        client.phone.save()

        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        client = self.__client

        if self.__success is None and self.__finalize:
            self.__success = exc_type is None

        if self.__success is not None:
            result = await self(functions.account.FinishTakeoutSessionRequest(self.__success))

            if not result:
                raise ValueError("Failed to finish the takeout.")

            self.session.takeout_id = None

        client.phone.takeout = False
        client.phone.save()


class TelegramClient(OpenteleClient):
    """Extended telegram client"""

    APIS = [
        API.TelegramDesktop,
        API.TelegramAndroid,
        API.TelegramAndroidX,
        API.TelegramIOS,
        API.TelegramMacOS,
    ]

    def __init__(self, phone: 'models.TypePhone', *args, **kwargs):
        self.phone = phone

        if self.phone.api is None:
            self.phone.api = self.APIS[random.randint(0, len(self.APIS) - 1)].Generate().__dict__

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

    class __ParticipantsIter(_ParticipantsIter):
        async def _load_next_chunk(self):
            if not self.requests:
                return True

            # Only care about the limit for the first request
            # (small amount of people, won't be aggressive).
            #
            # Most people won't care about getting exactly 12,345
            # members so it doesn't really matter not to be 100%
            # precise with being out of the offset/limit here.
            self.requests[0].limit = min(
                self.limit - self.requests[0].offset, _MAX_PARTICIPANTS_CHUNK_SIZE)

            if self.requests[0].offset > self.limit:
                return True

            if self.total is None:
                f = self.requests[0].filter
                if len(self.requests) > 1 or (
                    not isinstance(f, types.ChannelParticipantsRecent)
                    and (not isinstance(f, types.ChannelParticipantsSearch) or f.q)
                ):
                    # Only do an additional getParticipants here to get the total
                    # if there's a filter which would reduce the real total number.
                    # getParticipants is cheaper than getFull.
                    self.total = (await self.client(functions.channels.GetParticipantsRequest(
                        channel=self.requests[0].channel,
                        filter=types.ChannelParticipantsRecent(),
                        offset=0,
                        limit=1,
                        hash=0
                    ))).count

            results = [await self.client(request) for request in self.requests]

            for i in reversed(range(len(self.requests))):
                participants = results[i]
                if self.total is None:
                    # Will only get here if there was one request with a filter that matched all users.
                    self.total = participants.count
                if not participants.users:
                    self.requests.pop(i)
                    continue

                self.requests[i].offset += len(participants.participants)
                users = {user.id: user for user in participants.users}
                for participant in participants.participants:

                    if isinstance(participant, types.ChannelParticipantBanned):
                        if not isinstance(participant.peer, types.PeerUser):
                            # May have the entire channel banned. See #3105.
                            continue
                        user_id = participant.peer.user_id
                    else:
                        user_id = participant.user_id

                    user = users[user_id]
                    if not self.filter_entity(user) or user.id in self.seen:
                        continue
                    self.seen.add(user_id)
                    user = users[user_id]
                    user.participant = participant
                    self.buffer.append(user)

    def iter_participants(
            self: 'TelegramClient',
            entity: 'hints.EntityLike',
            limit: float = None,
            *,
            search: str = '',
            filter: 'types.TypeChannelParticipantsFilter' = None,
            aggressive: bool = False) -> _ParticipantsIter:
        return self.__ParticipantsIter(
            self,
            limit,
            entity=entity,
            filter=filter,
            search=search,
            aggressive=aggressive
        )

    async def _sync_dialogs(self):
        dialogs = await self.get_dialogs(limit=0)

        if dialogs.total >= 500:
            self.phone.status = models.Phone.FULL
            self.phone.save()

        async for dialog in self.iter_dialogs():
            if dialog.is_user:
                continue

            internal_id = telethon.utils.get_peer_id(dialog.dialog.peer)

            for chat in models.Chat.find(internal_id=internal_id):
                if not models.ChatPhone.find(chat=chat, phone=self.phone):
                    models.ChatPhone(chat=chat, phone=self.phone, is_using=True).save()

    async def start(self):
        try:
            if not self.is_connected():
                await self.connect()

            if await self.get_me() is not None:
                return self
        except telethon.errors.UserDeactivatedBanError as ex:
            self.phone.status = models.Phone.BAN
            self.phone.status_text = str(ex)
        else:
            self.phone.status = models.Phone.CREATED
            self.phone.status_text = "Unauthorized"

        self.phone.save()

        raise exceptions.UnauthorizedError(self.phone.status_text)

    async def wait_code(self):
        wait = 0

        while True:
            await asyncio.sleep(10)

            self.phone.reload()

            if self.phone.code is not None:
                return self.phone.code

            wait += 1

            if wait >= 10:  # Wait code for 10 minutes
                raise ValueError(
                    "Wait code timeout."
                )

    async def _start(self, force_sms=False, max_attempts=3):
        if not self.is_connected():
            await self.connect()

        me = await self.get_me()

        if me is not None:
            return self

        self.phone.number = telethon.utils.parse_phone(self.phone.number) or self.phone.number

        await self.send_code_request(self.phone.number, force_sms=force_sms)

        me = None
        attempts = 0

        while attempts < max_attempts:
            try:
                code = await self.wait_code()

                me = await self.sign_up(code, names.get_first_name(), names.get_last_name())

                break
            except telethon.errors.SessionPasswordNeededError:
                raise ValueError("Two-step verification is enabled for this account.")
            except (
                telethon.errors.PhoneCodeEmptyError,
                telethon.errors.PhoneCodeExpiredError,
                telethon.errors.PhoneCodeHashEmptyError,
                telethon.errors.PhoneCodeInvalidError
            ):
                self.phone.code = None
                self.phone.status_text = "Invalid code. Please try again."
                self.phone.save()

            attempts += 1
        else:
            raise RuntimeError(f'{max_attempts} consecutive sign-in attempts failed. Aborting')

        self.phone.internal_id = me.id
        self.phone.first_name = me.first_name
        self.phone.last_name = me.last_name
        self.phone.username = me.username
        self.phone.session = self.session.save()
        self.phone.status = models.Phone.READY
        self.phone.status_text = None
        self.phone.code = None
        self.phone.save()

        await self._sync_dialogs()

        return self

    def takeout(
            self,
            finalize: bool = True,
            *,
            contacts: bool = None,
            users: bool = None,
            chats: bool = None,
            megagroups: bool = None,
            channels: bool = None,
            files: bool = None,
            max_file_size: bool = None):
        """Override"""
        request_kwargs = dict(
            contacts=contacts,
            message_users=users,
            message_chats=chats,
            message_megagroups=megagroups,
            message_channels=channels,
            files=files,
            file_max_size=max_file_size
        )
        arg_specified = (arg is not None for arg in request_kwargs.values())

        if self.session.takeout_id is None or any(arg_specified):
            request = functions.account.InitTakeoutSessionRequest(
                **request_kwargs)
        else:
            request = None

        return _TakeoutClient(finalize, self, request)

    async def end_takeout(self, success: bool) -> bool:
        try:
            async with _TakeoutClient(True, self, None) as takeout:
                takeout.success = success
        except ValueError:
            return False
        return True

    async def resolve(self, string: 'str'):
        """Resolve entity from string"""

        username, is_join_chat = utils.parse_username(string)

        if is_join_chat:
            invite = await self(telethon.functions.messages.CheckChatInviteRequest(username))

            if isinstance(invite, telethon.types.ChatInvite):
                return invite
            elif isinstance(invite, telethon.types.ChatInviteAlready):
                return invite.chat
        elif username:
            return await self.get_entity(username)

        raise ValueError(f"Cannot find any entity corresponding to '{string}' in {self}.")

    async def join(self, string: 'str'):
        """Join to chat by phone"""

        username, is_join_chat = utils.parse_username(string)

        if is_join_chat:
            invite = await self(telethon.functions.messages.CheckChatInviteRequest(username))

            if isinstance(invite, telethon.types.ChatInviteAlready):
                return invite.chat
            else:
                updates = await self(telethon.functions.messages.ImportChatInviteRequest(username))

                return updates.chats[-1]
        elif username:
            updates = await self(telethon.functions.channels.JoinChannelRequest(username))

            return updates.chats[-1]

        raise ValueError(f"Cannot find any entity corresponding to '{string}' in {self}.")

    async def get_messages_count(self, entity: 'hints.EntityLike'):
        messages = await self.get_messages(entity, limit=0)

        return messages.total

    async def get_participants_count(self, entity: 'hints.EntityLike'):
        if entity.participants_count is None:
            try:
                participants = await self.get_participants(entity, limit=0)

                return participants.total
            except (
                telethon.errors.ChannelPrivateError,
                telethon.errors.ChatAdminRequiredError
            ):
                pass

        return entity.participants_count or 0

    async def download_media(self, media, loc, file_size, extension):
        chunk_number = 0
        chunk_size = downloads.MAX_CHUNK_SIZE
        total_chunks = math.ceil(file_size / chunk_size)

        async for chunk in self.iter_download(loc, chunk_size=chunk_size, file_size=file_size):
            ApiService().chunk(
                media._endpoint, media.id, str(loc.id) + extension, chunk,
                chunk_number, chunk_size, total_chunks, file_size
            )

            chunk_number += 1

    async def download_chat_photo(self, chat, entity):
        if isinstance(entity, telethon.types.Chat):
            entity = await self(
                telethon.functions.messages.GetFullChatRequest(
                    chat_id=entity.id
                )
            )
        elif isinstance(entity, telethon.types.Channel):
            entity = await self(
                telethon.functions.channels.GetFullChannelRequest(
                    channel=entity
                )
            )

        photo = entity.full_chat.chat_photo

        media = models.ChatMedia(internal_id=photo.id, chat=chat, date=photo.date.isoformat()).save()

        if media.path is None:
            loc, file_size, extension = utils.get_photo_location(photo)

            await self.download_media(media, loc, file_size, extension)


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
                      params={"filename": filename, "chunk_number": chunk_number, "chunk_size": chunk_size})
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
                         params={"filename": filename, "chunk_number": chunk_number, "total_chunks": total_chunks,
                                 "chunk_size": chunk_size, "total_size": total_size}, files={"chunk": chunk})

    def send(self, method: 'str', endpoint: 'str', path: 'str', body: 'dict' = None, params: 'dict' = None,
             files: 'dict' = None) -> 'dict | list[dict] | None':
        """Send request to API"""

        try:
            r = requests.request(
                method,
                os.environ['CELERY_API_URL'] + f"/{endpoint}/{path}",
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


def get_photo_location(photo):
    # Include video sizes here (but they may be None so provide an empty list)
    size = utils.TelegramClient._get_thumb(photo.sizes + (photo.video_sizes or []), -1)
    if not size or isinstance(size, telethon.types.PhotoSizeEmpty):
        return

    extension = '.mp4' if isinstance(size, telethon.types.VideoSize) else '.jpg'

    if isinstance(size, (telethon.types.PhotoCachedSize, telethon.types.PhotoStrippedSize)):
        # TODO: Решить как качать кэшированные
        # return telethon.utils._download_cached_photo_size(size, file)
        return

    if isinstance(size, telethon.types.PhotoSizeProgressive):
        file_size = max(size.sizes)
    else:
        file_size = size.size

    loc = telethon.types.InputPhotoFileLocation(
        id=photo.id,
        access_hash=photo.access_hash,
        file_reference=photo.file_reference,
        thumb_size=size.type
    )

    return loc, file_size, extension


def get_document_location(document):
    file_size = document.size

    extension = telethon.utils.get_extension(document)

    loc = telethon.types.InputDocumentFileLocation(
        id=document.id,
        access_hash=document.access_hash,
        file_reference=document.file_reference,
        thumb_size=''
    )

    return loc, file_size, extension
