import threading
import entities, threads

class ChatPhone(entities.Entity):
    def __init__(self, id: 'str', chat: 'entities.TypeChat', phone: 'entities.TypePhone', isUsing: 'bool' = False, *args, **kwargs):
        self.id: 'str | None' = id
        self.chat: 'entities.TypeChat' = chat
        self.phone: 'entities.TypePhone' = phone
        self.isUsing: 'bool' = isUsing

    @property
    def name(self) -> 'str':
        return "chat-phone"
        
    @property
    def unique_constraint(self) -> 'dict | None':
        return { 'chat': { "id": self.chat.id }, "phone": { "id": self.phone.id } }

    async def expand(self) -> 'ChatPhone':
        return self

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "chat": { "id": self.chat.id },
            "phone": { "id": self.phone.id },
            "isUsing": self.isUsing
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict') -> 'ChatPhone':
        self.id = _dict.get("id")
        # self.chat = self.chat.deserialize(_dict.get("chat"))
        # self.phone = self.phone.deserialize(_dict.get("phone"))
        self.isUsing = _dict.get("isUsing", False)

        return self

    def join_chat(self) -> 'None':
        thread = threading.Thread(target=threads.join_chat_thread, args=(self, ))
        thread.start()
