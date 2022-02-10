import re
import threading
from utils import get_hash

from core.PhonesManager import PhonesManager
from threads.ChatThread import ChatThread
from threads.ChatMediaThread import ChatMediaThread
from threads.MembersThread import MembersThread
from threads.MessagesThread import MessagesThread
from threads.ChatMediaThread import ChatMediaThread

class Chat(object):
    def __init__(self, _dict):
        if not 'id' in _dict or _dict['id'] is None:
            raise Exception('Unexpected chat id')

        if not 'link' in _dict or _dict['link'] is None:
            raise Exception('Unexpected chat link')

        self.username, self.hash = get_hash(_dict['link'])
        
        self.title = None
        self.link = None
        self.internal_id = None
        self.is_available = False
        
        self.phones = []
        self.available_phones = []

        self._phones = []
        self._available_phones = []

        self.chat_thread = None
        self.chat_media_thread = None
        self.members_thread = None
        self.messages_thread = None

        self.run_event = threading.Event()
        
        self.from_dict(_dict)

    def __del__(self):
        if self.run_event.is_set():
            self.run_event.clear()
        # TODO: Мы должны убивать треды при удалении чата.
        pass
        
    @property
    def phones(self):
        return self._phones
    
    @phones.setter
    def phones(self, new_value):
        self._phones = [PhonesManager()[p['id']] for p in new_value if p['id'] in PhonesManager()]
        
    @property
    def available_phones(self):
        return self._available_phones
    
    @available_phones.setter
    def available_phones(self, new_value):
        self._available_phones = [PhonesManager()[p['id']] for p in new_value if p['id'] in PhonesManager()]
        
    def from_dict(self, _dict):
        pattern = re.compile(r'(?<!^)(?=[A-Z])')
        
        for key in _dict:
            setattr(self, pattern.sub('_', key).lower(), _dict[key])
            
        return self

    def run(self):
        self.chat_thread = ChatThread(self)
        self.chat_thread.setDaemon(True)
        self.chat_thread.start()

        self.chat_media_thread = ChatMediaThread(self)
        self.chat_media_thread.setDaemon(True)
        self.chat_media_thread.start()

        self.members_thread = MembersThread(self)
        self.members_thread.setDaemon(True)
        self.members_thread.start()

        self.messages_thread = MessagesThread(self)
        self.messages_thread.setDaemon(True)
        self.messages_thread.start()

        return self
