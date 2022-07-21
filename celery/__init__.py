from abc import abstractmethod
import os
import string
import re
import asyncio
import telethon
import telethon.sessions
from celery import Celery
from celery.utils.log import get_task_logger
from . import models, utils, exceptions


app = celery.Celery('telegram-parser')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
app.conf.timezone = os.environ['CELERY_TIMEZONE']
app.conf.enable_utc = os.environ['CELERY_ENABLE_UTC']


logger = get_task_logger(__name__)


class Task(app.Task):
    @abstractmethod
    def run(self, *args, **kswargs):
        """Start the task work"""

        raise NotImplementedError


class BasePhoneTask(Task):
    @staticmethod
    def before_start(task_id, args, kwargs):
        try:
            phone_task = models.PhoneTask(id=task_id).reload()
        except exceptions.RequestException as ex:
            return

        phone_task.status = models.PhoneTask.STATUS_IN_PROGRESS
        phone_task.status_text = None
        phone_task.started_at = app.now().isoformat()
        phone_task.save()

    @staticmethod
    def on_success(retval, task_id, args, kwargs):
        try:
            phone_task = models.PhoneTask(id=task_id).reload()
        except exceptions.RequestException as ex:
            return

        phone_task.status = models.PhoneTask.STATUS_SUCCESED
        phone_task.status_text = None
        phone_task.ended_at = app.now().isoformat()
        phone_task.save()

    @staticmethod
    def on_failure(exc, task_id, args, kwargs, einfo):
        try:
            phone_task = models.PhoneTask(id=task_id).reload()
        except exceptions.RequestException as ex:
            return

        phone_task.status = models.PhoneTask.STATUS_FAILED
        phone_task.status_text = str(exc)
        phone_task.ended_at = app.now().isoformat()
        phone_task.save()


class BaseChatTask(Task):
    @classmethod
    async def _set_member_media(cls, client, member: 'models.TypeMember', tg_user: 'telethon.types.User'):
        try:
            async for photo in client.iter_profile_photos(tg_user):
                photo: 'telethon.types.TypePhoto'

                media = models.MemberMedia(
                    internal_id=photo.id,
                    member=member,
                    date=photo.date.isoformat()
                ).save()

                if media.path is None:
                    loc, file_size, extension = utils.get_photo_location(photo)

                    await client.download_media(media, loc, file_size, extension)
            else:
                return
        except telethon.errors.FloodWaitError as ex:
            logger.warning(f"Member media download must wait. Exception {ex}")

            await asyncio.sleep(ex.seconds)

            cls._set_member_media(client, member, tg_user)

    @classmethod
    async def _set_member(cls, client, tg_user: 'telethon.types.User') -> 'models.TypeMember':
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
        except Exception:
            pass
        else:
            new_member["username"] = full_user.user.username
            new_member["first_name"] = full_user.user.first_name
            new_member["last_name"] = full_user.user.last_name
            new_member["phone"] = full_user.user.phone
            new_member["about"] = full_user.about

        member = models.Member(**new_member).save()

        await cls._set_member_media(client, member, tg_user)

        return member

    @staticmethod
    def _set_chat_member(chat: 'models.TypeChat', member: 'models.TypeMember',
                         participant=None) -> 'models.TypeChatMember':
        """Create 'ChatMember' from telegram entity"""

        new_chat_member = {"chat": chat, "member": member}

        if isinstance(participant, (telethon.types.ChannelParticipant, telethon.types.ChatParticipant)):
            new_chat_member["date"] = participant.date.isoformat()
        else:
            new_chat_member["isLeft"] = True

        return models.ChatMember(**new_chat_member).save()

    @staticmethod
    def _set_chat_member_role(chat_member: 'models.TypeChatMember',
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
    async def _set_message_media(cls, client, message, tg_message):
        if isinstance(tg_message.media, telethon.types.MessageMediaPhoto):
            photo = tg_message.media.photo
            date = photo.date.isoformat()
            loc, file_size, extension = utils.get_photo_location(photo)
        elif isinstance(tg_message.media, telethon.types.MessageMediaDocument):
            document = tg_message.media.document
            date = document.date.isoformat()
            loc, file_size, extension = utils.get_document_location(document)
        # TODO:
        # elif isinstance(tg_message.media, telethon.types.MessageMediaPoll):
        #     pass
        # elif isinstance(tg_message.media, telethon.types.MessageMediaVenue):
        #     pass
        # elif isinstance(tg_message.media, telethon.types.MessageMediaContact):
        #     pass
        else:
            return

        media = models.MessageMedia(internal_id=loc.id, message=message, date=date).save()

        if media.path is None:
            await client.download_media(media, loc, file_size, extension)

    @classmethod
    async def set_chat_user(cls, client: 'utils.TypeTelegramClient', chat: 'models.TypeChat',
                            tg_user: 'telethon.types.TypeUser', participant=None):
        """Handle telegram user"""

        if tg_user.is_self:
            return None, None, None, None

        member = await cls._set_member(client, tg_user)
        chat_member = cls._set_chat_member(chat, member, participant)
        chat_member_role = cls._set_chat_member_role(chat_member, participant)

        return member, chat_member, chat_member_role

    @classmethod
    async def find_links(cls, text):
        """Handle links from message text"""

        for link in re.finditer(utils.LINK_RE, text):
            username, is_join_chat = utils.parse_username(link.group())

            if not username:
                continue

            models.Link(link=link.group()).save()

    @classmethod
    async def set_message(cls, client, chat: 'models.TypeChat', tg_message: 'telethon.types.TypeMessage'):
        """Handle telegram message"""

        if isinstance(tg_message.from_id, telethon.types.PeerUser):
            user: 'telethon.types.TypeUser' = await client.get_entity(tg_message.from_id)

            member, chat_member, chat_member_role = await cls.set_chat_user(client, chat, user)
        else:
            chat_member = models.ChatMember()

        if tg_message.reply_to is not None:
            reply_to = models.Message(internal_id=tg_message.reply_to.reply_to_msg_id, chat=chat).save()
        else:
            reply_to = models.Message()

        if tg_message.replies is not None:
            async for reply in client.iter_messages(tg_message.input_chat, reply_to=tg_message.id):
                if not isinstance(reply, telethon.types.Message):
                    continue

                await cls.find_links(reply.message)

                await cls.set_message(client, chat, reply)

        fwd_from_id, fwd_from_name = cls._get_fwd(tg_message.fwd_from)

        message = models.Message(
            internal_id=tg_message.id,
            text=tg_message.message,
            chat=chat,
            member=chat_member,
            reply_to=reply_to.id,
            is_pinned=tg_message.pinned,
            forwarded_from_id=fwd_from_id,
            forwarded_from_name=fwd_from_name,
            grouped_id=tg_message.grouped_id,
            date=tg_message.date.isoformat()
        )
        message.save()

        if tg_message.media is not None:
            await cls._set_message_media(client, message, tg_message)

    @staticmethod
    def before_start(task_id, args, kwargs):
        try:
            chat_task = models.ChatTask(id=task_id).reload()
        except exceptions.RequestException as ex:
            return

        chat_task.status = models.ChatTask.STATUS_IN_PROGRESS
        chat_task.status_text = None
        chat_task.started_at = app.now().isoformat()
        chat_task.save()

    @staticmethod
    def on_success(retval, task_id, args, kwargs):
        try:
            chat_task = models.ChatTask(id=task_id).reload()
        except exceptions.RequestException as ex:
            return

        chat_task.status = models.ChatTask.STATUS_SUCCESED
        chat_task.status_text = None
        chat_task.ended_at = app.now().isoformat()
        chat_task.save()

    @staticmethod
    def on_failure(exc, task_id, args, kwargs, einfo):
        try:
            chat_task = models.ChatTask(id=task_id).reload()
        except exceptions.RequestException as ex:
            return

        chat_task.status = models.ChatTask.STATUS_FAILED
        chat_task.status_text = str(exc)
        chat_task.ended_at = app.now().isoformat()
        chat_task.save()


class PhoneAuthorizationTask(BasePhoneTask):
    name = "PhoneAuthorizationTask"
    queue = "high_prio"

    async def _run(self, phone: 'models.TypePhone'):
        client = utils.TelegramClient(phone)

        try:
            await client._start()
        except (
            ValueError,
            RuntimeError,
            telethon.errors.RPCError
        ) as ex:
            phone.session = None
            phone.status = models.Phone.BAN
            phone.status_text = str(ex)
            phone.code = None
            phone.save()

            raise

        me = await client.get_me()

        signed, name = 'Signed in successfully as %s', telethon.utils.get_display_name(me)

        try:
            logger.info(signed, name)
        except UnicodeEncodeError:
            # Some terminals don't support certain characters
            logger.info(signed, name.encode('utf-8', errors='ignore')
                                    .decode('ascii', errors='ignore'))

        return True

    def run(self, phone_id):
        try:
            phone = models.Phone(id=phone_id).reload()
        except exceptions.RequestException as ex:
            return f"{ex}"

        return asyncio.run(self._run(phone))


app.register_task(PhoneAuthorizationTask())


class LinkResolveTask(BaseChatTask):
    name = "LinkResolveTask"
    queue = "high_prio"

    async def _run(self, link: 'models.TypeLink', phones: 'list[models.TypePhone]'):
        for phone in phones:
            try:
                async with utils.TelegramClient(phone) as client:
                    try:
                        tg_entity = await client.resolve(link.link)
                    except telethon.errors.FloodWaitError as ex:
                        logger.warning(f"Link resolve must wait {ex.seconds}. Exception {ex}.")

                        continue
                    except (ValueError, telethon.errors.RPCError) as ex:
                        link.status = models.Link.STATUS_FAILED
                        link.status_text = str(ex)
                        link.save()

                        raise ex
                    else:
                        if isinstance(tg_entity, telethon.types.User):
                            member = await super()._set_member(client, tg_entity)

                            link.__class__ = models.MemberLink
                            link.status = models.Link.STATUS_AVAILABLE
                            link.member = member
                            link.save()

                            return True

                        chat = models.Chat(title=tg_entity.title, status=models.Chat.STATUS_AVAILABLE)

                        if isinstance(tg_entity, telethon.types.ChatInvite):
                            logger.warning("Chat is available, but need to join.")

                            creator_id, chat_id, rand_int = telethon.utils.resolve_invite_link(link.link)
                            chat.internal_id = chat_id

                            chat.status_text = "Chat is available, but need to join."
                        else:
                            chat.internal_id = telethon.utils.get_peer_id(tg_entity)
                            chat.status_text = None

                            chat.total_messages = await client.get_messages_count(tg_entity)
                            chat.total_members = await client.get_participants_count(tg_entity)

                        chat.save()

                        link.__class__ = models.ChatLink
                        link.status = models.Link.STATUS_AVAILABLE
                        link.chat = chat
                        link.save()

                        if not isinstance(tg_entity, telethon.types.ChatInvite):
                            await client.download_chat_photo(chat, tg_entity)

                        return True
            except exceptions.UnauthorizedError as ex:
                logger.critical(f"{ex}")

                continue

        raise Exception("Available phones doesn't exist.")

    def run(self, link_id: 'str'):
        try:
            link = models.Link(id=link_id).reload()
        except exceptions.RequestException as ex:
            logger.error(f"{ex}")

            raise Exception("Can't get given link.")

        try:
            phones = models.Phone.find(status=models.Phone.READY, takeout=False)
        except exceptions.RequestException as ex:
            logger.error(f"{ex}")

            raise Exception("Can't get phones.")

        return asyncio.run(self._run(link, phones))


app.register_task(LinkResolveTask())


class JoinChatTask(BaseChatTask):
    name = "JoinChatTask"
    queue = "high_prio"

    async def _run(self, link: 'models.TypeChatLink', phone: 'models.TypePhone'):
        while True:
            async with utils.TelegramClient(phone) as client:
                try:
                    tg_entity = await client.join(link.link)
                except telethon.errors.FloodWaitError as ex:
                    logger.warning(f"Chat wiring for phone {phone.id} must wait {ex.seconds}.")

                    await asyncio.sleep(ex.seconds)

                    continue
                except telethon.errors.ChannelsTooMuchError as ex:
                    phone.status = models.Phone.FULL
                    phone.status_text = str(ex)
                    phone.save()

                    raise ex
                except (ValueError, telethon.errors.RPCError) as ex:
                    link.status = models.ChatLink.STATUS_FAILED
                    link.status_text = str(ex)
                    link.save()

                    raise ex
                else:
                    chat = link.chat

                    models.ChatPhone(chat=chat, phone=phone, is_using=True).save()

                    chat.internal_id = telethon.utils.get_peer_id(tg_entity)
                    chat.total_messages = await client.get_messages_count(tg_entity)
                    chat.total_members = await client.get_participants_count(tg_entity)
                    chat.title = tg_entity.title
                    chat.save()

                    await client.download_chat_photo(chat, tg_entity)

                    messages = await client.get_messages(tg_entity, limit=1)

                    for tg_message in messages:
                        await self.set_message(client, chat, tg_message)

                    return True

    def run(self, link_id: 'str', phone_id: 'str'):
        try:
            link = models.ChatLink(id=link_id).reload()
        except exceptions.RequestException as ex:
            logger.error(f"{ex}")

            raise Exception("Can't get given link.")

        try:
            phone = models.Phone(id=phone_id).reload()
        except exceptions.RequestException as ex:
            logger.error(f"{ex}")

            raise Exception("Can't get given phone.")

        return asyncio.run(self._run(link, phone))


app.register_task(JoinChatTask())


class ChatMediaTask(Task):
    name = "ChatMediaTask"
    queue = "low_prio"

    async def _run(self, chat: 'models.TypeChat', chat_phones: 'list[models.TypeChatPhone]'):
        for chat_phone in chat_phones:
            try:
                async with utils.TelegramClient(chat_phone.phone) as client:
                    id, peer = telethon.utils.resolve_id(chat.internal_id)

                    while True:
                        try:
                            async for photo in client.iter_profile_photos(peer):
                                photo: 'telethon.types.TypePhoto'

                                media = models.ChatMedia(
                                    internal_id=photo.id,
                                    chat=chat,
                                    date=photo.date.isoformat()
                                ).save()

                                if media.path is None:
                                    loc, file_size, extension = utils.get_photo_location(photo)

                                    await client.download_media(media, loc, file_size, extension)
                            else:
                                return
                        except telethon.errors.FloodWaitError as ex:
                            logger.warning(f"Chat media download must wait. Exception {ex}")

                            await asyncio.sleep(ex.seconds)

                            continue
            except exceptions.UnauthorizedError as ex:
                logger.critical(f"{ex}")

                chat_phone.is_using = False
                chat_phone.save()

                continue

        raise Exception("Chat doesn't have available phones, try again later.")

    def run(self, chat_id):
        try:
            chat = models.Chat(id=chat_id).reload()
        except exceptions.RequestException as ex:
            logger.error(f"{ex}")

            raise Exception("Can't get given chat.")

        try:
            chat_phones = models.ChatPhone.find(chat=chat_id, is_using=True)
        except exceptions.RequestException as ex:
            logger.error(f"{ex}")

            raise Exception("Can't get chat wired phones.")

        return asyncio.run(self._run(chat, chat_phones))


app.register_task(ChatMediaTask())


class ParseMembersTask(BaseChatTask):
    name = "ParseMembersTask"
    queue = "high_prio"

    @classmethod
    async def _get_members(cls, client: 'utils.TelegramClient', chat: 'models.TypeChat'):
        """Iterate telegram chat members and save to API"""

        # search = string.digits + string.ascii_lowercase + string.punctuation + ' ♥абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
        search = string.ascii_lowercase + '♥абвгдеёжзийклмнопрстуфхцчшщъыьэюя'

        async for user in client.iter_participants(entity=chat.internal_id, search=search, aggressive=True):
            await cls.set_chat_user(client, chat, user, user.participant)
        else:
            logger.info("Members data download success.")

    async def _run(self, chat: 'models.TypeChat', chat_phones: 'list[models.TypeChatPhone]'):
        for chat_phone in chat_phones:
            phone = chat_phone.phone

            if phone.takeout:
                continue

            try:
                async with utils.TelegramClient(phone) as client:
                    while True:
                        try:
                            async with client.takeout(users=True, chats=True, megagroups=True, channels=True,
                                                      files=True, max_file_size=2147483647) as takeout:
                                await self._get_members(takeout, chat)
                        except telethon.errors.TakeoutInitDelayError as ex:
                            logger.warning('Must wait', ex.seconds, 'before takeout')

                            await asyncio.sleep(ex.seconds)

                            continue
                        except telethon.errors.TakeoutInvalidError as ex:
                            logger.error(f"{ex}")

                            break
                        else:
                            return True
            except exceptions.UnauthorizedError as ex:
                logger.critical(f"{ex}")

                chat_phone.is_using = False
                chat_phone.save()

                continue

        raise Exception("Chat doesn't have available phones, try again later.")

    def run(self, chat_id):
        try:
            chat = models.Chat(id=chat_id).reload()
        except exceptions.RequestException as ex:
            logger.error(f"{ex}")

            raise Exception("Can't get given chat.")

        try:
            chat_phones = models.ChatPhone.find(chat=chat.id, is_using=True)
        except exceptions.RequestException as ex:
            logger.error(f"{ex}")

            raise Exception("Can't get chat wired phones.")

        return asyncio.run(self._run(chat, chat_phones))


app.register_task(ParseMembersTask())


class ParseMessagesTask(BaseChatTask):
    name = "ParseMessagesTask"
    queue = "low_prio"

    async def _get_messages(self, client, chat: 'models.TypeChat'):
        """Iterate telegram chat messages and save to API"""

        last_messages = models.Message.find(chat=chat.id, ordering="-internal_id", limit=1)
        max_id = last_messages[0].internal_id if last_messages else 0

        async for tg_message in client.iter_messages(chat.internal_id, max_id=max_id):
            if not isinstance(tg_message, telethon.types.Message):
                continue

            await self.find_links(tg_message.message)

            await self.set_message(client, chat, tg_message)
        else:
            logger.info("Messages download success.")

    async def _run(self, chat: 'models.TypeChat', chat_phones: 'list[models.TypeChatPhone]'):
        for chat_phone in chat_phones:
            phone = chat_phone.phone

            if phone.takeout:
                continue

            try:
                async with utils.TelegramClient(phone) as client:
                    while True:
                        try:
                            async with client.takeout(users=True, chats=True, megagroups=True, channels=True,
                                                      files=True, max_file_size=2147483647) as takeout:
                                await self._get_messages(takeout, chat)
                        except telethon.errors.TakeoutInitDelayError as ex:
                            logger.warning('Must wait', ex.seconds, 'before takeout')

                            await asyncio.sleep(ex.seconds)

                            continue
                        except telethon.errors.TakeoutInvalidError as ex:
                            logger.error(f"{ex}")

                            break
                        else:
                            return True
            except exceptions.UnauthorizedError as ex:
                logger.critical(f"{ex}")

                chat_phone.is_using = False
                chat_phone.save()

                continue

        raise Exception("Chat doesn't have available phones, try again later.")

    def run(self, chat_id):
        try:
            chat = models.Chat(id=chat_id).reload()
        except exceptions.RequestException as ex:
            logger.error(f"{ex}")

            raise Exception("Can't find given chat.")

        try:
            chat_phones = models.ChatPhone.find(chat=chat.id, is_using=True)
        except exceptions.RequestException as ex:
            logger.error(f"{ex}")

            raise Exception("Can't get chat wired phones.")

        return asyncio.run(self._run(chat, chat_phones))


app.register_task(ParseMessagesTask())


class MonitoringChatTask(BaseChatTask):
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
                                await self.set_chat_user(client, chat, user, user.participant)

                    @client.on(telethon.events.NewMessage(chats=chat.internal_id, incoming=True))
                    async def handle_new_message(event):
                        if not isinstance(event.message, telethon.types.Message):
                            return

                        await self.find_links(event.message.message)

                        await self.set_message(client, chat, event.message)

                    await client.run_until_disconnected()

                    return True
            except exceptions.UnauthorizedError as ex:
                logger.critical(f"{ex}")

                chat_phone.is_using = False
                chat_phone.save()

                continue

        raise Exception("Chat doesn't have available phones, try again later.")

    def run(self, chat_id):
        try:
            chat = models.Chat(id=chat_id).reload()
        except exceptions.RequestException as ex:
            logger.error(f"{ex}")

            raise Exception("Can't get given chat.")

        try:
            chat_phones = models.ChatPhone.find(chat=chat.id, is_using=True)
        except exceptions.RequestException as ex:
            logger.error(f"{ex}")

            raise Exception("Can't get chat wired phones.")

        return asyncio.run(self._run(chat, chat_phones))


app.register_task(MonitoringChatTask())
