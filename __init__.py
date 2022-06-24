from abc import abstractmethod
from datetime import datetime
import os
import string
import re
import asyncio
import random
import names
import telethon
import telethon.sessions
from telethon.tl.types import PhotoSize
from celery import Celery
from celery.utils.log import get_task_logger
from celery.result import ResultBase
from . import models
from . import utils
from . import exceptions


app = Celery(
    'telegram-parser',
    broker=os.environ['CELERY_BROKER'],
    backend=os.environ['CELERY_BROKER'],
    namespace="CELERY"
)


logger = get_task_logger(__name__)


class Task(app.Task):
    @abstractmethod
    def run(self, *args, **kswargs):
        """Start the task work"""

        raise NotImplementedError


class ParseBaseTask(Task):
    @staticmethod
    async def __set_member(client, tg_user: 'telethon.types.User') -> 'models.TypeMember':
        """Create 'Member' from telegram entity"""

        new_member = {
            "internal_id": tg_user.id,
            "username": tg_user.username,
            "first_name": tg_user.first_name,
            "last_name": tg_user.last_name,
            "phone": tg_user.phone
        }

        try:
            full_user: 'telethon.types.UserFull' = await client(
                telethon.functions.users.GetFullUserRequest(tg_user.id)
            )
        except:
            pass
        else:
            new_member["username"] = full_user.user.username
            new_member["first_name"] = full_user.user.first_name
            new_member["last_name"] = full_user.user.last_name
            new_member["phone"] = full_user.user.phone
            new_member["about"] = full_user.about

        member = models.Member(**new_member).save()

        mm_t = app.send_task(
            "MemberMediaTask",
            args=[client.phone.id, member.id, {"id": tg_user.id, "access_hash": tg_user.access_hash}],
            queue='low_prio'
        )

        return member, mm_t

    @staticmethod
    def __set_chat_member(chat: 'models.TypeChat', member: 'models.TypeMember',
                          participant=None) -> 'models.TypeChatMember':
        """Create 'ChatMember' from telegram entity"""

        new_chat_member = {"chat": chat, "member": member}

        if isinstance(participant, (telethon.types.ChannelParticipant, telethon.types.ChatParticipant)):
            new_chat_member["date"] = participant.date.isoformat()
        else:
            new_chat_member["isLeft"] = True

        return models.ChatMember(**new_chat_member).save()

    @staticmethod
    def __set_chat_member_role(chat_member: 'models.TypeChatMember',
                               participant=None) -> 'models.TypeChatMemberRole':
        """Create 'ChatMemberRole' from telegram entity"""

        new_chat_member_role = {"member": chat_member}

        if isinstance(participant, (telethon.types.ChannelParticipantAdmin, telethon.types.ChatParticipantAdmin)):
            new_chat_member_role["title"] = (participant.rank if participant.rank is not None else "Администратор")
            new_chat_member_role["code"] = "admin"
        elif isinstance(participant, (telethon.types.ChannelParticipantCreator, telethon.types.ChatParticipantCreator)):
            new_chat_member_role["title"] = (participant.rank if participant.rank is not None else "Создатель")
            new_chat_member_role["code"] = "creator"
        else:
            new_chat_member_role["title"] = "Участник"
            new_chat_member_role["code"] = "member"

        return models.ChatMemberRole(**new_chat_member_role).save()

    @classmethod
    async def _handle_user(cls, client: 'utils.TypeTelegramClient', chat: 'models.TypeChat',
                           tg_user: 'telethon.types.TypeUser', participant=None):
        """Handle telegram user"""

        if tg_user.is_self:
            return None, None, None, None

        member, mm_t = await cls.__set_member(client, tg_user)
        chat_member = cls.__set_chat_member(chat, member, participant)
        chat_member_role = cls.__set_chat_member_role(chat_member, participant)

        return member, mm_t, chat_member, chat_member_role

    @classmethod
    async def _handle_links(cls, client: 'utils.TelegramClient', text):
        """Handle links from message text"""

        subs = []

        for link in re.finditer(utils.LINK_RE, text):
            _link = link.group()
            username, is_join_chat = utils.parse_username(_link)

            if not username:
                continue

            if not is_join_chat:
                try:
                    tg_entity: 'telethon.types.TypeChat | telethon.types.User' = await client.get_entity(username)

                    if isinstance(tg_entity, telethon.types.User):
                        member, mm_t = await cls.__set_member(client, tg_entity)

                        subs.append(mm_t)

                        continue

                    models.Chat(link=_link, internal_id=tg_entity.id, title=tg_entity.title, is_available=False).save()

                    logger.info(f"New entity from link {_link} created.")

                except (ValueError, exceptions.RequestException, telethon.errors.RPCError):
                    continue

        return subs

    @staticmethod
    def _get_fwd(fwd_from):
        """Returns thuple of forwarded from information"""

        if fwd_from is not None:
            fwd_from_id = None

            if fwd_from.from_id is not None:
                if isinstance(fwd_from.from_id, telethon.types.PeerChannel):
                    fwd_from_id = fwd_from.from_id.channel_id
                elif isinstance(fwd_from.from_id, telethon.types.PeerUser):
                    fwd_from_id = fwd_from.from_id.user_id

            return fwd_from_id, fwd_from.from_name if fwd_from.from_name is not None else "Неизвестно"

        return None, None

    @classmethod
    async def _handle_message_media(cls, client, message, tg_message):
        client.download_media

        if isinstance(tg_message.media, telethon.types.MessageMediaPhoto):
            entity = tg_message.media.photo
            _size = next(
                ((size.type, size.size) for size in entity.sizes if isinstance(size, PhotoSize)),
                ('', None)
            )
            size = _size[1]
            extension = telethon.utils.get_extension(entity)
            date = entity.date.isoformat()
            entity = telethon.types.InputPhotoFileLocation(
                id=entity.id,
                access_hash=entity.access_hash,
                file_reference=entity.file_reference,
                thumb_size=_size[0]
            )
        elif isinstance(tg_message.media, telethon.types.MessageMediaDocument):
            entity = tg_message.media.document
            size = entity.size
            extension = telethon.utils.get_extension(entity)
            date = entity.date.isoformat()
            entity = telethon.types.InputDocumentFileLocation(
                id=entity.id,
                access_hash=entity.access_hash,
                file_reference=entity.file_reference,
                thumb_size=''
            )
        # TODO:
        # elif isinstance(tg_message.media, telethon.types.MessageMediaPoll):
        #     pass
        # elif isinstance(tg_message.media, telethon.types.MessageMediaVenue):
        #     pass
        # elif isinstance(tg_message.media, telethon.types.MessageMediaContact):
        #     pass
        else:
            return

        media = models.MessageMedia(internal_id=entity.id, message=message, date=date)
        media.save()

        await media.upload(client, entity, size, extension)

    @classmethod
    async def _handle_message(cls, chat: 'models.TypeChat', client, tg_message: 'telethon.types.TypeMessage'):
        """Handle telegram message"""

        subs = []

        fwd_from_id, fwd_from_name = cls._get_fwd(tg_message.fwd_from)

        chat_member = None
        reply_to = None

        if isinstance(tg_message.from_id, telethon.types.PeerUser):
            user: 'telethon.types.TypeUser' = await client.get_entity(tg_message.from_id)

            member, mm_t, chat_member, chat_member_role = await cls._handle_user(client, chat, user)

            subs.append(mm_t)

        if tg_message.reply_to is not None:
            reply_to = models.Message(internal_id=tg_message.reply_to.reply_to_msg_id, chat=chat)
            reply_to.save()

        if tg_message.replies is not None:
            try:
                replies = await client(
                    telethon.tl.functions.messages.GetRepliesRequest(
                        tg_message.peer_id, tg_message.id, 0, None, 0, 0, 0, 0, 0
                    )
                )

                for reply in replies.messages:
                    reply: 'telethon.types.TypeMessage'

                    subs += await cls._handle_message(chat, client, reply)
            except Exception as ex:
                logger.exception(ex)

        message = models.Message(
            internal_id=tg_message.id,
            text=tg_message.message,
            chat=chat,
            member=chat_member,
            reply_to=reply_to,
            is_pinned=tg_message.pinned,
            forwarded_from_id=fwd_from_id,
            forwarded_from_name=fwd_from_name,
            grouped_id=tg_message.grouped_id,
            date=tg_message.date.isoformat()
        )
        message.save()

        if tg_message.media is not None:
            await cls._handle_message_media(client, message, tg_message)

        return subs

    @staticmethod
    def before_start(task_id, args, kwargs):
        try:
            chat_task = models.ChatTask(id=task_id).reload()
        except exceptions.RequestException as ex:
            logger.error(f"Error occurred while getting current task from API. Exception: {ex}")

            return

        chat_task.status = models.ChatTask.IN_PROGRESS_STATUS
        chat_task.status_text = None
        chat_task.started_at = datetime.now().isoformat()
        chat_task.save()

    @staticmethod
    def on_success(retval, task_id, args, kwargs):
        try:
            chat_task = models.ChatTask(id=task_id).reload()
        except exceptions.RequestException as ex:
            logger.error(f"Error occurred while getting current task from API. Exception: {ex}")

            return

        chat_task.status = models.ChatTask.SUCCESED_STATUS
        chat_task.status_text = None
        chat_task.ended_at = datetime.now().isoformat()
        chat_task.save()

    @staticmethod
    def on_failure(exc, task_id, args, kwargs, einfo):
        try:
            chat_task = models.ChatTask(id=task_id).reload()
        except exceptions.RequestException as ex:
            logger.error(f"Error occurred while getting current task from API. Exception: {ex}")

            return

        chat_task.status = models.ChatTask.FAILED_STATUS
        chat_task.status_text = str(exc)
        chat_task.ended_at = datetime.now().isoformat()
        chat_task.save()


class PhoneAuthorizationTask(Task):
    name = "PhoneAuthorizationTask"
    queue = "high_prio"

    async def _sync_dialogs(self, client, phone: 'models.TypePhone'):
        dialogs = await client.get_dialogs(limit=0)

        if dialogs.total >= 500:
            phone.status = models.Phone.FULL
            phone.save()

        async for dialog in client.iter_dialogs():
            if dialog.is_user:
                continue

            internal_id = telethon.utils.get_peer_id(dialog.dialog.peer)

            for chat in models.Chat.find(internal_id=internal_id):
                if not models.ChatPhone.find(chat=chat, phone=phone):
                    models.ChatPhone(chat=chat, phone=phone, is_using=True).save()

    async def _run(self, phone: 'models.TypePhone'):
        client = utils.TelegramClient(phone)

        if not client.is_connected():
            try:
                await client.connect()
            except OSError as ex:
                logger.critical(f"Unable to connect client. Exception: {ex}")

                return f"{ex}"

        code_hash = None

        while True:
            if not await client.is_user_authorized():
                try:
                    if phone.code is not None and code_hash is not None:
                        try:
                            await client.sign_in(phone.number, phone.code, phone_code_hash=code_hash)
                        except telethon.errors.PhoneNumberUnoccupiedError:
                            await asyncio.sleep(random.randint(2, 5))

                            if phone.first_name is None or phone.first_name == '':
                                phone.first_name = names.get_first_name()

                            if phone.last_name is None or phone.last_name == '':
                                phone.last_name = names.get_last_name()

                            await client.sign_up(
                                phone.code,
                                phone.first_name,
                                phone.last_name,
                                phone_code_hash=code_hash
                            )
                        except (
                            telethon.errors.PhoneCodeEmptyError,
                            telethon.errors.PhoneCodeExpiredError,
                            telethon.errors.PhoneCodeHashEmptyError,
                            telethon.errors.PhoneCodeInvalidError
                        ) as ex:
                            logger.warning(f"Code invalid. Exception {ex}")

                            phone.code = None
                            phone.status_text = "Code invalid"
                            phone.save()

                            continue

                        me = await client.get_me()

                        phone.internal_id = me.id
                        phone.first_name = me.first_name
                        phone.last_name = me.last_name
                        phone.username = me.username
                        phone.session = client.session.save()
                        phone.status = models.Phone.READY
                        phone.status_text = None
                        phone.code = None
                        phone.save()

                        await self._sync_dialogs(client, phone)

                        break
                    elif code_hash is None:
                        try:
                            sent = await client.send_code_request(phone=phone.number)

                            code_hash = sent.phone_code_hash
                        except telethon.errors.rpcerrorlist.FloodWaitError as ex:
                            logger.warning(f"Flood exception. Sleep {ex.seconds}.")

                            phone.status = models.Phone.FLOOD
                            phone.status_text = str(ex)
                            phone.save()

                            await asyncio.sleep(ex.seconds)

                            continue
                    else:
                        await asyncio.sleep(10)

                        phone.reload()
                except telethon.errors.FloodWaitError as ex:
                    logger.warning(f"Phone authorization must wait {ex.seconds}. Exception {ex}.")

                    await asyncio.sleep(ex.seconds)

                    continue
                except telethon.errors.RPCError as ex:
                    logger.error(f"Cannot authentificate. Exception: {ex}")

                    phone.session = None
                    phone.status = models.Phone.BAN
                    phone.status_text = str(ex)
                    phone.code = None
                    phone.save()

                    return f"{ex}"
            else:
                break

        return True

    def run(self, phone_id):
        try:
            phone = models.Phone(id=phone_id).reload()
        except exceptions.RequestException as ex:
            return f"{ex}"

        return asyncio.run(self._run(phone))


app.register_task(PhoneAuthorizationTask())


class ChatResolveTask(Task):
    name = "ChatResolveTask"
    queue = "high_prio"

    @staticmethod
    async def __get_avatar(client, chat, photo):
        if photo is None or isinstance(photo, telethon.types.PhotoEmpty):
            return

        if isinstance(photo, telethon.types.ChatPhoto):
            return

        media = models.ChatMedia(internal_id=photo.id, chat=chat, date=photo.date.isoformat()).save()

        info = telethon.utils._get_file_info(photo)
        extension = telethon.utils.get_extension(photo)

        await media.upload(client, info.location, info.size, extension)

    async def __resolve(self, client, string):
        """Resolve entity from string"""

        username, is_join_chat = utils.parse_username(string)

        if is_join_chat:
            invite = await client(telethon.functions.messages.CheckChatInviteRequest(username))

            if isinstance(invite, telethon.types.ChatInvite):
                return invite
            elif isinstance(invite, telethon.types.ChatInviteAlready):
                return invite.chat
        elif username:
            return await client.get_entity(username)

        raise ValueError(f"Cannot find any entity corresponding to '{string}' in {self}.")

    async def _run(self, chat: 'models.TypeChat', phones: 'list[models.TypePhone]'):
        for phone in phones:
            try:
                async with utils.TelegramClient(phone) as client:
                    try:
                        tg_chat = await self.__resolve(client, chat.link)
                    except telethon.errors.FloodWaitError as ex:
                        logger.warning(f"Chat resolve must wait {ex.seconds}. Exception {ex}.")

                        phone.status = models.Phone.FLOOD
                        phone.status_text = str(ex)
                        phone.save()

                        continue
                    except (ValueError, telethon.errors.RPCError) as ex:
                        logger.error(f"Chat resolve exception. Exception: {ex}.")

                        chat.status = models.Chat.FAILED
                        chat.status_text = str(ex)
                        chat.save()

                        return f"{ex}"
                    else:
                        if isinstance(tg_chat, telethon.types.User):
                            logger.warning("User link.")

                            chat.status = models.Chat.FAILED
                            chat.status_text = "User link."
                            chat.save()

                            return False

                        if isinstance(tg_chat, telethon.types.ChatInvite):
                            logger.warning("Chat is available, but need to join.")

                            chat.status_text = "Chat is available, but need to join."
                        else:
                            chat.internal_id = telethon.utils.get_peer_id(tg_chat)
                            chat.status_text = None

                            messages = await client.get_messages(tg_chat, limit=0)
                            chat.total_messages = messages.total

                        chat.title = tg_chat.title
                        chat.total_members = tg_chat.participants_count or 0
                        chat.status = models.Chat.AVAILABLE
                        chat.save()

                        # await self.__get_avatar(client, chat, tg_chat.photo)

                        return True
            except exceptions.UnauthorizedError as ex:
                logger.critical(f"{ex}")

                continue

        return False

    def run(self, chat_id):
        try:
            chat = models.Chat(id=chat_id).reload()
        except exceptions.RequestException as ex:
            return f"{ex}"

        try:
            phones = models.Phone.find(status=models.Phone.READY, parser=chat.parser.id)
        except exceptions.RequestException as ex:
            return f"{ex}"

        return asyncio.run(self._run(chat, phones))


app.register_task(ChatResolveTask())


class JoinChatTask(Task):
    name = "JoinChatTask"
    queue = "high_prio"

    async def __join(self, client, string: 'str'):
        """Join to chat by phone"""

        username, is_join_chat = utils.parse_username(string)

        if is_join_chat:
            invite = await client(telethon.functions.messages.CheckChatInviteRequest(username))

            if isinstance(invite, telethon.types.ChatInviteAlready):
                return invite.chat
            else:
                updates = await client(telethon.functions.messages.ImportChatInviteRequest(username))

                return updates.chats[-1]
        elif username:
            updates = await client(telethon.functions.channels.JoinChannelRequest(username))

            return updates.chats[-1]

        raise ValueError(f"Cannot find any entity corresponding to '{string}' in {self}.")

    async def _run(self, chat: 'models.TypeChat', phone: 'models.TypePhone'):
        while True:
            try:
                async with utils.TelegramClient(phone) as client:
                    try:
                        dialogs = await client.get_dialogs(limit=0)

                        if dialogs.total >= 500:
                            phone.status = models.Phone.FULL
                            phone.save()

                            break

                        tg_chat = await self.__join(client, chat.link)
                    except telethon.errors.FloodWaitError as ex:
                        logger.warning(f"Chat wiring for phone {phone.id} must wait {ex.seconds}.")

                        phone.status = models.Phone.FLOOD
                        phone.status_text = str(ex)
                        phone.save()

                        await asyncio.sleep(ex.seconds)

                        continue
                    except telethon.errors.ChannelsTooMuchError as ex:
                        phone.status = models.Phone.FULL
                        phone.status_text = str(ex)
                        phone.save()

                        return f"{ex}"
                    except telethon.errors.UserDeactivatedBanError as ex:
                        logger.critical(f"Chat not available for phone {phone.id}. Exception {ex}")

                        phone.status = models.Phone.BAN
                        phone.status_text = str(ex)
                        phone.save()

                        return f"{ex}"
                    except (ValueError, telethon.errors.RPCError) as ex:
                        logger.error(f"Chat not available. Exception {ex}.")

                        chat.status = models.Chat.FAILED
                        chat.status_text = str(ex)
                        chat.save()

                        return f"{ex}"
                    else:
                        models.ChatPhone(chat=chat, phone=phone, is_using=True).save()

                        internal_id = telethon.utils.get_peer_id(tg_chat)
                        chat.internal_id = internal_id

                        messages = await client.get_messages(tg_chat, limit=0)
                        chat.total_messages = messages.total

                        chat.total_members = tg_chat.participants_count or 0
                        chat.title = tg_chat.title
                        chat.save()

                        await asyncio.sleep(random.randint(2, 5))

                        messages = await client.get_messages(tg_chat, limit=3)

                        for tg_message in messages:
                            models.Message(
                                internal_id=tg_message.id,
                                text=tg_message.message,
                                chat=chat,
                                date=tg_message.date.isoformat()
                            ).save()

                        return True
            except exceptions.UnauthorizedError as ex:
                logger.critical(f"{ex}")

                return f"{ex}"

        return False

    def run(self, chat_id: 'str', phone_id: 'str'):
        try:
            chat = models.Chat(id=chat_id).reload()
        except exceptions.RequestException as ex:
            return f"{ex}"

        try:
            phone = models.Phone(id=phone_id).reload()
        except exceptions.RequestException as ex:
            return f"{ex}"

        return asyncio.run(self._run(chat, phone))


app.register_task(JoinChatTask())


class ChatMediaTask(Task):
    name = "ChatMediaTask"
    queue = "low_prio"

    async def _run(self, chat: 'models.TypeChat', chat_phones: 'list[models.TypeChatPhone]'):
        id, peer = telethon.utils.resolve_id(chat.internal_id)

        for chat_phone in chat_phones:
            try:
                async with utils.TelegramClient(chat_phone.phone) as client:
                    while True:
                        try:
                            async for photo in client.iter_profile_photos(peer):
                                photo: 'telethon.types.TypePhoto'

                                media = models.ChatMedia(
                                    internal_id=photo.id,
                                    chat=chat,
                                    date=photo.date.isoformat()
                                ).save()

                                size = next(
                                    ((size.type, size.size) for size in photo.sizes if isinstance(size, PhotoSize)),
                                    ('', None)
                                )
                                loc = telethon.types.InputPhotoFileLocation(
                                    id=photo.id,
                                    access_hash=photo.access_hash,
                                    file_reference=photo.file_reference,
                                    thumb_size=size[0]
                                )
                                extension = telethon.utils.get_extension(photo)

                                await media.upload(client, loc, size[1], extension)
                            else:
                                return True
                        except telethon.errors.FloodWaitError as ex:
                            logger.warning(f"Chat media download must wait. Exception {ex}")

                            await asyncio.sleep(ex.seconds)

                            continue
                        except (ValueError, telethon.errors.RPCError) as ex:
                            logger.error(f"Can't get chat {chat.id} media. Exception {ex}")

                            return f"{ex}"
            except exceptions.UnauthorizedError as ex:
                logger.critical(f"{ex}")

                chat_phone.is_using = False
                chat_phone.save()

                continue

        return False

    def run(self, chat_id):
        try:
            chat = models.Chat(id=chat_id).reload()
        except exceptions.RequestException as ex:
            return f"{ex}"

        try:
            chat_phones = models.ChatPhone.find(chat=chat_id, is_using=True)

            if not len(chat_phones):
                return "Chat phones not found."
        except exceptions.RequestException as ex:
            return f"{ex}"

        return asyncio.run(self._run(chat, chat_phones))


app.register_task(ChatMediaTask())


class MemberMediaTask(Task):
    name = "MemberMediaTask"
    queue = "low_prio"

    async def _run(self, phone: 'models.TypePhone', member: 'models.TypeMember', tg_user: 'telethon.types.TypeUser'):
        try:
            async with utils.TelegramClient(phone) as client:
                while True:
                    try:
                        async for photo in client.iter_profile_photos(tg_user):
                            photo: 'telethon.types.TypePhoto'

                            media = models.MemberMedia(
                                internal_id=photo.id,
                                member=member,
                                date=photo.date.isoformat()
                            ).save()

                            size = next(
                                ((size.type, size.size) for size in photo.sizes if isinstance(size, PhotoSize)),
                                ('', None)
                            )
                            tg_media = telethon.types.InputPhotoFileLocation(
                                id=photo.id,
                                access_hash=photo.access_hash,
                                file_reference=photo.file_reference,
                                thumb_size=size[0]
                            )
                            extension = telethon.utils.get_extension(photo)

                            await media.upload(client, tg_media, size[1], extension)
                        else:
                            return True
                    except telethon.errors.FloodWaitError as ex:
                        logger.warning(f"Member media download must wait. Exception {ex}")

                        await asyncio.sleep(ex.seconds)

                        continue
                    except (ValueError, telethon.errors.RPCError) as ex:
                        logger.error(f"Can't get member {member.id} media. Exception {type(ex)} {ex}")

                        return f"{ex}"
        except exceptions.UnauthorizedError as ex:
            logger.critical(f"{ex}")

            return f"{ex}"

        return False

    def run(self, phone_id, member_id, tg_user):
        try:
            phone = models.Phone(id=phone_id).reload()
        except exceptions.RequestException as ex:
            return f"{ex}"

        try:
            member = models.Member(id=member_id).reload()
        except exceptions.RequestException as ex:
            return f"{ex}"

        tg_user = telethon.types.User(**tg_user)

        return asyncio.run(self._run(phone, member, tg_user))


app.register_task(MemberMediaTask())


class ParseMembersTask(ParseBaseTask):
    name = "ParseMembersTask"
    queue = "high_prio"

    @classmethod
    async def _get_members(cls, client: 'utils.TelegramClient', chat: 'models.TypeChat'):
        """Iterate telegram chat members and save to API"""

        # search = string.digits + string.ascii_lowercase + string.punctuation + ' ♥абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
        search = string.ascii_lowercase + '♥абвгдеёжзийклмнопрстуфхцчшщъыьэюя'

        subs = []

        async for user in client.iter_participants(entity=chat.internal_id, search=search, aggressive=True):
            member, mm_t, chat_member, chat_member_role = await cls._handle_user(client, chat, user, user.participant)

            if mm_t is not None:
                subs.append(mm_t)
        else:
            logger.info("Members data download success.")

        return subs

    async def _run(self, chat: 'models.TypeChat', chat_phones: 'list[models.TypeChatPhone]'):
        for chat_phone in chat_phones:
            phone = chat_phone.phone

            try:
                async with utils.TelegramClient(phone) as client:
                    subs = await self._get_members(client, chat)

                    [sub.get(disable_sync_subtasks=False) for sub in subs if isinstance(sub, ResultBase)]

                    return True
            except exceptions.UnauthorizedError as ex:
                logger.critical(f"{ex}")

                chat_phone.is_using = False
                chat_phone.save()

                continue

        raise Exception("Chat doesn't have available phones.")

    def run(self, chat_id):
        try:
            chat = models.Chat(id=chat_id).reload()
        except exceptions.RequestException as ex:
            return f"{ex}"

        try:
            chat_phones = models.ChatPhone.find(chat=chat.id, is_using=True)

            if not len(chat_phones):
                return "Chat phones not found."
        except exceptions.RequestException as ex:
            return f"{ex}"

        return asyncio.run(self._run(chat, chat_phones))


app.register_task(ParseMembersTask())


class ParseMessagesTask(ParseBaseTask):
    name = "ParseMessagesTask"
    queue = "low_prio"

    async def _get_messages(self, chat: 'models.TypeChat', client):
        """Iterate telegram chat messages and save to API"""

        last_messages = models.Message.find(chat=chat.id, ordering="-internal_id", limit=1)
        max_id = last_messages[0].internal_id if last_messages else 0

        subs = []

        async for tg_message in client.iter_messages(chat.internal_id, max_id=max_id):
            if not isinstance(tg_message, telethon.types.Message):
                continue

            subs += await self._handle_links(client, tg_message.message)

            subs += await self._handle_message(chat, client, tg_message)
        else:
            logger.info("Messages download success.")

        return subs

    async def _run(self, chat: 'models.TypeChat', chat_phones: 'list[models.TypeChatPhone]'):
        for chat_phone in chat_phones:
            phone = chat_phone.phone

            try:
                async with utils.TelegramClient(phone) as client:
                    try:
                        subs = await self._get_messages(chat, client)
                    except telethon.errors.FloodWaitError as ex:
                        logger.warning(f"Messages request must wait {ex.seconds} seconds.")

                        await asyncio.sleep(ex.seconds)

                        continue
                    else:
                        [sub.get(disable_sync_subtasks=False) for sub in subs if isinstance(sub, ResultBase)]

                        return True
            except exceptions.UnauthorizedError as ex:
                logger.critical(f"{ex}")

                chat_phone.is_using = False
                chat_phone.save()

                continue

        raise Exception("Chat doesn't have available phones.")

    def run(self, chat_id):
        try:
            chat = models.Chat(id=chat_id).reload()
        except exceptions.RequestException as ex:
            return f"{ex}"

        try:
            chat_phones = models.ChatPhone.find(chat=chat.id, is_using=True)

            if not len(chat_phones):
                return "Chat phones not found."
        except exceptions.RequestException as ex:
            return f"{ex}"

        return asyncio.run(self._run(chat, chat_phones))


app.register_task(ParseMessagesTask())


class MonitoringChatTask(ParseBaseTask):
    name = "MonitoringChatTask"
    queue = "high_prio"

    async def _run(self, chat: 'models.TypeChat', chat_phones: 'list[models.TypeChatPhone]'):
        for chat_phone in chat_phones:
            phone = chat_phone.phone

            try:
                async with utils.TelegramClient(phone) as client:
                    @client.on(telethon.events.chataction.ChatAction(chats=chat.internal_id))
                    async def handle_chat_action(event):
                        if event.user_added or event.user_joined or event.user_left or event.user_kicked:
                            async for user in event.get_users():
                                await self._handle_user(client, chat, user, user.participant)

                    @client.on(telethon.events.NewMessage(chats=chat.internal_id, incoming=True))
                    async def handle_new_message(event):
                        if not isinstance(event.message, telethon.types.Message):
                            return

                        await self._handle_links(client, event.message.message)

                        await self._handle_message(chat, client, event.message)

                    client.run_until_disconnected()
            except exceptions.UnauthorizedError as ex:
                logger.critical(f"{ex}")

                chat_phone.is_using = False
                chat_phone.save()

                continue

        return False

    def run(self, chat_id):
        try:
            chat = models.Chat(id=chat_id).reload()
        except exceptions.RequestException as ex:
            return f"{ex}"

        try:
            chat_phones = models.ChatPhone.find(chat=chat.id, is_using=True)

            if not len(chat_phones):
                return "Chat phones not found."
        except exceptions.RequestException as ex:
            return f"{ex}"

        return asyncio.run(self._run(chat, chat_phones))


app.register_task(MonitoringChatTask())
