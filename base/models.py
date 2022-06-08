"""Collection of entity representations"""

from abc import ABCMeta, abstractmethod
from typing import Generic, TypeVar
import math
from telethon.client import downloads
from base.utils import ApiService

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
    def __endpoint__(self) -> str:
        """Название сущности в пути API."""

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

        entities = ApiService().get(cls.__endpoint__, **kwargs)

        return [cls(**entity) for entity in entities["results"]]

    def reload(self) -> 'T':
        """Обновляет текущую сущность из API."""

        if not self.id:
            raise ValueError("Entity hasn't id")

        entity = ApiService().get(self.__class__.__endpoint__, id=self.id, force=True)

        self.deserialize(**entity)

        return self

    def save(self) -> 'T':
        """Создает/изменяет сущность в API."""

        entity = ApiService().set(self.__class__.__endpoint__, **self.serialize())

        self.deserialize(**entity)

        return self

    def delete(self) -> 'None':
        """
        Удаляет сущность из API.
        """

        ApiService().delete(self.__class__.__endpoint__, self.id)


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
                self.__class__.__endpoint__,
                self.id,
                str(tg_media.id) + extension,
                chunk,
                chunk_number,
                chunk_size,
                total_chunks,
                size
            )

            chunk_number += 1


class RelationProperty(object):
    __name = None
    __cls = None
    __value = None

    def __init__(self, name, cls: 'TypeEntity', default=None):
        self.__name = name
        self.__cls = cls
        self.__value = default

    def __get__(self, instance, owner=None):
        if self.__value is None:
            return Entity()

        self.__value.reload()

        return self.__value

    def __set__(self, instance, value):
        if isinstance(value, self.__cls):
            self.__value = value
        elif isinstance(value, str):
            value = self.__cls(id=value)

            if self.__value != value:
                self.__value = value
        elif isinstance(value, dict):
            if isinstance(self.__value, self.__cls):
                self.__value.deserialize(**value)
            else:
                self.__value = self.__cls(**value)
        elif value is None:
            self.__value = None
        else:
            raise TypeError(
                f"Can't cast {type(value)} to '{self.__cls.__name__}' object in property {self.__name} of {instance}."
            )


class Host(Entity['Host']):
    """Host entity representation"""

    __endpoint__ = "hosts"

    public_ip: 'str' = None
    local_ip: 'str' = None
    name: 'str' = None

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

    __endpoint__ = "parsers"

    NEW = 0
    IN_PROGRESS = 1
    FAILED = 2

    host: 'TypeHost' = RelationProperty("host", Host)
    status: 'int' = NEW
    api_id: 'str' = None
    api_hash: 'str' = None

    def serialize(self) -> 'dict':
        return {
            "id": self.id,
            "host": self.host.alias(),
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

    __endpoint__ = "chats"

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
    parser: 'TypeHost' = RelationProperty("parser", Parser)

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
            "parser": self.parser.alias(),
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


class ChatMedia(Media['ChatMedia']):
    """ChatMedia entity representation"""

    __endpoint__ = "chats-medias"

    chat: 'TypeChat' = RelationProperty("chat", Chat)
    internal_id: 'int' = None
    path: 'str' = None
    date: 'str' = None

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "chat": self.chat.alias(),
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


class Phone(Entity['Phone']):
    """Phone entity representation"""

    __endpoint__ = "phones"

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
    parser: 'TypeParser' = RelationProperty("parser", Parser)
    api: 'dict' = None

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
            "parser": self.parser.alias(),
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

    __endpoint__ = "chats-phones"

    chat: 'TypeChat' = RelationProperty("chat", Chat)
    phone: 'TypePhone' = RelationProperty("phone", Phone)
    is_using: 'bool' = False

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


class Member(Entity['Member']):
    """Member entity representation"""

    __endpoint__ = "members"

    internal_id: 'int' = None
    username: 'str' = None
    first_name: 'str' = None
    last_name: 'str' = None
    phone: 'str' = None
    about: 'str' = None

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


class MemberMedia(Media['MemberMedia']):
    """MemberMedia entity representation"""

    __endpoint__ = "members-medias"

    member: 'TypeMember' = RelationProperty("member", Member)
    internal_id: 'int' = None
    path: 'str' = None
    date: 'str' = None

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "member": self.member.alias(),
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


class ChatMember(Entity['ChatMember']):
    """ChatMember entity representation"""

    __endpoint__ = "chats-members"

    chat: 'TypeChat' = RelationProperty("chat", Chat)
    member: 'TypeMember' = RelationProperty("member", Member)
    date: 'str' = None
    is_left: 'bool' = False
    _roles: 'list[TypeChatMemberRole]' = []
    roles: 'list[TypeChatMemberRole]' = None

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
            "chat": self.chat.alias(),
            "member": self.member.alias(),
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

    __endpoint__ = "chats-members-roles"

    member: 'TypeMember' = RelationProperty("member", ChatMember)
    title: 'str' = "Участник"
    code: 'str' = "member"

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "member": self.member.alias(),
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


class Message(Entity['Message']):
    """Message entity representation"""

    __endpoint__ = "messages"

    internal_id: 'int' = None
    chat: 'TypeChat' = RelationProperty("chat", Chat)
    text: 'str' = None
    member: 'TypeMember' = RelationProperty("member", ChatMember)
    reply_to: 'TypeMember' = RelationProperty("reply_to", 'Message')
    is_pinned: 'bool' = False
    forwarded_from_id: 'int' = None
    forwarded_from__endpoint__: 'str' = None
    grouped_id: 'int' = None
    date: 'str' = None

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "internal_id": self.internal_id,
            "text": self.text,
            "chat": self.chat.alias(),
            "member": self.member.alias(),
            "reply_to": self.reply_to.alias(),
            "is_pinned": self.is_pinned,
            "forwarded_from_id": self.forwarded_from_id,
            "forwarded_from__endpoint__": self.forwarded_from__endpoint__,
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
        self.forwarded_from__endpoint__ = kwargs.get("forwarded_from__endpoint__")
        self.grouped_id = kwargs.get("grouped_id")
        self.date = kwargs.get("date")

        return self


class MessageMedia(Media['MessageMedia']):
    """MessageMedia entity representation"""

    __endpoint__ = "messages-medias"

    message: 'TypeMessage' = RelationProperty("message", Message)
    internal_id: 'int' = None
    path: 'str' = None
    date: 'str' = None

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
