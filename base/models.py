from abc import ABCMeta, abstractmethod
from typing import Generic, TypeVar
import math
from telethon.client import downloads
from base.utils import ApiService
from base import exceptions

T = TypeVar('T', bound='Entity')


class Entity(Generic[T], metaclass=ABCMeta):
    """Base class for entities"""

    def __init__(self, id: 'str' = None):
        self._id = id

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

    @abstractmethod
    def deserialize(self, **kwargs) -> 'T':
        """Десериализация сущности. Т.е. из `dict` в `self`"""

        raise NotImplementedError

    @classmethod
    def find(cls, _dict) -> 'list[T]':
        """Возвращает отфильтрованный и отсортированный список сущностей"""

        entities = ApiService().get(cls.endpoint, **_dict)
        return [cls(**entity) for entity in entities]

    def reload(self) -> 'T':
        """Обновляет текущую сущность из API."""

        if not self.id:
            raise ValueError("Entity hasn't id")

        entity = ApiService().get(self.__class__.endpoint, id=self.id)

        self.deserialize(**entity)

        return self

    def save(self) -> 'T':
        """Создает/изменяет сущность в API."""

        try:
            entity = ApiService().set(self.__class__.endpoint, self.serialize())
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

    def deserialize(self, **kwargs) -> 'Chat':
        self.id = kwargs['id']
        self.public_ip = kwargs['public_ip']
        self.local_ip = kwargs['local_ip']
        self.name = kwargs['name']
        return self


class Parser(Entity['Parser']):
    """Parser entity representation"""

    endpoint = "parsers"

    NEW = 0
    IN_PROGRESS = 1
    FAILED = 2

    def __init__(self, host: 'TypeHost', status: 'int', api_id: 'str', api_hash: 'str', **kwargs):
        super().__init__(**kwargs)

        self._host: 'TypeHost' = None
        self.host: 'str' = host
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
        if isinstance(new_host, str):
            if isinstance(self._host, Host):
                self._host.id = new_host
            else:
                self._host = Host(new_host)
        elif isinstance(new_host, dict):
            if isinstance(self._host, Host):
                self._host.deserialize(**new_host)
            else:
                self._host = Host(**new_host)

        if isinstance(self._host, Host):
            self._host.reload()

    def serialize(self) -> 'dict':
        return {
            "id": self.id,
            "host": self.host.serialize() if self.host else None,
            "status": self.status,
            "api_id": self.api_id, 
            "api_hash": self.api_hash
        }

    def deserialize(self, **kwargs) -> 'Chat':
        self.id = kwargs['id']
        self.host = self.host.deserialize(**kwargs['host']) if self.host else Host(**kwargs['host'])
        self.status = kwargs['status']
        self.api_id = kwargs['api_id']
        self.api_hash = kwargs['api_hash']
        return self


class Chat(Entity['Chat']):
    """Chat entity representation"""

    endpoint = "chats"

    CREATED = 0
    AVAILABLE = 1
    MONITORING = 2
    FAILED = 3

    def __init__(self, link: 'str', **kwargs):
        super().__init__(**kwargs)

        self.link: 'str' = link
        self.status: 'int' = kwargs.get("status", 0)
        self.status_text: 'str | None' = kwargs.get("status_text")
        self.internal_id: 'int | None' = kwargs.get("internal_id")
        self.title: 'str | None' = kwargs.get("title")
        self.description: 'str | None' = kwargs.get("description")
        self.date: 'str | None' = kwargs.get("date")
        self.parser: 'TypeParser' = kwargs.get("parser")

    @property
    def unique_constraint(self) -> 'dict | None':
        return None

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
            "parser": self.parser
        }

    def deserialize(self, **kwargs) -> 'Chat':
        self.id = kwargs['id']
        self.link = kwargs['link']
        self.status = kwargs['status']
        self.status_text = kwargs.get('status_text')
        self.internal_id = kwargs.get('internal_id')
        self.title = kwargs.get('title')
        self.description = kwargs.get('description')
        self.date = kwargs.get('date')
        self.parser = self.parser.deserialize(**kwargs['parser']) if self.parser else Parser(**kwargs['parser'])

        return self


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
        self.status: 'bool' = kwargs.get("status", 0)
        self.status_text: 'str | None' = kwargs.get("status_text")
        self.internal_id: 'int | None' = kwargs.get("internal_id")
        self.session: 'str | None' = kwargs.get("session")
        self.first_name: 'str | None' = kwargs.get("first_name")
        self.last_name: 'str | None' = kwargs.get("last_name")
        self.code: 'str | None' = kwargs.get("code")
        self.parser = kwargs.get("parser")

    @property
    def unique_constraint(self) -> 'dict | None':
        return None

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
            "parser": {"id": self.parser.id} if self.parser else None
        }

    def deserialize(self, **kwargs) -> 'TypePhone':
        self.id = kwargs["id"]
        self.number = kwargs["number"]
        self.status = kwargs["status"]
        self.status_text = kwargs.get("status_text")
        self.parser = self.parser.deserialize(**kwargs["parser"]) if self.parser else (Parser(**kwargs["parser"]) if "parser" in kwargs else None)
        self.internal_id = kwargs.get("internal_id")
        self.session = kwargs.get("session")
        self.first_name = kwargs.get("first_name")
        self.last_name = kwargs.get("last_name")
        self.code = kwargs.get("code")

        return self


class ChatPhone(Entity['ChatPhone']):
    """ChatPhone entity representation"""

    endpoint = "chats-phones"

    def __init__(self, chat: 'TypeChat', phone: 'TypePhone', **kwargs):
        super().__init__(**kwargs)

        self.chat: 'TypeChat' = chat
        self.phone: 'TypePhone' = phone
        self.is_using: 'bool' = kwargs.get("is_using")

    @property
    def unique_constraint(self) -> 'dict | None':
        return {'chat': {"id": self.chat.id}, "phone": {"id": self.phone.id}}

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "chat": {"id": self.chat.id},
            "phone": {"id": self.phone.id},
            "is_using": self.is_using
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, **kwargs) -> 'ChatPhone':
        self.id = kwargs.get("id")
        # self.chat = self.chat.deserialize(**kwargs.get("chat"))
        # self.phone = self.phone.deserialize(**kwargs.get("phone"))
        self.is_using = kwargs.get("is_using", False)

        return self


class Message(Entity['Message']):
    """Message entity representation"""

    endpoint = "messages"

    def __init__(self, internal_id: 'int', chat: 'TypeChat', **kwargs):
        super().__init__(**kwargs)

        self.internal_id: 'int' = internal_id
        self.chat: 'TypeChat' = chat
        self.text: 'str | None' = kwargs.get("text")
        self.member: 'TypeMember | None' = kwargs.get("member")
        self.reply_to: 'TypeMessage | None' = kwargs.get("reply_to")
        self.is_pinned: 'bool' = kwargs.get("is_pinned", False)
        self.forwarded_from_id: 'int | None' = kwargs.get("forwarded_from_id")
        self.forwarded_fromendpoint: 'str | None' = kwargs.get("forwarded_fromendpoint")
        self.grouped_id: 'int | None' = kwargs.get("grouped_id")
        self.date: 'str | None' = kwargs.get("date")
        
    @property
    def unique_constraint(self) -> 'dict | None':
        return {'internal_id': self.internal_id, 'chat': {"id": self.chat.id}}

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id, 
            "internal_id": self.internal_id, 
            "text": self.text, 
            "chat": {"id": self.chat.id},
            "member": {"id": self.member.id} if self.member is not None and self.member.id is not None else None,
            "reply_to": {"id": self.reply_to.id} if self.reply_to is not None and self.reply_to.id is not None else None,
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
        self.chat = self.chat.deserialize(**kwargs.get("chat"))
        self.member = self.member.deserialize(**kwargs.get("member")) if self.member is not None and "member" in kwargs else None
        self.reply_to = self.reply_to.deserialize(**kwargs.get("reply_to")) if self.reply_to is not None and "reply_to" in kwargs else None
        self.is_pinned = kwargs.get("is_pinned")
        self.forwarded_from_id = kwargs.get("forwarded_from_id")
        self.forwarded_fromendpoint = kwargs.get("forwarded_fromendpoint")
        self.grouped_id = kwargs.get("grouped_id")
        self.date = kwargs.get("date")

        return self


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

    def __init__(self, chat: 'TypeChat', member: 'TypeMember', **kwargs):
        super().__init__(**kwargs)

        self.chat: 'TypeChat' = chat
        self.member: 'TypeMember' = member
        self.date: 'str | None' = kwargs.get("date")
        self.is_left: 'bool' = kwargs.get("is_left")
        self.roles: 'list[TypeChatMemberRole]' = kwargs.get("roles")

    @property
    def unique_constraint(self) -> 'dict | None':
        return {'chat': {"id": self.chat.id}, "member": {"id": self.member.id}}

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "chat": {"id": self.chat.id} if self.chat is not None and self.chat.id is not None else None,
            "member": {"id": self.member.id} if self.member is not None and self.member.id is not None else None,
            "date": self.date,
            "is_left": self.is_left,
            "roles": [{"id": role.id} for role in self.roles if role is not None and role.id is not None],
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, **kwargs) -> 'TypeChatMember':
        self.id = kwargs["id"]
        self.chat = self.chat.deserialize(**kwargs["chat"]) if self.chat is not None and "chat" in kwargs else None
        self.member = self.member.deserialize(**kwargs["member"]) if self.member is not None and "member" in kwargs else None
        self.date = kwargs.get("date")
        self.is_left = kwargs.get("is_left")

        return self


class ChatMemberRole(Entity['ChatMemberRole']):
    """ChatMemberRole entity representation"""

    endpoint = "chats-members-roles"

    def __init__(self, member: 'TypeChatMember', **kwargs):
        super().__init__(**kwargs)

        self.member: 'TypeChatMember' = member
        self.title: 'str' = kwargs.get("title", "Участник")
        self.code: 'str' = kwargs.get("code", "member")

    @property
    def unique_constraint(self) -> 'dict | None':
        return {'member': {"id": self.member.id}, 'title': self.title, 'code': self.code}

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "member": {"id": self.member.id} if self.member is not None and self.member.id is not None else None,
            "title": self.title,
            "code": self.code
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, **kwargs) -> 'TypeChatMemberRole':
        self.id = kwargs["id"]
        self.member = self.member.deserialize(**kwargs.get("member")) if self.member is not None and "member" in kwargs else None
        self.title = kwargs["title"]
        self.code = kwargs["code"]

        return self


class ChatMedia(Media['ChatMedia']):
    """ChatMedia entity representation"""

    endpoint = "chats-medias"

    def __init__(self, internal_id: 'int', chat: 'TypeChat' = None, **kwargs):
        super().__init__(**kwargs)

        self.chat: 'TypeChat' = chat
        self.internal_id: 'int' = internal_id
        self.path: 'str | None' = kwargs.get("path")
        self.date: 'str | None' = kwargs.get("date")

    @property
    def unique_constraint(self) -> 'dict | None':
        return {"internal_id": self.internal_id}

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "chat": {"id": self.chat.id},
            "internal_id": self.internal_id,
            "path": self.path,
            "date": self.date,
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, **kwargs) -> 'TypeChatMedia':
        self.id = kwargs.get("id")
        # self.chat = self.chat.deserialize(**kwargs.get("chat"))
        self.internal_id = kwargs.get("internal_id")
        self.path = kwargs.get("path")
        self.date = kwargs.get("date")

        return self


class MemberMedia(Media['MemberMedia']):
    """MemberMedia entity representation"""

    endpoint = "members-medias"

    def __init__(self, internal_id: 'int', member: 'TypeMember', **kwargs):
        super().__init__(**kwargs)

        self.member: 'TypeMember | None' = member
        self.internal_id: 'int' = internal_id
        self.path: 'str | None' = kwargs.get("path")
        self.date: 'str | None' = kwargs.get("date")

    @property
    def unique_constraint(self) -> 'dict | None':
        return {'internal_id': self.internal_id}

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "member": {"id": self.member.id} if self.member is not None and self.member.id is not None else None,
            "internal_id": self.internal_id,
            "path": self.path,
            "date": self.date,
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, **kwargs) -> 'TypeMemberMedia':
        self.id = kwargs["id"]
        self.internal_id = kwargs["internal_id"]
        self.member = self.member.deserialize(**kwargs.get("member")) if self.member is not None and "member" in kwargs else None
        self.path = kwargs.get("path")
        self.date = kwargs.get("date")

        return self


class MessageMedia(Media['MessageMedia']):
    """MessageMedia entity representation"""

    endpoint = "messages-medias"

    def __init__(self, internal_id: 'int', message: 'TypeMessage', **kwargs) -> None:
        super().__init__(**kwargs)

        self.message: 'TypeMessage' = message
        self.internal_id: 'int' = internal_id
        self.path: 'str | None' = kwargs.get("path")
        self.date: 'str | None' = kwargs.get("date")

    @property
    def unique_constraint(self) -> 'dict | None':
        return {'internal_id': self.internal_id}

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "message": {"id": self.message.id} if self.message is not None and self.message.id is not None else None,
            "internal_id": self.internal_id,
            "path": self.path,
            "date": self.date,
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, **kwargs) -> 'TypeMessageMedia':
        self.id = kwargs["id"]
        self.internal_id = kwargs["internal_id"]
        self.message = self.message.deserialize(**kwargs.get("message")) if "message" in kwargs else None
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
