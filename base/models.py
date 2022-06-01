from abc import ABCMeta, abstractmethod
from typing import Generic, TypeVar
from base.utils import ApiService

T = TypeVar('T', bound='Entity')


class Entity(Generic[T], metaclass=ABCMeta):
    @property
    @abstractmethod
    @staticmethod
    def __name() -> str:
        """
        Название сущности в пути API.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def id(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def unique_constraint(self) -> 'dict | None':
        """
        Свойства для проверки существования сущности, они же отражают уникольность.
        """
        raise NotImplementedError

    @abstractmethod
    def serialize(self) -> 'dict':
        """
        Сериализация сущности. Т.е. из `self` в `dict`
        """
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, _dict: 'dict') -> 'T':
        """
        Десериализация сущности. Т.е. из `dict` в `self`
        """
        raise NotImplementedError

    @staticmethod
    def find(_dict) -> 'list[T]':
        """
        Возвращает отфильтрованный и отсортированный список сущностей
        """
        return ApiService().get(Entity.__name, _dict)

    def reload(self) -> 'T':
        """
        Обновляет текущую сущность из API.
        """
        if not self.id:
            raise ValueError("Entity hasn't id")

        self.deserialize(ApiService().get(Entity.__name, {"id": self.id}))

    def save(self) -> 'T':
        """
        Создает/изменяет сущность в API.
        """
        import base.exceptions as exceptions
        
        try:
            self.deserialize(ApiService().set(Entity.__name, self.serialize()))
        except exceptions.UniqueConstraintViolationError as ex:
            if self.unique_constraint is None:
                raise ex
                
            entities = ApiService().get(Entity.__name, self.unique_constraint)
            
            if len(entities) > 0:
                self.id = entities[0]['id']
                self.save()

        return self

    def delete(self) -> 'None':
        """
        Удаляет сущность из API.
        """
        ApiService().delete(Entity.__name, self.serialize())


class Media(Entity['Media'], metaclass=ABCMeta):
    async def upload(self, client, tg_media, file_size: 'int', extension: 'str') -> 'None':
        import math
        from telethon.client import downloads

        if not file_size or self.id is None:
            return

        media = ApiService().get(Media.__name, {"id": self.id})

        if media.get("path") is not None:
            return

        chunk_number = 0
        chunk_size = downloads.MAX_CHUNK_SIZE
        total_chunks = math.ceil(file_size / chunk_size)

        async for chunk in client.iter_download(file=tg_media, chunk_size=chunk_size, file_size=file_size):
            ApiService().chunk(
                Media.__name, self.serialize(), str(tg_media.id) + extension,
                chunk, chunk_number, chunk_size, total_chunks, file_size
            )
            chunk_number += 1


class Host(Entity['Host']):
    def __init__(self, id: 'str', public_ip: 'str', local_ip: 'str', name: 'str', *args, **kwargs):
        self.id: 'str' = id
        self.public_ip: 'str' = public_ip
        self.local_ip: 'str' = local_ip
        self.name: 'str' = name
    
    @property
    @staticmethod
    def __name() -> 'str':
        return "hosts"

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

    def deserialize(self, _dict: 'dict') -> 'Chat':
        self.id = _dict['id']
        self.public_ip = _dict['public_ip']
        self.local_ip = _dict['local_ip']
        self.name = _dict['name']
        return self


class Parser(Entity['Parser']):
    NEW = 0
    IN_PROGRESS = 1
    FAILED = 2

    def __init__(self, id: 'str', host: 'TypeHost | dict', status: 'int', api_id: 'str', api_hash: 'str', *args, **kwargs):
        self.id: 'str' = id
        self.host: 'str' = host if isinstance(host, Host) else Host(**host)
        self.status: 'int' = status
        self.api_id: 'str' = api_id
        self.api_hash: 'str' = api_hash
    
    @property
    @staticmethod
    def __name() -> 'str':
        return "parsers"
        
    @property
    def unique_constraint(self) -> 'dict | None':
        return None

    def serialize(self) -> 'dict':
        return {
            "id": self.id,
            "host": self.host.serialize() if self.host else None,
            "status": self.status,
            "api_id": self.api_id, 
            "api_hash": self.api_hash
        }

    def deserialize(self, _dict: 'dict') -> 'Chat':
        self.id = _dict['id']
        self.host = self.host.deserialize(_dict['host']) if self.host else Host(**_dict['host'])
        self.status = _dict['status']
        self.api_id = _dict['api_id']
        self.api_hash = _dict['api_hash']

        return self


class Chat(Entity['Chat']):
    CREATED = 0
    AVAILABLE = 1
    MONITORING = 2
    FAILED = 3

    def __init__(self, link: 'str', id: 'str' = None, status: 'int' = 0, status_text: 'str' = None, internal_id: 'int' = None, title: 'str' = None, description: 'str' = None, date: 'str' = None, parser: 'TypeParser | dict' = None, *args, **kwargs):
        self.id: 'str' = id
        self.link: 'str' = link
        self.status: 'int' = status
        self.status_text: 'str | None' = status_text
        self.internal_id: 'int | None' = internal_id
        self.title: 'str | None' = title
        self.description: 'str | None' = description
        self.date: 'str | None' = date
        self.parser: 'TypeParser' = parser if isinstance(parser, Parser) else Parser(**parser)
    
    @property
    @staticmethod
    def __name() -> 'str':
        return "chats"
        
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

    def deserialize(self, _dict: 'dict') -> 'Chat':
        self.id = _dict['id']
        self.link = _dict['link']
        self.status = _dict['status']
        self.status_text = _dict.get('status_text')
        self.internal_id = _dict.get('internal_id')
        self.title = _dict.get('title')
        self.description = _dict.get('description')
        self.date = _dict.get('date')
        self.parser = self.parser.deserialize(_dict['parser']) if self.parser else Parser(**_dict['parser'])

        return self


class Phone(Entity['Phone']):
    CREATED = 0
    READY = 1
    FLOOD = 2
    FULL = 3
    BAN = 4

    def __init__(self, id: 'str', number: 'str' = None, parser: 'TypeParser | dict' = None, status: 'int' = 0, status_text: 'str' = None, internal_id: 'int' = None, session: 'str' = None, first_name: 'str' = None, last_name: 'str' = None, code: 'str' = None, *args, **kwargs):
        self.id: 'str' = id
        self.number: 'str | None' = number
        self.status: 'bool' = status
        self.status_text: 'str | None' = status_text
        self.internal_id: 'int | None' = internal_id
        self.session: 'str | None' = session
        self.first_name: 'str | None' = first_name
        self.last_name: 'str | None' = last_name
        self.code: 'str | None' = code
        self.parser = parser if isinstance(parser, Parser) else Parser(**parser)
        
        self.code_hash: 'str | None' = None

    @property
    @staticmethod
    def __name() -> 'str':
        return "phones"
        
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

    def deserialize(self, _dict: 'dict') -> 'TypePhone':
        self.id = _dict["id"]
        self.number = _dict["number"]
        self.status = _dict["status"]
        self.status_text = _dict.get("status_text")
        self.parser = self.parser.deserialize(_dict["parser"]) if self.parser else Parser(**_dict["parser"])
        self.internal_id = _dict.get("internal_id")
        self.session = _dict.get("session")
        self.first_name = _dict.get("first_name")
        self.last_name = _dict.get("last_name")
        self.code = _dict.get("code")

        return self


class ChatPhone(Entity['ChatPhone']):
    def __init__(self, chat: 'TypeChat', phone: 'TypePhone', is_using: 'bool' = False, id: 'str' = None, *args, **kwargs):
        self.id: 'str | None' = id
        self.chat: 'TypeChat' = chat
        self.phone: 'TypePhone' = phone
        self.is_using: 'bool' = is_using

    @property
    @staticmethod
    def __name() -> 'str':
        return "chats-phones"
        
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

    def deserialize(self, _dict: 'dict') -> 'ChatPhone':
        self.id = _dict.get("id")
        # self.chat = self.chat.deserialize(_dict.get("chat"))
        # self.phone = self.phone.deserialize(_dict.get("phone"))
        self.is_using = _dict.get("is_using", False)

        return self


class Message(Entity['Message']):
    def __init__(self, internal_id: 'int', chat: 'TypeChat', id: 'str' = None, text: 'str' = None, member: 'TypeChatMember' = None, reply_to: 'TypeMessage' = None, is_pinned: 'bool' = False, forwarded_from_id: 'int' = None, forwarded_from_name: 'str' = None, grouped_id: 'int' = None, date: 'str' = None, *args, **kwargs):
        self.id: 'str | None' = id
        self.internal_id: 'int' = internal_id
        self.text: 'str | None' = text
        self.chat: 'TypeChat' = chat
        self.member: 'TypeMember | None' = member
        self.reply_to: 'TypeMessage | None' = reply_to
        self.is_pinned: 'bool' = is_pinned
        self.forwarded_from_id: 'int | None' = forwarded_from_id
        self.forwarded_from_name: 'str | None' = forwarded_from_name
        self.grouped_id: 'int | None' = grouped_id
        self.date: 'str | None' = date

    @property
    @staticmethod
    def __name() -> 'str':
        return "messages"
        
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
            "forwarded_from_name": self.forwarded_from_name, 
            "grouped_id": self.grouped_id, 
            "date": self.date
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict') -> 'TypeMessage':
        self.id = _dict.get("id")
        self.internal_id = _dict.get("internal_id")
        self.text = _dict.get("text")
        self.chat = self.chat.deserialize(_dict.get("chat"))
        self.member = self.member.deserialize(_dict.get("member")) if self.member is not None and "member" in _dict else None
        self.reply_to = self.reply_to.deserialize(_dict.get("reply_to")) if self.reply_to is not None and "reply_to" in _dict else None
        self.is_pinned = _dict.get("is_pinned")
        self.forwarded_from_id = _dict.get("forwarded_from_id")
        self.forwarded_from_name = _dict.get("forwarded_from_name")
        self.grouped_id = _dict.get("grouped_id")
        self.date = _dict.get("date")

        return self


class Member(Entity['Member']):
    def __init__(
            self, internal_id: 'int', id: 'str' = None, username: 'str' = None, first_name: 'str' = None,
            last_name: 'str' = None, phone: 'str' = None, about: 'str' = None, *args, **kwargs) -> None:
        self.id: 'str | None' = id
        self.internal_id: 'int' = internal_id
        self.username: 'str | None' = username
        self.first_name: 'str | None' = first_name
        self.last_name: 'str | None' = last_name
        self.phone: 'str | None' = phone
        self.about: 'str | None' = about

    @property
    @staticmethod
    def __name() -> 'str':
        return "members"
        
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

    def deserialize(self, _dict: 'dict') -> 'TypeMember':
        self.id = _dict.get("id")
        self.internal_id = _dict.get("internal_id")
        self.username = _dict.get("username")
        self.first_name = _dict.get("first_name")
        self.last_name = _dict.get("last_name")
        self.phone = _dict.get("phone")
        self.about = _dict.get("about")

        return self


class ChatMember(Entity['ChatMember']):
    def __init__(self, chat: 'TypeChat', member: 'TypeMember', id: 'str' = None, date: 'str' = None, is_left: 'bool' = False, roles: 'list[TypeChatMemberRole]' = [], *args, **kwargs):
        self.id: 'str | None' = id
        self.chat: 'TypeChat' = chat if isinstance(chat, Chat) else Chat(**chat)
        self.member: 'TypeMember' = member if isinstance(member, Member) else Member(**member)
        self.date: 'str | None' = date
        self.is_left: 'bool' = is_left
        self.roles: 'list[TypeChatMemberRole]' = roles

    @property
    @staticmethod
    def __name() -> 'str':
        return "chats-members"
        
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

    def deserialize(self, _dict: 'dict') -> 'TypeChatMember':
        self.id = _dict["id"]
        self.chat = self.chat.deserialize(_dict["chat"]) if self.chat is not None and "chat" in _dict else None
        self.member = self.member.deserialize(_dict["member"]) if self.member is not None and "member" in _dict else None
        self.date = _dict.get("date")
        self.is_left = _dict.get("is_left")

        return self


class ChatMemberRole(Entity['ChatMemberRole']):
    def __init__(self, member: 'TypeChatMember', id: 'str' = None, title: 'str' = "Участник", code: 'str' = "member", *args, **kwargs):
        self.id: 'str | None' = id
        self.member: 'TypeChatMember' = member
        self.title: 'str' = title
        self.code: 'str' = code
        
    @property
    @staticmethod
    def __name() -> 'str':
        return "chats-members-roles"
        
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

    def deserialize(self, _dict: 'dict') -> 'TypeChatMemberRole':
        self.id = _dict["id"]
        self.member = self.member.deserialize(_dict.get("member")) if self.member is not None and "member" in _dict else None
        self.title = _dict["title"]
        self.code = _dict["code"]

        return self


class ChatMedia(Media['ChatMedia']):
    def __init__(self, internal_id: 'int', chat: 'TypeChat' = None, id=None, path=None, date=None, *args, **kwargs):
        self.id: 'str | None' = id
        self.chat: 'TypeChat' = chat
        self.internal_id: 'int' = internal_id
        self.path: 'str | None' = path
        self.date: 'str | None' = date
        
    @property
    @staticmethod
    def __name() -> 'str':
        return "chats-medias"
        
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

    def deserialize(self, _dict: 'dict') -> 'TypeChatMedia':
        self.id = _dict.get("id")
        # self.chat = self.chat.deserialize(_dict.get("chat"))
        self.internal_id = _dict.get("internal_id")
        self.path = _dict.get("path")
        self.date = _dict.get("date")

        return self


class MemberMedia(Media['MemberMedia']):
    def __init__(self, internal_id: 'int', member: 'TypeMember' = None, id=None, path=None, date=None, *args, **kwargs):
        self.id: 'str | None' = id
        self.member: 'TypeMember | None' = member
        self.internal_id: 'int' = internal_id
        self.path: 'str | None' = path
        self.date: 'str | None' = date
    
    @property
    @staticmethod
    def __name() -> 'str':
        return "members-medias"
        
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

    def deserialize(self, _dict: 'dict') -> 'TypeMemberMedia':
        self.id = _dict["id"]
        self.internal_id = _dict["internal_id"]
        self.member = self.member.deserialize(_dict.get("member")) if self.member is not None and "member" in _dict else None
        self.path = _dict.get("path")
        self.date = _dict.get("date")

        return self


class MessageMedia(Media['MessageMedia']):
    def __init__(
            self, internal_id: 'int', message: 'TypeMessage' = None, id: 'str' = None, path: 'str' = None,
            date: 'str' = None, *args, **kwargs) -> None:
        self.id: 'str | None' = id
        self.message: 'TypeMessage' = message
        self.internal_id: 'int' = internal_id
        self.path: 'str | None' = path
        self.date: 'str | None' = date
    
    @property
    @staticmethod
    def __name() -> 'str':
        return "messages-medias"
        
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

    def deserialize(self, _dict: 'dict') -> 'TypeMessageMedia':
        self.id = _dict["id"]
        self.internal_id = _dict["internal_id"]
        self.message = self.message.deserialize(_dict.get("message")) if "message" in _dict else None
        self.path = _dict.get("path")
        self.date = _dict.get("date")

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
