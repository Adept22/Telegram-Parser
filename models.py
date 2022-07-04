"""Collection of entity representations"""
import sys
from abc import ABCMeta, abstractmethod
from typing import Generic, TypeVar
from .utils import ApiService


class RelatedProperty(property):
    name = None

    def __init__(self, name, cls: 'TypeEntity | str'):
        self.name = name
        self._cls = cls

    @property
    def cls(self):
        if isinstance(self._cls, str):
            return getattr(sys.modules[__name__], self._cls)

        return self._cls

    def __get__(self, instance, owner=None):
        value = getattr(instance, f"{self.name}_id", None)
        value = self.cls(id=value)

        try:
            return value.reload()
        except ValueError:
            pass

        return value

    def __set__(self, instance, value):
        if isinstance(value, self.cls):
            value = value.id
        elif isinstance(value, (str, type(None))):
            value = value
        elif isinstance(value, dict):
            value = value['id']
        else:
            raise TypeError(
                f"Can't cast {type(value)} to '{self.name}'"
                f" object in property {self.name} of {self.cls}."
            )

        setattr(instance, f"{self.name}_id", value)


T = TypeVar('T', bound='Entity')


class Entity(Generic[T], metaclass=ABCMeta):
    """Base class for entities"""

    id = None

    def __init__(self, **kwargs):
        self.deserialize(**kwargs)

    def __str__(self):
        return f"<{self} object ({self.id})>"

    def __eq__(self, other):
        if not isinstance(other, Entity):
            return False

        my_id = self.id

        if my_id is None:
            return self is other

        return my_id == other.id

    @property
    @abstractmethod
    def _endpoint(self) -> str:
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

    @classmethod
    def find(cls, **kwargs) -> 'list[T]':
        """Возвращает отфильтрованный и отсортированный список сущностей"""

        entities = ApiService().get(cls._endpoint, **kwargs)

        return [cls(**entity) for entity in entities["results"]]

    def reload(self) -> 'T':
        """Обновляет текущую сущность из API."""

        if not self.id:
            raise ValueError("Entity hasn't id")

        entity = ApiService().get(self.__class__._endpoint, id=self.id, force=True)

        self.deserialize(**entity)

        return self

    def save(self) -> 'T':
        """Создает/изменяет сущность в API."""

        entity = ApiService().set(self.__class__._endpoint, **self.serialize())

        self.deserialize(**entity)

        return self

    def delete(self) -> 'None':
        """
        Удаляет сущность из API.
        """

        ApiService().delete(self.__class__._endpoint, self.id)


class Task(Entity['Task']):
    """Task entity representation"""

    STATUS_CREATED = 0
    STATUS_IN_PROGRESS = 1
    STATUS_SUCCESED = 2
    STATUS_FAILED = 3

    status: 'int' = STATUS_CREATED
    status_text: 'str' = None
    started_at: 'str' = None
    ended_at: 'str' = None

    @property
    @abstractmethod
    def _endpoint(self) -> str:
        """Название сущности в пути API."""

        raise NotImplementedError

    def serialize(self) -> 'dict':
        return {
            "id": self.id,
            "status": self.status,
            "status_text": self.status_text,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
        }

    def deserialize(self, **kwargs) -> 'TypeTask':
        self.id = kwargs.get("id")
        self.status = kwargs.get("status")
        self.status_text = kwargs.get("status_text")
        self.started_at = kwargs.get("started_at")
        self.ended_at = kwargs.get("ended_at")

        return self


class Link(Entity['Link']):
    """Link entity representation"""

    _endpoint = "links"

    TYPE_LINK = 0
    TYPE_CHAT_LINK = 1
    TYPE_MEMBER_LINK = 2
    TYPE_MESSAGE_LINK = 3

    STATUS_CREATED = 0
    STATUS_AVAILABLE = 1
    STATUS_FAILED = 2

    type: 'int' = TYPE_LINK
    link: 'str' = None
    status: 'int' = STATUS_CREATED
    status_text: 'str' = None

    def serialize(self) -> 'dict':
        return {
            "id": self.id,
            "type": self.type,
            "link": self.link,
            "status": self.status,
            "status_text": self.status_text
        }

    def deserialize(self, **kwargs) -> 'Link':
        self.id = kwargs.get('id')
        self.type = kwargs.get('type')
        self.link = kwargs.get('link')
        self.status = kwargs.get('status')
        self.status_text = kwargs.get('status_text')

        return self


class Host(Entity['Host']):
    """Host entity representation"""

    _endpoint = "hosts"

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

    _endpoint = "parsers"

    NEW = 0
    IN_PROGRESS = 1
    FAILED = 2

    host: 'TypeHost' = RelatedProperty("host", Host)
    status: 'int' = NEW
    api_id: 'str' = None
    api_hash: 'str' = None

    def serialize(self) -> 'dict':
        return {
            "id": self.id,
            "host": self.host.id,
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

    _endpoint = "chats"

    CREATED = 0
    AVAILABLE = 1
    FAILED = 2

    link: 'str' = None
    status: 'int' = CREATED
    status_text: 'str' = None
    internal_id: 'int' = None
    title: 'str' = None
    description: 'str' = None
    date: 'str' = None
    total_members: 'int' = None
    total_messages: 'int' = None
    parser: 'TypeParser' = RelatedProperty("parser", Parser)

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
            "total_members": self.total_members,
            "total_messages": self.total_messages,
            "parser": self.parser.id
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
        self.total_members = kwargs.get('total_members')
        self.total_messages = kwargs.get('total_messages')
        self.parser = kwargs.get('parser')

        return self


class ChatLink(Link['ChatLink']):
    """ChatLink entity representation"""

    type: 'int' = Link.TYPE_CHAT_LINK
    chat: 'TypeChat' = RelatedProperty("chat", Chat)

    def serialize(self) -> 'dict':
        _dict = super().serialize()

        return _dict.update(
            {
                "chat": self.chat.id
            }
        )

    def deserialize(self, **kwargs) -> 'Link':
        super().deserialize(**kwargs)

        self.chat = kwargs.get('chat')

        return self


class ChatTask(Task['ChatTask']):
    """ChatTask entity representation"""

    _endpoint = "chats-tasks"

    chat: 'TypeChat' = RelatedProperty("chat", Chat)
    type: 'int' = None

    def serialize(self) -> 'dict':
        _dict = super().serialize()

        return _dict.update(
            {
                "chat": self.chat.id,
                "type": self.type,
            }
        )

    def deserialize(self, **kwargs) -> 'TypeChatTask':
        super().deserialize(**kwargs)

        self.chat = kwargs.get("chat")
        self.type = kwargs.get("type")

        return self


class ChatMedia(Entity['ChatMedia']):
    """ChatMedia entity representation"""

    _endpoint = "chats-medias"

    chat: 'TypeChat' = RelatedProperty("chat", Chat)
    internal_id: 'int' = None
    path: 'str' = None
    date: 'str' = None

    def serialize(self) -> 'dict':
        return {
            "id": self.id,
            "chat": self.chat.id,
            "internal_id": self.internal_id,
            "path": self.path,
            "date": self.date,
        }

    def deserialize(self, **kwargs) -> 'TypeChatMedia':
        self.id = kwargs.get("id")
        self.chat = kwargs.get("chat")
        self.internal_id = kwargs.get("internal_id")
        self.path = kwargs.get("path")
        self.date = kwargs.get("date")

        return self


class Phone(Entity['Phone']):
    """Phone entity representation"""

    _endpoint = "phones"

    CREATED = 0
    READY = 1
    FLOOD = 2
    FULL = 3
    BAN = 4

    number: 'str' = None
    status: 'int' = None
    status_text: 'str' = None
    internal_id: 'int' = None
    session: 'str' = None
    username: 'str' = None
    first_name: 'str' = None
    last_name: 'str' = None
    code: 'str' = None
    parser: 'TypeParser' = RelatedProperty("parser", Parser)
    api: 'dict' = None
    takeout: 'bool' = False

    def serialize(self) -> 'dict':
        return {
            "id": self.id,
            "number": self.number,
            "status": self.status,
            "status_text": self.status_text,
            "internal_id": self.internal_id,
            "session": self.session,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "code": self.code,
            "parser": self.parser.id,
            "api": self.api,
            "takeout": self.takeout
        }

    def deserialize(self, **kwargs) -> 'TypePhone':
        self.id = kwargs.get("id")
        self.number = kwargs.get("number")
        self.status = kwargs.get("status")
        self.status_text = kwargs.get("status_text")
        self.parser = kwargs.get('parser')
        self.internal_id = kwargs.get("internal_id")
        self.session = kwargs.get("session")
        self.username = kwargs.get("username")
        self.first_name = kwargs.get("first_name")
        self.last_name = kwargs.get("last_name")
        self.code = kwargs.get("code")
        self.api = kwargs.get("api")
        self.takeout = kwargs.get("takeout", False)

        return self


class PhoneTask(Task['PhoneTask']):
    """PhoneTask entity representation"""

    _endpoint = "phones-tasks"

    phone: 'TypePhone' = RelatedProperty("phone", Phone)
    type: 'int' = None

    def serialize(self) -> 'dict':
        _dict = super().serialize()

        return _dict.update(
            {
                "phone": self.phone.id,
                "type": self.type,
            }
        )

    def deserialize(self, **kwargs) -> 'TypePhoneTask':
        super().deserialize(**kwargs)

        self.phone = kwargs.get("phone")
        self.type = kwargs.get("type")

        return self


class ChatPhone(Entity['ChatPhone']):
    """ChatPhone entity representation"""

    _endpoint = "chats-phones"

    chat: 'TypeChat' = RelatedProperty("chat", Chat)
    phone: 'TypePhone' = RelatedProperty("phone", Phone)
    is_using: 'bool' = False

    def serialize(self) -> 'dict':
        return {
            "id": self.id,
            "chat": self.chat.id,
            "phone": self.phone.id,
            "is_using": self.is_using
        }

    def deserialize(self, **kwargs) -> 'ChatPhone':
        self.id = kwargs.get("id")
        self.chat = kwargs.get("chat")
        self.phone = kwargs.get("phone")
        self.is_using = kwargs.get("is_using", False)

        return self


class Member(Entity['Member']):
    """Member entity representation"""

    _endpoint = "members"

    internal_id: 'int' = None
    username: 'str' = None
    first_name: 'str' = None
    last_name: 'str' = None
    phone: 'str' = None
    about: 'str' = None

    def serialize(self) -> 'dict':
        return {
            "id": self.id,
            "internal_id": self.internal_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "about": self.about
        }

    def deserialize(self, **kwargs) -> 'TypeMember':
        self.id = kwargs.get("id")
        self.internal_id = kwargs.get("internal_id")
        self.username = kwargs.get("username")
        self.first_name = kwargs.get("first_name")
        self.last_name = kwargs.get("last_name")
        self.phone = kwargs.get("phone")
        self.about = kwargs.get("about")

        return self


class MemberLink(Link['MemberLink']):
    """MemberLink entity representation"""

    _endpoint = "links"

    type: 'int' = Link.TYPE_MEMBER_LINK
    member: 'TypeMember' = RelatedProperty("member", Member)

    def serialize(self) -> 'dict':
        _dict = super().serialize()

        return _dict.update(
            {
                "member": self.member.id
            }
        )

    def deserialize(self, **kwargs) -> 'Link':
        super().deserialize(**kwargs)

        self.member = kwargs.get('member')

        return self


class MemberMedia(Entity['MemberMedia']):
    """MemberMedia entity representation"""

    _endpoint = "members-medias"

    member: 'TypeMember' = RelatedProperty("member", Member)
    internal_id: 'int' = None
    path: 'str' = None
    date: 'str' = None

    def serialize(self) -> 'dict':
        return {
            "id": self.id,
            "member": self.member.id,
            "internal_id": self.internal_id,
            "path": self.path,
            "date": self.date,
        }

    def deserialize(self, **kwargs) -> 'TypeMemberMedia':
        self.id = kwargs.get("id")
        self.internal_id = kwargs.get("internal_id")
        self.member = kwargs.get("member")
        self.path = kwargs.get("path")
        self.date = kwargs.get("date")

        return self


class ChatMember(Entity['ChatMember']):
    """ChatMember entity representation"""

    _endpoint = "chats-members"

    chat: 'TypeChat' = RelatedProperty("chat", Chat)
    member: 'TypeMember' = RelatedProperty("member", Member)
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
        return {
            "id": self.id,
            "chat": self.chat.id,
            "member": self.member.id,
            "date": self.date,
            "is_left": self.is_left,
            "roles": [role.id for role in self.roles if isinstance(role, ChatMemberRole)],
        }

    def deserialize(self, **kwargs) -> 'TypeChatMember':
        self.id = kwargs.get("id")
        self.chat = kwargs.get("chat")
        self.member = kwargs.get("member")
        self.date = kwargs.get("date")
        self.is_left = kwargs.get("is_left", False)
        self.roles = kwargs.get("roles")

        return self


class ChatMemberRole(Entity['ChatMemberRole']):
    """ChatMemberRole entity representation"""

    _endpoint = "chats-members-roles"

    member: 'TypeMember' = RelatedProperty("member", ChatMember)
    title: 'str' = "Участник"
    code: 'str' = "member"

    def serialize(self) -> 'dict':
        return {
            "id": self.id,
            "member": self.member.id,
            "title": self.title,
            "code": self.code
        }

    def deserialize(self, **kwargs) -> 'TypeChatMemberRole':
        self.id = kwargs.get("id")
        self.member = kwargs.get("member")
        self.title = kwargs.get("title")
        self.code = kwargs.get("code")

        return self


class Message(Entity['Message']):
    """Message entity representation"""

    _endpoint = "messages"

    internal_id: 'int' = None
    chat: 'TypeChat' = RelatedProperty("chat", Chat)
    text: 'str' = None
    member: 'TypeMember' = RelatedProperty("member", ChatMember)
    reply_to: 'str' = None
    is_pinned: 'bool' = False
    forwarded_from_id: 'int' = None
    forwarded_from_endpoint: 'str' = None
    grouped_id: 'int' = None
    date: 'str' = None

    def serialize(self) -> 'dict':
        return {
            "id": self.id,
            "internal_id": self.internal_id,
            "text": self.text,
            "chat": self.chat.id,
            "member": self.member.id,
            "reply_to": self.reply_to,
            "is_pinned": self.is_pinned,
            "forwarded_from_id": self.forwarded_from_id,
            "forwarded_from_endpoint": self.forwarded_from_endpoint,
            "grouped_id": self.grouped_id,
            "date": self.date
        }

    def deserialize(self, **kwargs) -> 'TypeMessage':
        self.id = kwargs.get("id")
        self.internal_id = kwargs.get("internal_id")
        self.text = kwargs.get("text")
        self.chat = kwargs.get("chat")
        self.member = kwargs.get("member")
        self.reply_to = kwargs.get("reply_to")
        self.is_pinned = kwargs.get("is_pinned", False)
        self.forwarded_from_id = kwargs.get("forwarded_from_id")
        self.forwarded_from_endpoint = kwargs.get("forwarded_from_endpoint")
        self.grouped_id = kwargs.get("grouped_id")
        self.date = kwargs.get("date")

        return self


class MessageMedia(Entity['MessageMedia']):
    """MessageMedia entity representation"""

    _endpoint = "messages-medias"

    message: 'TypeMessage' = RelatedProperty("message", Message)
    internal_id: 'int' = None
    path: 'str' = None
    date: 'str' = None

    def serialize(self) -> 'dict':
        return {
            "id": self.id,
            "message": self.message.id,
            "internal_id": self.internal_id,
            "path": self.path,
            "date": self.date,
        }

    def deserialize(self, **kwargs) -> 'TypeMessageMedia':
        self.id = kwargs.get("id")
        self.internal_id = kwargs.get("internal_id")
        self.message = kwargs.get("message")
        self.path = kwargs.get("path")
        self.date = kwargs.get("date")

        return self


TypeEntity = Entity
TypeTask = Task
TypeLink = Link
TypeHost = Host
TypeParser = Parser
TypeChat = Chat
TypeChatLink = ChatLink
TypeChatTask = ChatTask
TypeChatMedia = ChatMedia
TypePhone = Phone
TypePhoneTask = PhoneTask
TypeChatPhone = ChatPhone
TypeMember = Member
TypeMemberLink = MemberLink
TypeMemberMedia = MemberMedia
TypeChatMember = ChatMember
TypeChatMemberRole = ChatMemberRole
TypeMessage = Message
TypeMessageMedia = MessageMedia
