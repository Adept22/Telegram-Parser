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

    def __init__(self, **kwargs):
        self.deserialize(**kwargs)

    def __str__(self):
        return f"<{self} object ({self.id})>"

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
    def id(self, new_value) -> 'None':
        """Сеттер идентификатора сущности."""

        self._id = new_value

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

    @abstractmethod
    def deserialize(self, **kwargs) -> 'T':
        """Десериализация сущности. Т.е. из `dict` в `self`"""

        raise NotImplementedError

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

    public_ip: 'str' = None
    local_ip: 'str' = None
    name: 'str' = None

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

    def deserialize(self, **kwargs) -> 'Chat':
        self.id = kwargs.get('id')
        self.public_ip = kwargs.get('public_ip')
        self.local_ip = kwargs.get('local_ip')
        self.name = kwargs.get('name')

        return self


class Parser(Entity['Parser']):
    """Parser entity representation"""

    endpoint = "parsers"

    NEW = 0
    IN_PROGRESS = 1
    FAILED = 2

    _host: 'TypeHost' = None
    host: 'TypeHost' = None
    status: 'int' = NEW
    api_id: 'str' = None
    api_hash: 'str' = None

    @property
    def unique_constraint(self) -> 'dict | None':
        return None

    @property
    def host(self) -> 'TypeHost':
        """Host property"""

        return self._host

    @host.setter
    def host(self, new_value) -> 'None':
        if isinstance(new_value, Host):
            self._host = new_value
        elif isinstance(new_value, str):
            if isinstance(self._host, Host):
                self._host.id = new_value
            else:
                self._host = Host(id=new_value)
        elif isinstance(new_value, dict):
            if isinstance(self._host, Host):
                self._host.deserialize(**new_value)
            else:
                self._host = Host(**new_value)
        elif new_value is None:
            self._host = None
        else:
            raise TypeError(
                f"Can't cast {type(new_value)} to 'Host' object of property 'host' in {self}."
            )

        if isinstance(self._host, Host):
            self._host.reload()

    def serialize(self) -> 'dict':
        return {
            "id": self.id,
            "host": self.host.alias() if isinstance(self.host, Host) else None,
            "status": self.status,
            "api_id": self.api_id,
            "api_hash": self.api_hash
        }

    def deserialize(self, **kwargs) -> 'TypeParser':
        self.id = kwargs.get('id')
        self.host = kwargs.get('host')
        self.status = kwargs.get('status')
        self.api_id = kwargs.get('api_id')
        self.api_hash = kwargs.get('api_hash')

        return self


class Chat(Entity['Chat']):
    """Chat entity representation"""

    endpoint = "chats"

    CREATED = 0
    AVAILABLE = 1
    MONITORING = 2
    FAILED = 3

    link: 'str' = None
    status: 'int' = CREATED
    status_text: 'str' = None
    internal_id: 'int' = None
    title: 'str' = None
    description: 'str' = None
    date: 'str' = None
    _parser: 'TypeParser' = None
    parser: 'TypeParser' = None

    @property
    def unique_constraint(self) -> 'dict | None':
        return None

    @property
    def parser(self) -> 'TypeParser':
        """Parser property"""

        return self._parser

    @parser.setter
    def parser(self, new_value) -> 'None':
        if isinstance(new_value, Parser):
            self._parser = new_value
        elif isinstance(new_value, str):
            if isinstance(self._parser, Parser):
                self._parser.id = new_value
            else:
                self._parser = Parser(id=new_value)
        elif isinstance(new_value, dict):
            if isinstance(self._parser, Parser):
                self._parser.deserialize(**new_value)
            else:
                self._parser = Parser(**new_value)
        elif new_value is None:
            self._parser = None
        else:
            raise TypeError(
                f"Can't cast {type(new_value)} to 'Parser' object of property 'parser' in {self}."
            )

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
            "parser": self.parser.alias() if isinstance(self.parser, Parser) else None,
        }

    def deserialize(self, **kwargs) -> 'Chat':
        self.id = kwargs.get('id')
        self.link = kwargs.get('link')
        self.status = kwargs.get('status')
        self.status_text = kwargs.get('status_text')
        self.internal_id = kwargs.get('internal_id')
        self.title = kwargs.get('title')
        self.description = kwargs.get('description')
        self.date = kwargs.get('date')
        self.parser = kwargs.get('parser')

        return self


class Phone(Entity['Phone']):
    """Phone entity representation"""

    endpoint = "phones"

    CREATED = 0
    READY = 1
    FLOOD = 2
    FULL = 3
    BAN = 4

    number: 'str' = None
    status: 'bool' = None
    status_text: 'str' = None
    internal_id: 'int' = None
    session: 'str' = None
    first_name: 'str' = None
    last_name: 'str' = None
    code: 'str' = None
    _parser: 'TypeParser' = None
    parser: 'TypeParser' = None
    api: 'dict' = None

    @property
    def unique_constraint(self) -> 'dict | None':
        return None

    @property
    def parser(self) -> 'TypeParser':
        """Parser property"""

        return self._parser

    @parser.setter
    def parser(self, new_value) -> 'None':
        if isinstance(new_value, Parser):
            self._parser = new_value
        elif isinstance(new_value, str):
            if isinstance(self._parser, Parser):
                self._parser.id = new_value
            else:
                self._parser = Parser(id=new_value)
        elif isinstance(new_value, dict):
            if isinstance(self._parser, Parser):
                self._parser.deserialize(**new_value)
            else:
                self._parser = Parser(**new_value)
        elif new_value is None:
            self._parser = None
        else:
            raise TypeError(
                f"Can't cast {type(new_value)} to 'Parser' object of property 'parser' in {self}."
            )

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
            "api": self.api
        }

    def deserialize(self, **kwargs) -> 'TypePhone':
        self.id = kwargs.get("id")
        self.number = kwargs.get("number")
        self.status = kwargs.get("status")
        self.status_text = kwargs.get("status_text")
        self.parser = kwargs.get('parser')
        self.internal_id = kwargs.get("internal_id")
        self.session = kwargs.get("session")
        self.first_name = kwargs.get("first_name")
        self.last_name = kwargs.get("last_name")
        self.code = kwargs.get("code")
        self.api = kwargs.get("api")

        return self


class ChatPhone(Entity['ChatPhone']):
    """ChatPhone entity representation"""

    endpoint = "chats-phones"

    _chat: 'TypeChat' = None
    chat: 'TypeChat' = None
    _phone: 'TypePhone' = None
    phone: 'TypePhone' = None
    is_using: 'bool' = False

    @property
    def unique_constraint(self) -> 'dict | None':
        return {"chat": self.chat.alias(), "phone": self.phone.alias()}

    @property
    def chat(self) -> 'TypeChat':
        """Chat property"""

        return self._chat

    @chat.setter
    def chat(self, new_value) -> 'None':
        if isinstance(new_value, Chat):
            self._chat = new_value
        elif isinstance(new_value, str):
            if isinstance(self._chat, Chat):
                self._chat.id = new_value
            else:
                self._chat = Chat(id=new_value)
        elif isinstance(new_value, dict):
            if isinstance(self._chat, Chat):
                self._chat.deserialize(**new_value)
            else:
                self._chat = Chat(**new_value)
        elif new_value is None:
            self._chat = None
        else:
            raise TypeError(
                f"Can't cast {type(new_value)} to 'Chat' object of property 'chat' in {self}."
            )

        if isinstance(self._chat, Chat):
            self._chat.reload()

    @property
    def phone(self) -> 'TypePhone':
        """Phone property"""

        return self._phone

    @phone.setter
    def phone(self, new_value) -> 'None':
        if isinstance(new_value, Phone):
            self._phone = new_value
        elif isinstance(new_value, str):
            if isinstance(self._phone, Phone):
                self._phone.id = new_value
            else:
                self._phone = Phone(id=new_value)
        elif isinstance(new_value, dict):
            if isinstance(self._phone, Phone):
                self._phone.deserialize(**new_value)
            else:
                self._phone = Phone(**new_value)
        elif new_value is None:
            self._phone = None
        else:
            raise TypeError(
                f"Can't cast {type(new_value)} to 'Phone' object of property 'phone' in {self}."
            )

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

    def deserialize(self, **kwargs) -> 'ChatPhone':
        self.id = kwargs.get("id")
        self.chat = kwargs.get("chat")
        self.phone = kwargs.get("phone")
        self.is_using = kwargs.get("is_using", False)

        return self


class Message(Entity['Message']):
    """Message entity representation"""

    endpoint = "messages"

    internal_id: 'int' = None
    _chat: 'TypeChat' = None
    chat: 'TypeChat' = None
    text: 'str' = None
    _member: 'TypeMember' = None
    member: 'TypeMember' = None
    _reply_to: 'TypeMessage' = None
    reply_to: 'TypeMessage' = None
    is_pinned: 'bool' = False
    forwarded_from_id: 'int' = None
    forwarded_fromendpoint: 'str' = None
    grouped_id: 'int' = None
    date: 'str' = None

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
    def chat(self, new_value) -> 'None':
        if isinstance(new_value, Chat):
            self._chat = new_value
        if isinstance(new_value, str):
            if isinstance(self._chat, Chat):
                self._chat.id = new_value
            else:
                self._chat = Chat(id=new_value)
        elif isinstance(new_value, dict):
            if isinstance(self._chat, Chat):
                self._chat.deserialize(**new_value)
            else:
                self._chat = Chat(**new_value)
        elif new_value is None:
            self._chat = None
        else:
            raise TypeError(
                f"Can't cast {type(new_value)} to 'Chat' object of property 'chat' in {self}."
            )

        if isinstance(self._chat, Chat):
            self._chat.reload()

    @member.setter
    def member(self, new_value) -> 'None':
        if isinstance(new_value, ChatMember):
            self._member = new_value
        elif isinstance(new_value, str):
            if isinstance(self._member, ChatMember):
                self._member.id = new_value
            else:
                self._member = ChatMember(id=new_value)
        elif isinstance(new_value, dict):
            if isinstance(self._member, ChatMember):
                self._member.deserialize(**new_value)
            else:
                self._member = ChatMember(**new_value)
        elif new_value is None:
            self._member = None
        else:
            raise TypeError(
                f"Can't cast {type(new_value)} to 'ChatMember' object of property 'member' in {self}."
            )

        if isinstance(self._member, ChatMember):
            self._member.reload()

    @property
    def reply_to(self) -> 'TypeMessage':
        """Message property"""

        return self._reply_to

    @reply_to.setter
    def reply_to(self, new_value_to) -> 'None':
        if isinstance(new_value_to, Message):
            self._reply_to = new_value_to
        elif isinstance(new_value_to, str):
            if isinstance(self._reply_to, Message):
                self._reply_to.id = new_value_to
            else:
                self._reply_to = Message(id=new_value_to)
        elif isinstance(new_value_to, dict):
            if isinstance(self._reply_to, Message):
                self._reply_to.deserialize(**new_value_to)
            else:
                self._reply_to = Message(**new_value_to)
        elif new_value_to is None:
            self._reply_to = None
        else:
            raise TypeError(f"Can't cast {type(new_value_to)} to 'Message' object of property 'reply_to' in {self}.")

        if isinstance(self._reply_to, Message):
            self._reply_to.reload()

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "internal_id": self.internal_id,
            "text": self.text,
            "chat": self.chat.alias() if isinstance(self.chat, Chat) is not None else None,
            "member": self.member.alias() if isinstance(self.member, ChatMember) is not None else None,
            "reply_to": self.reply_to.alias() if isinstance(self.reply_to, Message) is not None else None,
            "is_pinned": self.is_pinned,
            "forwarded_from_id": self.forwarded_from_id,
            "forwarded_fromendpoint": self.forwarded_fromendpoint,
            "grouped_id": self.grouped_id,
            "date": self.date
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, **kwargs) -> 'TypeMessage':
        self.id = kwargs.get("id")
        self.internal_id = kwargs.get("internal_id")
        self.text = kwargs.get("text")
        self.chat = kwargs.get("chat")
        self.member = kwargs.get("member")
        self.reply_to = kwargs.get("reply_to")
        self.is_pinned = kwargs.get("is_pinned")
        self.forwarded_from_id = kwargs.get("forwarded_from_id")
        self.forwarded_fromendpoint = kwargs.get("forwarded_fromendpoint")
        self.grouped_id = kwargs.get("grouped_id")
        self.date = kwargs.get("date")

        return self


class Member(Entity['Member']):
    """Member entity representation"""

    endpoint = "members"

    internal_id: 'int' = None
    username: 'str' = None
    first_name: 'str' = None
    last_name: 'str' = None
    phone: 'str' = None
    about: 'str' = None

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

    def deserialize(self, **kwargs) -> 'TypeMember':
        self.id = kwargs.get("id")
        self.internal_id = kwargs.get("internal_id")
        self.username = kwargs.get("username")
        self.first_name = kwargs.get("first_name")
        self.last_name = kwargs.get("last_name")
        self.phone = kwargs.get("phone")
        self.about = kwargs.get("about")

        return self


class ChatMember(Entity['ChatMember']):
    """ChatMember entity representation"""

    endpoint = "chats-members"

    _chat: 'TypeChat' = None
    chat: 'TypeChat' = None
    _member: 'TypeMember' = None
    member: 'TypeMember' = None
    date: 'str' = None
    is_left: 'bool' = False
    _roles: 'list[TypeChatMemberRole]' = []
    roles: 'list[TypeChatMemberRole]' = None

    @property
    def unique_constraint(self) -> 'dict | None':
        return {'chat': self.chat.alias(), "member": self.member.alias()}

    @property
    def chat(self) -> 'TypeChat':
        """Chat property"""

        return self._chat

    @chat.setter
    def chat(self, new_value) -> 'None':
        if isinstance(new_value, Chat):
            self._chat = new_value
        elif isinstance(new_value, str):
            if isinstance(self._chat, Chat):
                self._chat.id = new_value
            else:
                self._chat = Chat(id=new_value)
        elif isinstance(new_value, dict):
            if isinstance(self._chat, Chat):
                self._chat.deserialize(**new_value)
            else:
                self._chat = Chat(**new_value)
        elif new_value is None:
            self._chat = None
        else:
            raise TypeError(
                f"Can't cast {type(new_value)} to 'Chat' object of property 'chat' in {self}."
            )

        if isinstance(self._chat, Chat):
            self._chat.reload()

    @property
    def member(self) -> 'TypeMember':
        """Member property"""

        return self._member

    @member.setter
    def member(self, new_value) -> 'None':
        if isinstance(new_value, Member):
            self._member = new_value
        elif isinstance(new_value, str):
            if isinstance(self._member, Member):
                self._member.id = new_value
            else:
                self._member = Member(id=new_value)
        elif isinstance(new_value, dict):
            if isinstance(self._member, Member):
                self._member.deserialize(**new_value)
            else:
                self._member = Member(**new_value)
        elif new_value is None:
            self._member = None
        else:
            raise TypeError(
                f"Can't cast {type(new_value)} to 'Member' object of property 'member' in {self}."
            )

        if isinstance(self._member, Member):
            self._member.reload()

    @property
    def roles(self) -> 'list[TypeChatMemberRole]':
        """ChatMemberRole property"""

        return self._roles

    @roles.setter
    def roles(self, new_value) -> 'None':
        _roles = []

        if isinstance(new_value, list):
            for new_value in new_value:
                if isinstance(new_value, ChatMemberRole):
                    _roles.append(new_value)
                elif isinstance(new_value, str):
                    _roles.append(ChatMemberRole(id=new_value))
                elif isinstance(new_value, dict):
                    _roles.append(ChatMemberRole(**new_value))
                else:
                    raise TypeError(
                        f"Can't cast {type(new_value)} to 'ChatMemberRole' object of property 'roles' in {self}."
                    )

        self._roles = _roles

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "chat": self.chat.alias() if isinstance(self.chat, Chat) is not None else None,
            "member": self.member.alias() if isinstance(self.member, Member) is not None else None,
            "date": self.date,
            "is_left": self.is_left,
            "roles": [role.alias() for role in self.roles if isinstance(role, ChatMemberRole)],
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, **kwargs) -> 'TypeChatMember':
        self.id = kwargs.get("id")
        self.chat = kwargs.get("chat")
        self.member = kwargs.get("member")
        self.date = kwargs.get("date")
        self.is_left = kwargs.get("is_left")
        self.roles = kwargs.get("roles")

        return self


class ChatMemberRole(Entity['ChatMemberRole']):
    """ChatMemberRole entity representation"""

    endpoint = "chats-members-roles"

    _member: 'TypeChatMember' = None
    member: 'TypeChatMember' = None
    title: 'str' = "Участник"
    code: 'str' = "member"

    @property
    def unique_constraint(self) -> 'dict | None':
        return {'member': self.member.alias(), 'title': self.title, 'code': self.code}

    @property
    def member(self) -> 'TypeChatMember':
        """ChatMember property"""

        return self._member

    @member.setter
    def member(self, new_value) -> 'None':
        if isinstance(new_value, ChatMember):
            self._member = new_value
        elif isinstance(new_value, str):
            if isinstance(self._member, ChatMember):
                self._member.id = new_value
            else:
                self._member = ChatMember(id=new_value)
        elif isinstance(new_value, dict):
            if isinstance(self._member, ChatMember):
                self._member.deserialize(**new_value)
            else:
                self._member = ChatMember(**new_value)
        elif new_value is None:
            self._member = None
        else:
            raise TypeError(
                f"Can't cast {type(new_value)} to 'ChatMember' object of property 'member' in {self}."
            )

        if isinstance(self._member, ChatMember):
            self._member.reload()

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "member": self.member.alias() if isinstance(self.member, ChatMember) is not None else None,
            "title": self.title,
            "code": self.code
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, **kwargs) -> 'TypeChatMemberRole':
        self.id = kwargs.get("id")
        self.member = kwargs.get("member")
        self.title = kwargs.get("title")
        self.code = kwargs.get("code")

        return self


class ChatMedia(Media['ChatMedia']):
    """ChatMedia entity representation"""

    endpoint = "chats-medias"

    _chat: 'TypeChat' = None
    chat: 'TypeChat' = None
    internal_id: 'int' = None
    path: 'str' = None
    date: 'str' = None

    @property
    def unique_constraint(self) -> 'dict | None':
        return {"internal_id": self.internal_id}

    @property
    def chat(self) -> 'TypeChat':
        """Chat property"""

        return self._chat

    @chat.setter
    def chat(self, new_value) -> 'None':
        if isinstance(new_value, Chat):
            self._chat = new_value
        elif isinstance(new_value, str):
            if isinstance(self._chat, Chat):
                self._chat.id = new_value
            else:
                self._chat = Chat(id=new_value)
        elif isinstance(new_value, dict):
            if isinstance(self._chat, Chat):
                self._chat.deserialize(**new_value)
            else:
                self._chat = Chat(**new_value)
        elif new_value is None:
            self._chat = None
        else:
            raise TypeError(
                f"Can't cast {type(new_value)} to 'Chat' object of property 'chat' in {self}."
            )

        if isinstance(self._chat, Chat):
            self._chat.reload()

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "chat": self.chat.alias() if isinstance(self.chat, Chat) else None,
            "internal_id": self.internal_id,
            "path": self.path,
            "date": self.date,
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, **kwargs) -> 'TypeChatMedia':
        self.id = kwargs.get("id")
        self.chat = kwargs.get("chat")
        self.internal_id = kwargs.get("internal_id")
        self.path = kwargs.get("path")
        self.date = kwargs.get("date")

        return self


class MemberMedia(Media['MemberMedia']):
    """MemberMedia entity representation"""

    endpoint = "members-medias"

    _member: 'TypeMember' = None
    member: 'TypeMember' = None
    internal_id: 'int' = None
    path: 'str' = None
    date: 'str' = None

    @property
    def unique_constraint(self) -> 'dict | None':
        return {'internal_id': self.internal_id}

    @property
    def member(self) -> 'TypeMember':
        """Member property"""

        return self._member

    @member.setter
    def member(self, new_value) -> 'None':
        if isinstance(new_value, Member):
            self._member = new_value
        elif isinstance(new_value, str):
            if isinstance(self._member, Member):
                self._member.id = new_value
            else:
                self._member = Member(id=new_value)
        elif isinstance(new_value, dict):
            if isinstance(self._member, Member):
                self._member.deserialize(**new_value)
            else:
                self._member = Member(**new_value)
        elif new_value is None:
            self._member = None
        else:
            raise TypeError(
                f"Can't cast {type(new_value)} to 'Member' object of property 'member' in {self}."
            )

        if isinstance(self._member, Member):
            self._member.reload()

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "member": self.member.alias() if isinstance(self.member, Member) is not None else None,
            "internal_id": self.internal_id,
            "path": self.path,
            "date": self.date,
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, **kwargs) -> 'TypeMemberMedia':
        self.id = kwargs.get("id")
        self.internal_id = kwargs.get("internal_id")
        self.member = kwargs.get("member")
        self.path = kwargs.get("path")
        self.date = kwargs.get("date")

        return self


class MessageMedia(Media['MessageMedia']):
    """MessageMedia entity representation"""

    endpoint = "messages-medias"

    _message: 'TypeMessage' = None
    message: 'TypeMessage' = None
    internal_id: 'int' = None
    path: 'str' = None
    date: 'str' = None

    @property
    def unique_constraint(self) -> 'dict | None':
        return {'internal_id': self.internal_id}

    @property
    def message(self) -> 'TypeMessage':
        """Message property"""

        return self._message

    @message.setter
    def message(self, new_value) -> 'None':
        if isinstance(new_value, Message):
            self._message = new_value
        if isinstance(new_value, str):
            if isinstance(self._message, Message):
                self._message.id = new_value
            else:
                self._message = Message(id=new_value)
        elif isinstance(new_value, dict):
            if isinstance(self._message, Message):
                self._message.deserialize(**new_value)
            else:
                self._message = Message(**new_value)
        elif new_value is None:
            self._message = None
        else:
            raise TypeError(
                f"Can't cast {type(new_value)} to 'Message' object of property 'message' in {self}."
            )

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

    def deserialize(self, **kwargs) -> 'TypeMessageMedia':
        self.id = kwargs.get("id")
        self.internal_id = kwargs.get("internal_id")
        self.message = kwargs.get("message")
        self.path = kwargs.get("path")
        self.date = kwargs.get("date")

        return self


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
