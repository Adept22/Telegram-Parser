import re
import logging

from models.Phone import Phone
from threads.ChatJoiningThread import ChatJoiningThread

from utils.Chat import get_hash

from core.PhonesManager import PhonesManager
from threads.MembersParserThread import MembersParserThread
from threads.MessagesParserThread import MessagesParserThread

class Chat(object):
    def __init__(self, dict):
        if dict is None:
            raise Exception('Unexpected chat dictionary')
            
        if not 'id' in dict or dict['id'] is None:
            raise Exception('Unexpected chat id')

        if not 'link' in dict or dict['link'] is None:
            raise Exception('Unexpected chat link')
        
        self.dict = dict
        
        self.title = None
        self._link = None
        self.username = None
        self.hash = None
        self.internal_id = None
        self.access_hash = None
        self.chat_joining_thread = None
        self.members_thread = None
        self.messages_thread = None
        
        self._phones = []
        self.messages = []
        
        self.from_dict(dict)
        
    @property
    def link(self):
        return self._link
    
    @link.setter
    def link(self, new_value):
        self.username, self.hash = get_hash(new_value)
        
        self._link = new_value
        
    @property
    def phones(self):
        return self._phones
    
    @phones.setter
    def phones(self, new_value):
        self._phones = []
        
        for phone in new_value:
            if isinstance(phone, Phone):
                self._phones.append(phone)
            elif isinstance(phone, dict) and phone['id'] in PhonesManager():
                self._phones.append(PhonesManager()[phone['id']])
    
    def from_dict(self, dict):
        pattern = re.compile(r'(?<!^)(?=[A-Z])')
        
        for key in dict:
            setattr(self, pattern.sub('_', key).lower(), dict[key])
            
        self.dict = dict
        
        return self
    
    async def init(self):
        if not self.is_available:
            print(f"Chat {self.id} actually not available and cant be used.")
            logging.debug(f"Chat {self.id} actually not available and cant be used.")
            
            return self
            
        if self.chat_joining_thread == None:
            self.chat_joining_thread = ChatJoiningThread(self)
            self.chat_joining_thread.start()
        else:
            print(f"Members parsing thread for chat {self.id} actually running.")
            logging.debug(f"Members parsing thread for chat {self.id} actually running.")
        
        #--> MEMBERS -->#
        if self.members_thread == None:
            self.members_thread = MembersParserThread(self)
            self.members_thread.start()
        else:
            print(f"Members parsing thread for chat {self.id} actually running.")
            logging.debug(f"Members parsing thread for chat {self.id} actually running.")
        #--< MEMBERS --<#
        
        #--> MESSAGES -->#
        # if self.messages_thread == None:
        #     self.messages_thread = MessagesParserThread(self)
        #     self.messages_thread.start()
        # else:
        #     print(f"Messages parsing thread for chat {self.id} now is running.")
        #     logging.debug(f"Messages parsing thread for chat {self.id} now is running.")
        #--< MESSAGES --<#
        
        return self