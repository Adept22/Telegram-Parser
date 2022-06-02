"""Collection of entity representations"""

from abc import ABCMeta, abstractmethod
from typing import Generic, TypeVar
import math
from telethon.client import downloads
from base.utils import ApiService
from base import exceptions

T = TypeVar('T', bound='Entity')


class Entity(Generic[T], metaclass=ABCMeta):
    """Base class for entities"""

    def __init__(self, id: 'str' = None, **kwargs):
        self._id = id

    def __str__(self):
        return f"{self.__class__.__name__} object ({self.id})"

    def __eq__(self, other):
        if not isinstance(other, Entity):
            raise NotImplementedError

        my_id = self.id

        if my_id is None:
            return self is other

        return my_id == other.id

    @property
    def id(self) -> 'str | None':
        """Идентификатор сущности."""

        return self._id

    @id.setter
    def id(self, new_id) -> 'None':
        """Сеттер идентификатора сущности."""

        self._id = new_id

    @property
    @abstractmethod
    def endpoint(self) -> str:
        """Название сущности в пути API."""

        raise NotImplementedError

    @property
    @abstractmethod
    def unique_constraint(self) -> 'dict | None':
        """Свойства для проверки существования сущности,
        они же отражают уникальность."""

        raise NotImplementedError

    @abstractmethod
    def serialize(self) -> 'dict':
        """Сериализация сущности. Т.е. из `self` в `dict`"""

        raise NotImplementedError

    def deserialize(self, **kwargs) -> 'T':
        """Десериализация сущности. Т.е. из `dict` в `self`"""

        for key in kwargs:
            if hasattr(self, key):
                setattr(self, key, kwargs[key])

        return self

    def alias(self) -> 'dict':
        """Сериализация ссылки на сущность"""
        if self.id is None:
            return None

        return {"id": self.id}

    @classmethod
    def find(cls, **kwargs) -> 'list[T]':
        """Возвращает отфильтрованный и отсортированный список сущностей"""

        entities = ApiService().get(cls.endpoint, **kwargs)
        return [cls(**entity) for entity in entities["results"]]

    def reload(self) -> 'T':
        """Обновляет текущую сущность из API."""

        if not self.id:
            raise ValueError("Entity hasn't id")

        entity = ApiService().get(self.__class__.endpoint, id=self.id, force=True)

        self.deserialize(**entity)

        return self

    def save(self) -> 'T':
        """Создает/изменяет сущность в API."""

        try:
            entity = ApiService().set(self.__class__.endpoint, **self.serialize())
        except exceptions.UniqueConstraintViolationError as ex:
            if self.unique_constraint is None:
                raise ex

            entities = ApiService().get(self.__class__.endpoint, **self.unique_constraint)

            if len(entities) > 0:
                self.id = entities[0]['id']
                self.save()
        else:
            self.deserialize(**entity)

        return self

    def delete(self) -> 'None':
        """
        Удаляет сущность из API.
        """

        ApiService().delete(self.__class__.endpoint, self.serialize())


class Media(Generic[T], Entity['Media'], metaclass=ABCMeta):
    """Base class for media entities"""

    async def upload(self, client, tg_media, size: 'int', extension: 'str') -> 'None':
        """Uploads media on server"""

        if self.id is None:
            raise ValueError("Entity hasn't id")

        chunk_number = 0
        chunk_size = downloads.MAX_CHUNK_SIZE
        total_chunks = math.ceil(size / chunk_size)

        async for chunk in client.iter_download(tg_media, chunk_size=chunk_size, file_size=size):
            ApiService().chunk(
                self.__class__.endpoint,
                self.id,
                str(tg_media.id) + extension,
                chunk,
                chunk_number,
                chunk_size,
                total_chunks,
                size
            )

            chunk_number += 1


class Host(Entity['Host']):
    """Host entity representation"""

    endpoint = "hosts"

    def __init__(self, public_ip: 'str', local_ip: 'str', name: 'str', **kwargs):
        super().__init__(**kwargs)

        self.public_ip: 'str' = public_ip
        self.local_ip: 'str' = local_ip
        self.name: 'str' = name

    @property
    def unique_constraint(self) -> 'dict | None':
        return None

    def serialize(self) -> 'dict':
        return {
            "id": self.id,
            "public_ip": self.public_ip,
            "local_ip": self.local_ip,
            "name": self.name
        }


class Parser(Entity['Parser']):
    """Parser entity representation"""

    endpoint = "parsers"

    NEW = 0
    IN_PROGRESS = 1
    FAILED = 2

    def __init__(self, status: 'int', api_id: 'str', api_hash: 'str', **kwargs):
        super().__init__(**kwargs)

        self._host: 'TypeHost' = None
        self.host: 'TypeHost' = kwargs.get('host')
        self.status: 'int' = status
        self.api_id: 'str' = api_id
        self.api_hash: 'str' = api_hash

    @property
    def unique_constraint(self) -> 'dict | None':
        return None

    @property
    def host(self) -> 'TypeHost':
        """Host property"""

        return self._host

    @host.setter
    def host(self, new_host) -> 'None':
        if isinstance(new_host, Host):
            self._host = new_host
        elif isinstance(new_host, str):
            if isinstance(self._host, Host):
                self._host.id = new_host
            else:
                self._host = Host(id=new_host)
        elif isinstance(new_host, dict):
            if isinstance(self._host, Host):
                self._host.deserialize(**new_host)
            else:
                self._host = Host(**new_host)
        elif new_host is None:
            self._host = None
        else:
            raise TypeError(f"Can't cast {type(new_host)} to 'Host' object of property 'host'.")

        if isinstance(self._host, Host):
            self._host.reload()

    def serialize(self) -> 'dict':
        return {
            "id": self.id,
            "host": self.host.alias() if self.host else None,
            "status": self.status,
            "api_id": self.api_id,
            "api_hash": self.api_hash
        }


class Chat(Entity['Chat']):
    """Chat entity representation"""

    endpoint = "chats"

    CREATED = 0
    AVAILABLE = 1
    MONITORING = 2
    FAILED = 3

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.link: 'str' = kwargs.get("link")
        self.status: 'int' = kwargs.get("status", 0)
        self.status_text: 'str | None' = kwargs.get("status_text")
        self.internal_id: 'int | None' = kwargs.get("internal_id")
        self.title: 'str | None' = kwargs.get("title")
        self.description: 'str | None' = kwargs.get("description")
        self.date: 'str | None' = kwargs.get("date")
        self._parser: 'TypeParser' = None
        self.parser: 'TypeParser' = kwargs.get("parser")

    @property
    def unique_constraint(self) -> 'dict | None':
        return None

    @property
    def parser(self) -> 'TypeParser':
        """Parser property"""

        return self._parser

    @parser.setter
    def parser(self, new_parser) -> 'None':
        if isinstance(new_parser, Parser):
            self._parser = new_parser
        elif isinstance(new_parser, str):
            if isinstance(self._parser, Parser):
                self._parser.id = new_parser
            else:
                self._parser = Parser(id=new_parser)
        elif isinstance(new_parser, dict):
            if isinstance(self._parser, Parser):
                self._parser.deserialize(**new_parser)
            else:
                self._parser = Parser(**new_parser)
        elif new_parser is None:
            self._parser = None
        else:
            raise TypeError(f"Can't cast {type(new_parser)} to 'Parser' object of property 'parser'.")

        if isinstance(self._parser, Parser):
            self._parser.reload()

    def serialize(self) -> 'dict':
        return {
            "id": self.id,
            "link": self.link,
            "status": self.status,
            "status_text": self.status_text,
            "internal_id": self.internal_id,
            "title": self.title,
            "description": self.description,
            "date": self.date,
            "parser": self.parser.alias() if self.parser else None,
        }


class Phone(Entity['Phone']):
    """Phone entity representation"""

    endpoint = "phones"

    CREATED = 0
    READY = 1
    FLOOD = 2
    FULL = 3
    BAN = 4

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.number: 'str | None' = kwargs.get("number")
        self.status: 'bool' = kwargs.get("status", Phone.CREATED)
        self.status_text: 'str | None' = kwargs.get("status_text")
        self.internal_id: 'int | None' = kwargs.get("internal_id")
        self.session: 'str | None' = kwargs.get("session")
        self.first_name: 'str | None' = kwargs.get("first_name")
        self.last_name: 'str | None' = kwargs.get("last_name")
        self.code: 'str | None' = kwargs.get("code")
        self._parser: 'TypeParser' = None
        self.parser: 'TypeParser' = kwargs.get("parser")

    @property
    def unique_constraint(self) -> 'dict | None':
        return None

    @property
    def parser(self) -> 'TypeParser':
        """Parser property"""

        return self._parser

    @parser.setter
    def parser(self, new_parser) -> 'None':
        if isinstance(new_parser, Parser):
            self._parser = new_parser
        elif isinstance(new_parser, str):
            if isinstance(self._parser, Parser):
                self._parser.id = new_parser
            else:
                self._parser = Parser(id=new_parser)
        elif isinstance(new_parser, dict):
            if isinstance(self._parser, Parser):
                self._parser.deserialize(**new_parser)
            else:
                self._parser = Parser(**new_parser)
        elif new_parser is None:
            self._parser = None
        else:
            raise TypeError(f"Can't cast {type(new_parser)} to 'Parser' object of property 'parser'.")

        if isinstance(self._parser, Parser):
            self._parser.reload()

    def serialize(self) -> 'dict':
        return {
            "id": self.id,
            "number": self.number,
            "status": self.status,
            "status_text": self.status_text,
            "internal_id": self.internal_id,
            "session": self.session,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "code": self.code,
            "parser": self.parser.alias() if self.parser else None,
        }


class ChatPhone(Entity['ChatPhone']):
    """ChatPhone entity representation"""

    endpoint = "chats-phones"

    def __init__(self, chat: 'TypeChat', phone: 'TypePhone', **kwargs):
        super().__init__(**kwargs)

        self._chat: 'TypeChat' = None
        self.chat: 'TypeChat' = chat
        self._phone: 'TypePhone' = None
        self.phone: 'TypePhone' = phone
        self.is_using: 'bool' = kwargs.get("is_using")

    @property
    def unique_constraint(self) -> 'dict | None':
        return {"chat": self.chat.alias(), "phone": self.phone.alias()}

    @property
    def chat(self) -> 'TypeChat':
        """Chat property"""

        return self._chat

    @chat.setter
    def chat(self, new_chat) -> 'None':
        if isinstance(new_chat, Chat):
            self._chat = new_chat
        elif isinstance(new_chat, str):
            if isinstance(self._chat, Chat):
                self._chat.id = new_chat
            else:
                self._chat = Chat(id=new_chat)
        elif isinstance(new_chat, dict):
            if isinstance(self._chat, Chat):
                self._chat.deserialize(**new_chat)
            else:
                self._chat = Chat(**new_chat)
        elif new_chat is None:
            self._chat = None
        else:
            raise TypeError(f"Can't cast {type(new_chat)} to 'Chat' object of property 'chat'.")

        if isinstance(self._chat, Chat):
            self._chat.reload()

    @property
    def phone(self) -> 'TypePhone':
        """Phone property"""

        return self._phone

    @phone.setter
    def phone(self, new_phone) -> 'None':
        if isinstance(new_phone, Phone):
            self._phone = new_phone
        elif isinstance(new_phone, str):
            if isinstance(self._phone, Phone):
                self._phone.id = new_phone
            else:
                self._phone = Phone(id=new_phone)
        elif isinstance(new_phone, dict):
            if isinstance(self._phone, Phone):
                self._phone.deserialize(**new_phone)
            else:
                self._phone = Phone(**new_phone)
        elif new_phone is None:
            self._phone = None
        else:
            raise TypeError(f"Can't cast {type(new_phone)} to 'Phone' object of property 'phone'.")

        if isinstance(self._phone, Phone):
            self._phone.reload()

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "chat": self.chat.alias(),
            "phone": self.phone.alias(),
            "is_using": self.is_using
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)


class Message(Entity['Message']):
    """Message entity representation"""

    endpoint = "messages"

    def __init__(self, internal_id: 'int', chat: 'TypeChat', **kwargs):
        super().__init__(**kwargs)

        self.internal_id: 'int' = internal_id
        self._chat: 'TypeChat' = None
        self.chat: 'TypeChat' = chat
        self.text: 'str | None' = kwargs.get("text")
        self._member: 'TypeMember | None' = None
        self.member: 'TypeMember | None' = kwargs.get("member")
        self._reply_to: 'TypeMessage | None' = None
        self.reply_to: 'TypeMessage | None' = kwargs.get("reply_to")
        self.is_pinned: 'bool' = kwargs.get("is_pinned", False)
        self.forwarded_from_id: 'int | None' = kwargs.get("forwarded_from_id")
        self.forwarded_fromendpoint: 'str | None' = kwargs.get("forwarded_fromendpoint")
        self.grouped_id: 'int | None' = kwargs.get("grouped_id")
        self.date: 'str | None' = kwargs.get("date")

    @property
    def unique_constraint(self) -> 'dict | None':
        return {'internal_id': self.internal_id, 'chat': self.chat.alias()}

    @property
    def member(self) -> 'TypeMember':
        """Member property"""

        return self._member

    @property
    def chat(self) -> 'TypeChat':
        """Chat property"""

        return self._chat

    @chat.setter
    def chat(self, new_chat) -> 'None':
        if isinstance(new_chat, Chat):
            self._chat = new_chat
        if isinstance(new_chat, str):
            if isinstance(self._chat, Chat):
                self._chat.id = new_chat
            else:
                self._chat = Chat(id=new_chat)
        elif isinstance(new_chat, dict):
            if isinstance(self._chat, Chat):
                self._chat.deserialize(**new_chat)
            else:
                self._chat = Chat(**new_chat)
        elif new_chat is None:
            self._chat = None
        else:
            raise TypeError(f"Can't cast {type(new_chat)} to 'Chat' object of property 'chat'.")

        if isinstance(self._chat, Chat):
            self._chat.reload()

    @member.setter
    def member(self, new_member) -> 'None':
        if isinstance(new_member, Member):
            self._member = new_member
        elif isinstance(new_member, str):
            if isinstance(self._member, Member):
                self._member.id = new_member
            else:
                self._member = Member(id=new_member)
        elif isinstance(new_member, dict):
            if isinstance(self._member, Member):
                self._member.deserialize(**new_member)
            else:
                self._member = Member(**new_member)
        elif new_member is None:
            self._member = None
        else:
            raise TypeError(f"Can't cast {type(new_member)} to 'Member' object of property 'member'.")

        if isinstance(self._member, Member):
            self._member.reload()

    @property
    def reply_to(self) -> 'TypeMessage':
        """Message property"""

        return self._reply_to

    @reply_to.setter
    def reply_to(self, new_reply_to) -> 'None':
        if isinstance(new_reply_to, Message):
            self._reply_to = new_reply_to
        elif isinstance(new_reply_to, str):
            if isinstance(self._reply_to, Message):
                self._reply_to.id = new_reply_to
            else:
                self._reply_to = Message(id=new_reply_to)
        elif isinstance(new_reply_to, dict):
            if isinstance(self._reply_to, Message):
                self._reply_to.deserialize(**new_reply_to)
            else:
                self._reply_to = Message(**new_reply_to)
        elif new_reply_to is None:
            self._reply_to = None
        else:
            raise TypeError(f"Can't cast {type(new_reply_to)} to 'Message' object of property 'reply_to'.")

        if isinstance(self._reply_to, Message):
            self._reply_to.reload()

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "internal_id": self.internal_id,
            "text": self.text,
            "chat": self.chat.alias() if self.chat is not None else None,
            "member": self.member.alias() if self.member is not None else None,
            "reply_to": self.reply_to.alias() if self.reply_to is not None else None,
            "is_pinned": self.is_pinned,
            "forwarded_from_id": self.forwarded_from_id,
            "forwarded_fromendpoint": self.forwarded_fromendpoint,
            "grouped_id": self.grouped_id,
            "date": self.date
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)


class Member(Entity['Member']):
    """Member entity representation"""

    endpoint = "members"

    def __init__(self, internal_id: 'int', **kwargs) -> None:
        super().__init__(**kwargs)

        self.internal_id: 'int' = internal_id
        self.username: 'str | None' = kwargs.get("username")
        self.first_name: 'str | None' = kwargs.get("first_name")
        self.last_name: 'str | None' = kwargs.get("last_name")
        self.phone: 'str | None' = kwargs.get("phone")
        self.about: 'str | None' = kwargs.get("about")

    @property
    def unique_constraint(self) -> 'dict | None':
        return {'internal_id': self.internal_id}

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "internal_id": self.internal_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "about": self.about
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)


class ChatMember(Entity['ChatMember']):
    """ChatMember entity representation"""

    endpoint = "chats-members"

    def __init__(self, chat: 'TypeChat', member: 'TypeMember', **kwargs):
        super().__init__(**kwargs)

        self._chat: 'TypeChat' = None
        self.chat: 'TypeChat' = chat
        self._member: 'TypeMember' = None
        self.member: 'TypeMember' = member
        self.date: 'str | None' = kwargs.get("date")
        self.is_left: 'bool' = kwargs.get("is_left")
        self._roles: 'list[TypeChatMemberRole]' = []
        self.roles: 'list[TypeChatMemberRole]' = kwargs.get("roles")

    @property
    def unique_constraint(self) -> 'dict | None':
        return {'chat': self.chat.alias(), "member": self.member.alias()}

    @property
    def chat(self) -> 'TypeChat':
        """Chat property"""

        return self._chat

    @chat.setter
    def chat(self, new_chat) -> 'None':
        if isinstance(new_chat, Chat):
            self._chat = new_chat
        elif isinstance(new_chat, str):
            if isinstance(self._chat, Chat):
                self._chat.id = new_chat
            else:
                self._chat = Chat(id=new_chat)
        elif isinstance(new_chat, dict):
            if isinstance(self._chat, Chat):
                self._chat.deserialize(**new_chat)
            else:
                self._chat = Chat(**new_chat)
        elif new_chat is None:
            self._chat = None
        else:
            raise TypeError(f"Can't cast {type(new_chat)} to 'Chat' object of property 'chat'.")

        if isinstance(self._chat, Chat):
            self._chat.reload()

    @property
    def member(self) -> 'TypeMember':
        """Member property"""

        return self._member

    @member.setter
    def member(self, new_member) -> 'None':
        if isinstance(new_member, Member):
            self._member = new_member
        elif isinstance(new_member, str):
            if isinstance(self._member, Member):
                self._member.id = new_member
            else:
                self._member = Member(id=new_member)
        elif isinstance(new_member, dict):
            if isinstance(self._member, Member):
                self._member.deserialize(**new_member)
            else:
                self._member = Member(**new_member)
        elif new_member is None:
            self._member = None
        else:
            raise TypeError(f"Can't cast {type(new_member)} to 'Member' object of property 'member'.")

        if isinstance(self._member, Member):
            self._member.reload()

    @property
    def roles(self) -> 'list[TypeChatMemberRole]':
        """ChatMemberRole property"""

        return self._roles

    @roles.setter
    def roles(self, new_roles) -> 'None':
        _roles = []

        if isinstance(new_roles, list):
            for new_role in new_roles:
                if isinstance(new_role, ChatMemberRole):
                    _roles.append(new_role)
                elif isinstance(new_role, str):
                    _roles.append(ChatMemberRole(id=new_role))
                elif isinstance(new_role, dict):
                    _roles.append(ChatMemberRole(**new_role))
                else:
                    raise TypeError(f"Can't cast {type(new_role)} to 'ChatMemberRole' object of property 'roles'.")

        self._roles = _roles

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "chat": self.chat.alias() if self.chat is not None else None,
            "member": self.member.alias() if self.member is not None else None,
            "date": self.date,
            "is_left": self.is_left,
            "roles": [role.alias() for role in self.roles],
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)


class ChatMemberRole(Entity['ChatMemberRole']):
    """ChatMemberRole entity representation"""

    endpoint = "chats-members-roles"

    def __init__(self, member: 'TypeChatMember', **kwargs):
        super().__init__(**kwargs)

        self._member: 'TypeChatMember' = None
        self.member: 'TypeChatMember' = member
        self.title: 'str' = kwargs.get("title", "Участник")
        self.code: 'str' = kwargs.get("code", "member")

    @property
    def unique_constraint(self) -> 'dict | None':
        return {'member': self.member.alias(), 'title': self.title, 'code': self.code}

    @property
    def member(self) -> 'TypeChatMember':
        """ChatMember property"""

        return self._member

    @member.setter
    def member(self, new_member) -> 'None':
        if isinstance(new_member, ChatMember):
            self._member = new_member
        elif isinstance(new_member, str):
            if isinstance(self._member, ChatMember):
                self._member.id = new_member
            else:
                self._member = ChatMember(id=new_member)
        elif isinstance(new_member, dict):
            if isinstance(self._member, ChatMember):
                self._member.deserialize(**new_member)
            else:
                self._member = ChatMember(**new_member)
        elif new_member is None:
            self._member = None
        else:
            raise TypeError(f"Can't cast {type(new_member)} to 'ChatMember' object of property 'member'.")

        if isinstance(self._member, ChatMember):
            self._member.reload()

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "member": self.member.alias() if self.member is not None else None,
            "title": self.title,
            "code": self.code
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)


class ChatMedia(Media['ChatMedia']):
    """ChatMedia entity representation"""

    endpoint = "chats-medias"

    def __init__(self, internal_id: 'int', chat: 'TypeChat' = None, **kwargs):
        super().__init__(**kwargs)

        self._chat: 'TypeChat' = None
        self.chat: 'TypeChat' = chat
        self.internal_id: 'int' = internal_id
        self.path: 'str | None' = kwargs.get("path")
        self.date: 'str | None' = kwargs.get("date")

    @property
    def unique_constraint(self) -> 'dict | None':
        return {"internal_id": self.internal_id}

    @property
    def chat(self) -> 'TypeChat':
        """Chat property"""

        return self._chat

    @chat.setter
    def chat(self, new_chat) -> 'None':
        if isinstance(new_chat, Chat):
            self._chat = new_chat
        elif isinstance(new_chat, str):
            if isinstance(self._chat, Chat):
                self._chat.id = new_chat
            else:
                self._chat = Chat(id=new_chat)
        elif isinstance(new_chat, dict):
            if isinstance(self._chat, Chat):
                self._chat.deserialize(**new_chat)
            else:
                self._chat = Chat(**new_chat)
        elif new_chat is None:
            self._chat = None
        else:
            raise TypeError(f"Can't cast {type(new_chat)} to 'Chat' object of property 'chat'.")

        if isinstance(self._chat, Chat):
            self._chat.reload()

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "chat": self.chat.alias(),
            "internal_id": self.internal_id,
            "path": self.path,
            "date": self.date,
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)


class MemberMedia(Media['MemberMedia']):
    """MemberMedia entity representation"""

    endpoint = "members-medias"

    def __init__(self, internal_id: 'int', member: 'TypeMember', **kwargs):
        super().__init__(**kwargs)

        self._member: 'TypeMember | None' = None
        self.member: 'TypeMember | None' = member
        self.internal_id: 'int' = internal_id
        self.path: 'str | None' = kwargs.get("path")
        self.date: 'str | None' = kwargs.get("date")

    @property
    def unique_constraint(self) -> 'dict | None':
        return {'internal_id': self.internal_id}

    @property
    def member(self) -> 'TypeMember':
        """Member property"""

        return self._member

    @member.setter
    def member(self, new_member) -> 'None':
        if isinstance(new_member, Member):
            self._member = new_member
        elif isinstance(new_member, str):
            if isinstance(self._member, Member):
                self._member.id = new_member
            else:
                self._member = Member(id=new_member)
        elif isinstance(new_member, dict):
            if isinstance(self._member, Member):
                self._member.deserialize(**new_member)
            else:
                self._member = Member(**new_member)
        elif new_member is None:
            self._member = None
        else:
            raise TypeError(f"Can't cast {type(new_member)} to 'Member' object of property 'member'.")

        if isinstance(self._member, Member):
            self._member.reload()

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "member": self.member.alias() if self.member is not None else None,
            "internal_id": self.internal_id,
            "path": self.path,
            "date": self.date,
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)


class MessageMedia(Media['MessageMedia']):
    """MessageMedia entity representation"""

    endpoint = "messages-medias"

    def __init__(self, internal_id: 'int', message: 'TypeMessage', **kwargs) -> None:
        super().__init__(**kwargs)

        self._message: 'TypeMessage' = None
        self.message: 'TypeMessage' = message
        self.internal_id: 'int' = internal_id
        self.path: 'str | None' = kwargs.get("path")
        self.date: 'str | None' = kwargs.get("date")

    @property
    def unique_constraint(self) -> 'dict | None':
        return {'internal_id': self.internal_id}

    @property
    def message(self) -> 'TypeMessage':
        """Message property"""

        return self._message

    @message.setter
    def message(self, new_message) -> 'None':
        if isinstance(new_message, Message):
            self._message = new_message
        if isinstance(new_message, str):
            if isinstance(self._message, Message):
                self._message.id = new_message
            else:
                self._message = Message(id=new_message)
        elif isinstance(new_message, dict):
            if isinstance(self._message, Message):
                self._message.deserialize(**new_message)
            else:
                self._message = Message(**new_message)
        elif new_message is None:
            self._message = None
        else:
            raise TypeError(f"Can't cast {type(new_message)} to 'Message' object of property 'message'.")

        if isinstance(self._message, Message):
            self._message.reload()

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "message": self.message.alias() if self.message is not None else None,
            "internal_id": self.internal_id,
            "path": self.path,
            "date": self.date,
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)


TypeEntity = Entity
TypeMedia = Media
TypeHost = Host
TypeParser = Parser
TypeChat = Chat
TypePhone = Phone
TypeParser = Parser
TypeMessageMedia = MessageMedia
TypeMessage = Message
TypeMemberMedia = MemberMedia
TypeMember = Member
TypeChatMemberRole = ChatMemberRole
TypeChatMember = ChatMember
TypeChatMedia = ChatMedia
TypeChatPhone = ChatPhone
