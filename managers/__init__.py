from multiprocessing.managers import BaseManager

from .ChatsManager import ChatsManager, ChatsManagerProxy
from .PhonesManager import PhonesManager, PhonesManagerProxy

class ParserManager(BaseManager):
    pass

ParserManager.register('chats', ChatsManager, ChatsManagerProxy)
ParserManager.register('phones', PhonesManager, PhonesManagerProxy)