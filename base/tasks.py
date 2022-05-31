from __future__ import absolute_import
import asyncio, telethon
from base.celeryapp import app
from base.utils import ApiService
import base.models as models

@app.task
def test(params: str):
    print("Run with params: {}".format(params))
    return True


class PhoneAuthorizationTask(app.Task):
    import base.models as models

    name = "PhoneAuthorizationTask"

    async def _run(self, phone: 'models.TypePhone'):
        import random, names, telethon, telethon.sessions
        import base.models as models

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

                            await client.sign_up(phone.code, phone.first_name, phone.last_name, phone_code_hash=code_hash)
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
                        phone.status = models.Phone.READY
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
                            
                            phone.status = models.Phone.FLOOD
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
                    phone.status = models.Phone.BAN
                    phone.status_text = str(ex)
                    phone.code = None

                    phone.save()

                    return False
            else:
                break

        dialogs = await client.get_dialogs(limit=0)

        if dialogs.total >= 500:
            phone.status = models.Phone.FULL
            phone.save()

        print(f"Authorized.")

        return True

    def run(self, phone_id):
        from models import Phone
        import base.exceptions as exceptions

        try:
            phone = Phone(phone_id).reload()
        except exceptions.RequestException:
            return False

        return asyncio.run(self._run(phone))


app.register_task(PhoneAuthorizationTask())


class ChatResolveTask(app.Task):
    name = "ChatResolveTask"

    async def __resolve(self, client, string):
        from base.utils import parse_username

        username, is_join_chat = parse_username(string)

        if is_join_chat:
            invite = await client(telethon.functions.messages.CheckChatInviteRequest(username))

            if isinstance(invite, telethon.types.ChatInvite):
                return invite
            elif isinstance(invite, telethon.types.ChatInviteAlready):
                return invite.chat
        elif username:
            return await client.get_entity(username)

        raise ValueError(
            'Cannot find any entity corresponding to "{}"'.format(string)
        )

    async def _run(self, chat: 'models.TypeChat', phones: 'list[models.TypePhone]'):
        from models import Chat, Phone
        from base.utils import TelegramClient
        from base.exceptions import UnauthorizedError

        for phone in phones:
            try:
                async with TelegramClient(phone) as client:
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
                            print(f"Chat is available, but need to join.")

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
                UnauthorizedError,
                telethon.errors.UserDeactivatedBanError
            ) as ex:
                phone.status = Phone.CREATED if isinstance(ex, UnauthorizedError) else Phone.BAN
                phone.status_text = str(ex)

                phone.save()

        chat.save()

    def run(self, chat_id):
        from models import Chat, Phone
        import base.exceptions as exceptions

        try:
            chat: 'models.TypeChat' = Chat(chat_id).reload()
        except exceptions.RequestException:
            return False

        phones = ApiService().get('phones', { "status": Phone.READY, "parser": { "id": chat.parser.id } })
        phones = [Phone(**phone) for phone in phones]

        return asyncio.run(self._run(chat, phones))


app.register_task(ChatResolveTask())


class JoinChatTask(app.Task):
    name = "JoinChatTask"

    async def __join(self, client, string):
        from base.utils import parse_username

        username, is_join_chat = parse_username(string)

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

        raise ValueError(
            'Cannot find any entity corresponding to "{}"'.format(string)
        )

    async def _run(self, chat, phone):
        from base.exceptions import UnauthorizedError
        from base.utils import TelegramClient
        from models import Chat, Phone, ChatPhone

        while True:
            try:
                async with TelegramClient(phone) as client:
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
                        raise UnauthorizedError(str(ex))
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
                UnauthorizedError,
                telethon.errors.UserDeactivatedBanError
            ) as ex:
                phone.status = Phone.CREATED if isinstance(ex, UnauthorizedError) else Phone.BAN
                phone.status_text = str(ex)

                phone.save()

                break

        return False

    def run(self, chat_id, phone_id):
        from models import Chat, Phone
        import base.exceptions as exceptions

        try:
            chat: 'models.TypeChat' = Chat(chat_id).reload()
        except exceptions.RequestException:
            return False

        try:
            phone: 'models.TypePhone' = Phone(phone_id).reload()
        except exceptions.RequestException:
            return False

        return asyncio.run(self._run(chat, phone, chat.parser))


app.register_task(JoinChatTask())


class ParseChatTask(app.Task):
    name = "ParseChatTask"

    async def _set_member(self, client, user):
        from models import Member

        new_member = {
            "internal_id": user.id, 
            "username": user.username, 
            "first_name": user.first_name, 
            "last_name": user.last_name, 
            "phone": user.phone
        }

        try:
            full_user = await client(
                telethon.functions.users.GetFullUserRequest(user.id)
            )
        except Exception:
            pass
        else:
            new_member["username"] = full_user.user.username
            new_member["first_name"] = full_user.user.first_name
            new_member["last_name"] = full_user.user.last_name
            new_member["phone"] = full_user.user.phone
            new_member["about"] = full_user.about

        return await sync_to_async(Member.objects.update_or_create)(**new_member)
        
    async def _set_chat_member(self, chat, member, participant = None):
        from models import ChatMember

        new_chat_member = { "chat": chat, "member": member }

        if isinstance(participant, (telethon.types.ChannelParticipant, telethon.types.ChatParticipant)):
            new_chat_member["date"] = participant.date.isoformat()
        else:
            new_chat_member["isLeft"] = True

        return await sync_to_async(ChatMember.objects.update_or_create)(**new_chat_member)
    
    async def _set_chat_member_role(self, chat_member, participant = None):
        from models import ChatMemberRole

        new_chat_member_role = { "member": chat_member }

        if isinstance(participant, (telethon.types.ChannelParticipantAdmin, telethon.types.ChatParticipantAdmin)):
            new_chat_member_role["title"] = (participant.rank if participant.rank is not None else "Администратор")
            new_chat_member_role["code"] = "admin"
        elif isinstance(participant, (telethon.types.ChannelParticipantCreator, telethon.types.ChatParticipantCreator)):
            new_chat_member_role["title"] = (participant.rank if participant.rank is not None else "Создатель")
            new_chat_member_role["code"] = "creator"
        else:
            new_chat_member_role["title"] = "Участник"
            new_chat_member_role["code"] = "member"

        return await sync_to_async(ChatMemberRole.objects.update_or_create)(**new_chat_member_role)
    
    def _get_fwd(self, fwd_from):
        if fwd_from is not None:
            fwd_from_id = None

            if fwd_from.from_id is not None:
                if isinstance(fwd_from.from_id, telethon.types.PeerChannel):
                    fwd_from_id = fwd_from.from_id.channel_id
                elif isinstance(fwd_from.from_id, telethon.types.PeerUser):
                    fwd_from_id = fwd_from.from_id.user_id
            
            return fwd_from_id, fwd_from.from_name if fwd_from.from_name is not None else "Неизвестно"
            
        return None, None
    
    async def _handle_links(self, client, text):
        import re
        from base.utils import LINK_RE, parse_username
        from models import Chat

        for link in re.finditer(LINK_RE, text):
            username, is_join_chat = parse_username(link)

            if not username:
                continue
            elif not is_join_chat:
                try:
                    tg_entity = await client.get_entity(username)

                    if isinstance(tg_entity, telethon.types.User):
                        member = await self._set_member(client, tg_entity)

                        # TODO: Как запускать?
                        # multiprocessing.Process(target=processes.member_media_process, args=(chat_phone, member, tg_entity)).start()

                        continue
                except (ValueError, telethon.errors.RPCError) as ex:
                    continue

            await sync_to_async(Chat.objects.create)(link=link, internal_id=tg_entity.id, title=tg_entity.title, is_available=False)

            print(f"New entity from link {link} created.")

    async def _handle_user(self, chat, client, user, participant=None):
        if user.is_self:
            return None, None, None

        member = await self._set_member(client, user)
        chat_member = await self._set_chat_member(chat, member, participant)
        chat_member_role = await self._set_chat_member_role(chat_member, participant)

        return member, chat_member, chat_member_role
        
    async def _handle_message(self, chat, client, tg_message):
        from models import Message
        
        fwd_from_id, fwd_from_name = self._get_fwd(tg_message.fwd_from)
        
        chat_member = None

        if isinstance(tg_message.from_id, telethon.types.PeerUser):
            user = await client.get_entity(tg_message.from_id)

            member, chat_member, chat_member_role = await self._handle_user(chat, client, user)

            # TODO: Как запускать?
            # multiprocessing.Process(target=processes.member_media_process, args=(chat_phone, member, user)).start()

        reply_to = await sync_to_async(Message.objects.update_or_create)(internal_id=tg_message.reply_to.reply_to_msg_id, chat=chat) if tg_message.reply_to is not None else None

        if tg_message.replies is not None:
            try:
                replies = await client(
                    telethon.tl.functions.messages.GetRepliesRequest(
                        tg_message.peer_id, tg_message.id, 0, None, 0, 0, 0, 0, 0
                    )
                )

                for reply in replies.messages:
                    await self._handle_message(chat, client, reply)
            except Exception as ex:
                print(str(ex))

        message = await sync_to_async(Message.objects.update_or_create)(
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
        
        # if tg_message.media != None:
        #     TODO: Как запускать?
        #     multiprocessing.Process(target=processes.message_media_process, args=(chat_phone, message, tg_message)).start()

    async def _get_members(self, chat, client):
        async for user in client.iter_participants(entity=chat.internal_id, aggressive=True):
            member, chat_member, chat_member_role = await self._handle_user(
                chat, client, user, user.participant
            )

            # TODO: Как запускать?
            # multiprocessing.Process(target=processes.member_media_process, args=(chat_phone, member, user)).start()
        else:
            print(f"Messages download success.")

    async def _get_messages(self, chat, client, max_id=0):
        async for tg_message in client.iter_messages(chat.internal_id, 1000, max_id=max_id):
            if not isinstance(tg_message, telethon.types.Message):
                continue

            await self._handle_links(client, tg_message.message)

            await self._handle_message(chat, client, tg_message)
        else:
            print(f"Messages download success.")

    async def _run(self, chat, chat_phones, max_id):
        from models import Chat, Phone
        from base.exceptions import UnauthorizedError
        from base.utils import TelegramClient

        for chat_phone in chat_phones:
            phone = await sync_to_async(chat_phone.phone)()

            try:
                async with TelegramClient(phone) as client:
                    try:
                        await self._get_members(chat, client)

                        await self._get_messages(chat, client, max_id)
                    except telethon.errors.TimeoutError as ex:
                        print(f"{ex}")

                        # TODO: Ретрай?
                    except telethon.errors.FloodWaitError as ex:
                        print(f"Messages request must wait {ex.seconds} seconds.")

                        phone.status = Phone.FLOOD
                        phone.status_text = str(ex)

                        await sync_to_async(phone.save)()

                        await asyncio.sleep(ex.seconds)

                        continue
                    except (KeyError, ValueError, telethon.errors.RPCError) as ex:
                        print(f"Chat not available. Exception: {ex}")

                        chat.status = Chat.FAILED
                        chat.status_text = str(ex)

                        await sync_to_async(chat.save)()
            except (
                UnauthorizedError,
                telethon.errors.UserDeactivatedBanError
            ) as ex:
                phone.status = Phone.CREATED if isinstance(ex, UnauthorizedError) else Phone.BAN
                phone.status_text = str(ex)

                await sync_to_async(phone.save)()

    def run(self, chat_id):
        from models import Chat, ChatPhone, Message

        try:
            chat = Chat.objects.get(id=chat_id)
        except Chat.DoesNotExist:
            return False

        chat_phones = ChatPhone.objects.filter(chat_id=chat.id)

        last_message = Message.objects.filter(chat_id=chat.id).order_by("-internal_id")[0]
        max_id = last_message.internal_id if last_message is not None else 0

        return asyncio.run(self._run(chat, chat_phones, max_id))


app.register_task(ParseChatTask())


class MonitoringChatTask(ParseChatTask):
    name = "MonitoringChatTask"

    async def _run(self, chat, chat_phones):
        from models import Phone, Chat
        from base.utils import TelegramClient
        from base.exceptions import UnauthorizedError

        for chat_phone in chat_phones:
            phone = await sync_to_async(chat_phone.phone)()

            try:
                async with TelegramClient(phone) as client:
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

                        await sync_to_async(chat.refresh_from_db)()

                        if chat.status is not Chat.MONITORING:
                            return True
            except (
                UnauthorizedError,
                telethon.errors.UserDeactivatedBanError
            ) as ex:
                phone.status = Phone.CREATED if isinstance(ex, UnauthorizedError) else Phone.BAN
                phone.status_text = str(ex)

                await sync_to_async(phone.save)()

    def run(self, chat_id):
        from models import Chat, ChatPhone

        try:
            chat = Chat.objects.get(id=chat_id)
        except Chat.DoesNotExist:
            return False

        chat_phones = ChatPhone.objects.filter(chat_id=chat.id)

        return asyncio.run(self._run(chat, chat_phones))


app.register_task(MonitoringChatTask())

