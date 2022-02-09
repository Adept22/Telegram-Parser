import re
import threading
from utils import get_hash

from core.PhonesManager import PhonesManager
from threads.ChatThread import ChatThread
from threads.ChatMediaThread import ChatMediaThread
from threads.MembersParserThread import MembersParserThread
from threads.MessagesParserThread import MessagesParserThread

class Chat(object):
    def __init__(self, _dict):
        if not 'id' in _dict or _dict['id'] is None:
            raise Exception('Unexpected chat id')

        if not 'link' in _dict or _dict['link'] is None:
            raise Exception('Unexpected chat link')
        
        self.dict = _dict
        
        self.username, self.hash = get_hash(_dict['link'])
        
        self.title = None
        self.link = None
        self.internal_id = None
        self.is_available = False
        
        self.phones = []
        self.available_phones = []
        self.joining_thread = None
        self.members_thread = None
        self.medias_thread = None
        self.messages_thread = None
        self._phones = []
        self._available_phones = []

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
    def phones(self, new_value: 'dict'):
        self._phones = [PhonesManager()[p['id']] for p in new_value if p['id'] in PhonesManager()]
        
    @property
    def available_phones(self):
        return self._available_phones
    
    @available_phones.setter
    def available_phones(self, new_value: 'dict'):
        self._available_phones = [PhonesManager()[p['id']] for p in new_value if p['id'] in PhonesManager()]
        
    def from_dict(self, dict):
        pattern = re.compile(r'(?<!^)(?=[A-Z])')
        
        for key in dict:
            setattr(self, pattern.sub('_', key).lower(), dict[key])
            
        return self

    def run(self):
        self.chat_thread = ChatThread(self)
        self.chat_thread.setDaemon(True)
        self.chat_thread.start()
        
        self.medias_thread = ChatMediaThread(self)
        self.medias_thread.setDaemon(True)
        self.medias_thread.start()

        self.members_parser_thread = MembersParserThread(self)
        self.members_parser_thread.setDaemon(True)
        self.members_parser_thread.start()

        self.messages_parser_thread = MessagesParserThread(self)
        self.messages_parser_thread.setDaemon(True)
        self.messages_parser_thread.start()

        return self