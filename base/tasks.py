"""Collection of tasks representations"""

from __future__ import absolute_import
from abc import abstractmethod
import re
import asyncio
import telethon
import random
import names
import telethon.sessions

from base.celeryapp import app
from base import models, utils, exceptions
from base.models import Phone, Chat, ChatPhone, Message, Member, ChatMember, ChatMemberRole


class Task(app.Task):
    """Base task class"""

    @abstractmethod
    def run(self, *args, **kswargs):
        """Start the task work"""

        raise NotImplementedError


class PhoneAuthorizationTask(Task):
    """PhoneAuthorizationTask"""

    name = "PhoneAuthorizationTask"

    async def _run(self, phone: 'models.TypePhone'):
        client = telethon.TelegramClient(
            connection_retries=-1,
            retry_delay=5,
            session=telethon.sessions.StringSession(phone.session),
            api_id=phone.parser.api_id,
            api_hash=phone.parser.api_hash,
        )

        if not client.is_connected():
            try:
                await client.connect()
            except OSError as ex:
                print(f"Unable to connect client. Exception: {ex}")

                return False

        code_hash = None

        while True:
            if not await client.is_user_authorized():
                try:
                    if phone.code is not None and code_hash is not None:
                        try:
                            await client.sign_in(phone.number, phone.code, phone_code_hash=code_hash)
                        except telethon.errors.PhoneNumberUnoccupiedError:
                            await asyncio.sleep(random.randint(2, 5))

                            if phone.first_name is None:
                                phone.first_name = names.get_first_name()

                            if phone.last_name is None:
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
                            print(f"Code invalid. Exception {ex}")

                            phone.code = None
                            phone.status_text = "Code invalid"
                            phone.save()

                            continue

                        me = await client.get_me()

                        internal_id = me.id if me else None

                        if internal_id is not None and phone.internal_id != internal_id:
                            phone.internal_id = internal_id

                        phone.session = client.session.save()
                        phone.status = Phone.READY
                        phone.status_text = None
                        phone.code = None
                        phone.save()

                        break
                    elif code_hash is None:
                        try:
                            sent = await client.send_code_request(phone=phone.number, force_sms=True)

                            code_hash = sent.phone_code_hash
                        except telethon.errors.rpcerrorlist.FloodWaitError as ex:
                            print(f"Flood exception. Sleep {ex.seconds}.")

                            phone.status = Phone.FLOOD
                            phone.status_text = str(ex)
                            phone.save()

                            await asyncio.sleep(ex.seconds)

                            continue
                    else:
                        await asyncio.sleep(10)

                        phone.reload()
                except telethon.errors.RPCError as ex:
                    print(f"Cannot authentificate. Exception: {ex}")

                    phone.session = None
                    phone.status = Phone.BAN
                    phone.status_text = str(ex)
                    phone.code = None
                    phone.save()

                    return False
            else:
                break

        dialogs = await client.get_dialogs(limit=0)

        if dialogs.total >= 500:
            phone.status = Phone.FULL
            phone.save()

        print("Authorized.")

        return True

    def run(self, phone_id):
        try:
            phone = Phone(phone_id).reload()
        except exceptions.RequestException:
            return False

        return asyncio.run(self._run(phone))


app.register_task(PhoneAuthorizationTask())


class ChatResolveTask(Task):
    """ChatResolveTask"""

    name = "ChatResolveTask"

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

        raise ValueError(f"Cannot find any entity corresponding to '{string}'")

    async def _run(self, chat: 'models.TypeChat', phones: 'list[models.TypePhone]'):
        for phone in phones:
            try:
                async with utils.TelegramClient(phone) as client:
                    try:
                        tg_chat = await self.__resolve(client, chat.link)
                    except telethon.errors.FloodWaitError as ex:
                        print(f"Chat resolve must wait {ex.seconds}.")

                        phone.status = Phone.FLOOD
                        phone.status_text = str(ex)
                        phone.save()

                        continue
                    except (TypeError, KeyError, ValueError, telethon.errors.RPCError) as ex:
                        print(f"Chat resolve exception. Exception: {ex}.")

                        chat.status = Chat.FAILED
                        chat.status_text = str(ex)

                        break
                    else:
                        if isinstance(tg_chat, telethon.types.ChatInvite):
                            print("Chat is available, but need to join.")

                            chat.status_text = "Chat is available, but need to join."
                        else:
                            chat.status_text = None

                            internal_id = telethon.utils.get_peer_id(tg_chat)

                            if chat.internal_id != internal_id:
                                chat.internal_id = internal_id

                        if chat.title != tg_chat.title:
                            chat.title = tg_chat.title

                        chat.status = Chat.AVAILABLE

                        break
            except (
                exceptions.UnauthorizedError,
                telethon.errors.UserDeactivatedBanError
            ) as ex:
                phone.status = Phone.CREATED if isinstance(ex, exceptions.UnauthorizedError) else Phone.BAN
                phone.status_text = str(ex)

                phone.save()

        chat.save()

    def run(self, chat_id):
        try:
            chat = Chat(chat_id).reload()
        except exceptions.RequestException:
            return False

        phones = Phone.find(status=Phone.READY, parser=chat.parser.alias())

        return asyncio.run(self._run(chat, phones))


app.register_task(ChatResolveTask())


class JoinChatTask(Task):
    """JoinChatTask"""

    name = "JoinChatTask"

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

        raise ValueError(f"Cannot find any entity corresponding to '{string}'")

    async def _run(self, chat: 'models.TypeChat', phone: 'models.TypePhone'):
        while True:
            try:
                async with utils.TelegramClient(phone) as client:
                    try:
                        dialogs = await client.get_dialogs(limit=0)

                        if dialogs.total >= 500:
                            phone.status = Phone.FULL
                            phone.save()

                            break

                        tg_chat = await self.__join(client, chat.link)
                    except telethon.errors.FloodWaitError as ex:
                        print(f"Chat wiring for phone {phone.id} must wait {ex.seconds}.")

                        phone.status = Phone.FLOOD
                        phone.status_text = str(ex)
                        phone.save()

                        await asyncio.sleep(ex.seconds)

                        continue
                    except telethon.errors.ChannelsTooMuchError as ex:
                        phone.status = Phone.FULL
                        phone.status_text = str(ex)
                        phone.save()

                        break
                    except telethon.errors.UserDeactivatedBanError as ex:
                        print(f"Chat not available for phone {phone.id}. Exception {ex}")

                        phone.status = Phone.BAN
                        phone.status_text = str(ex)
                        phone.save()

                        break
                    except telethon.errors.SessionPasswordNeededError as ex:
                        raise exceptions.UnauthorizedError(str(ex))
                    except (TypeError, KeyError, ValueError, telethon.errors.RPCError) as ex:
                        print(f"Chat not available. Exception {ex}.")

                        chat.status = Chat.FAILED
                        chat.status_text = str(ex)
                        chat.save()

                        break
                    else:
                        if tg_chat:
                            internal_id = telethon.utils.get_peer_id(tg_chat)

                            if chat.internal_id != internal_id:
                                chat.internal_id = internal_id

                            if chat.title != tg_chat.title:
                                chat.title = tg_chat.title

                        chat_phone = ChatPhone(chat, phone, True)
                        chat_phone.save()

                        return True
            except (
                exceptions.UnauthorizedError,
                telethon.errors.UserDeactivatedBanError
            ) as ex:
                phone.status = Phone.CREATED if isinstance(ex, exceptions.UnauthorizedError) else Phone.BAN
                phone.status_text = str(ex)
                phone.save()

                break

        return False

    def run(self, chat_id: 'str', phone_id: 'str'):
        try:
            chat = Chat(chat_id).reload()
        except exceptions.RequestException:
            return False

        try:
            phone = Phone(phone_id).reload()
        except exceptions.RequestException:
            return False

        return asyncio.run(self._run(chat, phone))


app.register_task(JoinChatTask())


class ParseChatTask(Task):
    """ParseChatTask"""

    name = "ParseChatTask"

    async def _set_member(self, client, user: 'telethon.types.User') -> 'models.TypeMember':
        """Create 'Member' from telegram entity"""

        new_member = {
            "internal_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone
        }

        try:
            full_user: 'telethon.types.UserFull' = await client(
                telethon.functions.users.GetFullUserRequest(user.id)
            )
        except:
            pass
        else:
            new_member["username"] = full_user.user.username
            new_member["first_name"] = full_user.user.first_name
            new_member["last_name"] = full_user.user.last_name
            new_member["phone"] = full_user.user.phone
            new_member["about"] = full_user.about

        return Member(**new_member).save()

    def __set_chat_member(self, chat: 'models.TypeChat', member: 'models.TypeMember', participant=None) -> 'models.TypeChatMember':
        """Create 'ChatMember' from telegram entity"""

        new_chat_member = {"chat": chat, "member": member}

        if isinstance(participant, (telethon.types.ChannelParticipant, telethon.types.ChatParticipant)):
            new_chat_member["date"] = participant.date.isoformat()
        else:
            new_chat_member["isLeft"] = True

        return ChatMember(**new_chat_member).save()

    def __set_chat_member_role(self, chat_member: 'models.TypeChatMember', participant=None) -> 'models.TypeChatMemberRole':
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

        return ChatMemberRole(**new_chat_member_role).save()

    async def _handle_user(self, chat: 'models.TypeChat', client, user: 'telethon.types.TypeUser', participant=None):
        """Handle telegram user"""

        if user.is_self:
            return None, None, None

        member = await self._set_member(client, user)
        chat_member = self.__set_chat_member(chat, member, participant)
        chat_member_role = self.__set_chat_member_role(chat_member, participant)

        return member, chat_member, chat_member_role

    async def _handle_links(self, client: 'utils.TelegramClient', text):
        """Handle links from message text"""

        for link in re.finditer(utils.LINK_RE, text):
            username, is_join_chat = utils.parse_username(link)

            if not username:
                continue

            if not is_join_chat:
                try:
                    tg_entity: 'telethon.types.TypeChat | telethon.types.User' = await client.get_entity(username)

                    if isinstance(tg_entity, telethon.types.User):
                        member = await self._set_member(client, tg_entity)

                        # TODO: Как запускать?
                        # processes.member_media_process(chat_phone, member, tg_entity)

                        continue
                except (ValueError, telethon.errors.RPCError):
                    continue

            Chat(link=link, internal_id=tg_entity.id, title=tg_entity.title, is_available=False).save()

            print(f"New entity from link {link} created.")

    def _get_fwd(self, fwd_from):
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

    async def _handle_message(self, chat: 'models.TypeChat', client, tg_message: 'telethon.types.TypeMessage'):
        """Handle telegram message"""

        fwd_from_id, fwd_from_name = self._get_fwd(tg_message.fwd_from)

        chat_member = None

        if isinstance(tg_message.from_id, telethon.types.PeerUser):
            user: 'telethon.types.TypeUser' = await client.get_entity(tg_message.from_id)

            member, chat_member, chat_member_role = await self._handle_user(chat, client, user)

            # TODO: Как запускать?
            # processes.member_media_process(chat_phone, member, user)

        reply_to = Message(internal_id=tg_message.reply_to.reply_to_msg_id, chat=chat).save() if tg_message.reply_to is not None else None

        if tg_message.replies is not None:
            try:
                replies = await client(
                    telethon.tl.functions.messages.GetRepliesRequest(
                        tg_message.peer_id, tg_message.id, 0, None, 0, 0, 0, 0, 0
                    )
                )

                for reply in replies.messages:
                    reply: 'telethon.types.TypeMessage'

                    await self._handle_message(chat, client, reply)
            except Exception as ex:
                print(str(ex))

        message = Message(
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

        # if tg_message.media != None:
        #     TODO: Как запускать?
        #     multiprocessing.Process(target=processes.message_media_process, args=(chat_phone, message, tg_message)).start()

    async def _get_members(self, chat: 'models.TypeChat', client):
        """Iterate telegram chat members and save to API"""

        async for user in client.iter_participants(entity=chat.internal_id, aggressive=True):
            member, chat_member, chat_member_role = await self._handle_user(
                chat, client, user, user.participant
            )

            # TODO: Как запускать?
            # multiprocessing.Process(target=processes.member_media_process, args=(chat_phone, member, user)).start()
        else:
            print("Members download success.")

    async def _get_messages(self, chat: 'models.TypeChat', client):
        """Iterate telegram chat messages and save to API"""

        last_messages = Message.find(chat=chat.alias(), ordering="-internal_id", limit=1)
        max_id = last_messages[0].internal_id if last_messages.get(0) is not None else 0

        async for tg_message in client.iter_messages(chat.internal_id, 1000, max_id=max_id):
            if not isinstance(tg_message, telethon.types.Message):
                continue

            await self._handle_links(client, tg_message.message)

            await self._handle_message(chat, client, tg_message)
        else:
            print("Messages download success.")

    async def _run(self, chat: 'models.TypeChat'):
        chat_phones = ChatPhone.find(chat=chat.alias())

        for chat_phone in chat_phones:
            phone = chat_phone.phone

            try:
                async with utils.TelegramClient(phone) as client:
                    try:
                        await self._get_members(chat, client)

                        await self._get_messages(chat, client)
                    except telethon.errors.TimeoutError as ex:
                        print(f"{ex}")

                        # TODO: Ретрай?
                    except telethon.errors.FloodWaitError as ex:
                        print(f"Messages request must wait {ex.seconds} seconds.")

                        phone.status = Phone.FLOOD
                        phone.status_text = str(ex)
                        phone.save()

                        await asyncio.sleep(ex.seconds)

                        continue
                    except (KeyError, ValueError, telethon.errors.RPCError) as ex:
                        print(f"Chat not available. Exception: {ex}")

                        chat.status = Chat.FAILED
                        chat.status_text = str(ex)
                        chat.save()
            except (
                exceptions.UnauthorizedError,
                telethon.errors.UserDeactivatedBanError
            ) as ex:
                phone.status = Phone.CREATED if isinstance(ex, exceptions.UnauthorizedError) else Phone.BAN
                phone.status_text = str(ex)
                phone.save()

    def run(self, chat_id):
        try:
            chat = Chat(chat_id).reload()
        except exceptions.RequestException:
            return False

        return asyncio.run(self._run(chat))


app.register_task(ParseChatTask())


class MonitoringChatTask(ParseChatTask):
    name = "MonitoringChatTask"

    async def _run(self, chat):
        from base.models import Phone, Chat, ChatPhone

        chat_phones = ChatPhone.find(chat=chat.alias())

        for chat_phone in chat_phones:
            phone = chat_phone.phone

            try:
                async with utils.TelegramClient(phone) as client:
                    async def handle_chat_action(event):
                        if event.user_added or event.user_joined or event.user_left or event.user_kicked:
                            async for user in event.get_users():
                                await self._handle_user(chat, client, user, user.participant)

                    async def handle_new_message(event):
                        if not isinstance(event.message, telethon.types.Message):
                            return

                        await self._handle_links(client, event.message.message)

                        await self._handle_message(chat, client, event.message)

                    client.add_event_handler(handle_chat_action, telethon.events.chataction.ChatAction(chats=chat.internal_id))
                    client.add_event_handler(handle_new_message, telethon.events.NewMessage(chats=chat.internal_id, incoming=True))

                    while True:
                        await asyncio.sleep(10)

                        chat.reload()

                        if chat.status is not Chat.MONITORING:
                            return True
            except (
                exceptions.UnauthorizedError,
                telethon.errors.UserDeactivatedBanError
            ) as ex:
                phone.status = Phone.CREATED if isinstance(ex, exceptions.UnauthorizedError) else Phone.BAN
                phone.status_text = str(ex)
                phone.save()


app.register_task(MonitoringChatTask())
