import re
import logging
from utils import get_hash

from core.PhonesManager import PhonesManager
from processors.ApiProcessor import ApiProcessor
from threads.ChatThread import ChatThread
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
        self._phones = []
        self._available_phones = []
        
        self.chat_thread = None
        self.members_parser_thread = None
        self.messages_parser_thread = None
        
        self.from_dict(_dict)
        
    @property
    def phones(self):
        return self._phones
    
    @phones.setter
    def phones(self, new_value: 'dict'):
        self._phones = [PhonesManager()[p['id']] for p in new_value if p['id'] in PhonesManager()]
        
        # if len(self._phones) != len(new_value):
        #     ApiProcessor().set('chat', { 'id': self.id, 'phones': self._phones })
        
    @property
    def available_phones(self):
        return self._available_phones
    
    @available_phones.setter
    def available_phones(self, new_value: 'dict'):
        self._available_phones = [PhonesManager()[p['id']] for p in new_value if p['id'] in PhonesManager()]
        
        # if len(self._available_phones) != len(new_value):
        #     ApiProcessor().set('chat', { 'id': self.id, 'availablePhones': self._available_phones })
        
    def from_dict(self, dict):
        pattern = re.compile(r'(?<!^)(?=[A-Z])')
        
        for key in dict:
            setattr(self, pattern.sub('_', key).lower(), dict[key])
            
        return self
    
    async def init(self):
        if self.chat_thread == None:
            self.chat_thread = ChatThread(self)
            self.chat_thread.setDaemon(True)
            self.chat_thread.start()
        
        if len(self.phones) > 0:
            #--> MEMBERS -->#
            if self.members_parser_thread == None:
                self.members_parser_thread = MembersParserThread(self)
                self.members_parser_thread.setDaemon(True)
                self.members_parser_thread.start()
            else:
                logging.debug(f"Members parsing thread for chat {self.id} is running.")
            #--< MEMBERS --<#
            
            #--> MESSAGES -->#
            if self.messages_parser_thread == None:
                self.messages_parser_thread = MessagesParserThread(self)
                self.messages_parser_thread.setDaemon(True)
                self.messages_parser_thread.start()
            else:
                logging.debug(f"Messages parsing thread for chat {self.id} is running.")
            #--< MESSAGES --<#