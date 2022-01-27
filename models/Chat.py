import re
import logging
import threading
from utils import get_hash

from models.Entity import Entity
from core.PhonesManager import PhonesManager
from processors.ApiProcessor import ApiProcessor
from threads.ChatPulseThread import ChatPulseThread
from threads.ChatJoiningThread import ChatJoiningThread
from threads.MembersParserThread import MembersParserThread
from threads.MessagesParserThread import MessagesParserThread

class Chat(Entity):
    _type = 'member'
    _attrs = ['dict', 'lock', 'username', 'hash', '_phones', '_available_phones', 'chat_pulse_thread', 'chat_joining_thread', 'members_thread', 'messages_thread']
    
    def __init__(self, _dict):
        super().__init__(_dict)

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
        
        self.chat_pulse_thread = None
        self.chat_joining_thread = None
        self.members_thread = None
        self.messages_thread = None
        
        self.from_dict()
        
    @property
    def phones(self):
        return self._phones
    
    @phones.setter
    def phones(self, new_value):
        new_phones = []

        for phone in new_value:
            phone = PhonesManager().get(phone['id'])
                
            if phone != None:
                new_phones.append(phone)
            
        self._phones = new_phones
        
        if len(new_phones) != len(new_value):
            self.save()
        
    @property
    def available_phones(self):
        return self._available_phones
    
    @available_phones.setter
    def available_phones(self, new_value):
        new_available_phones = []

        for available_phone in new_value:
            available_phone = PhonesManager().get(available_phone['id'])
                
            if available_phone != None:
                new_available_phones.append(available_phone)
            
        self._available_phones = new_available_phones
        
        if len(new_available_phones) != len(new_value):
            self.save()
    
    async def init(self):
        if not self.is_available or (len(self.available_phones) == 0 and len(self.phones) == 0):
            if self.is_available:
                self.is_available = False
                
                self.save()
            
            return
        
        if len(self.phones) >= 3 or len(self.available_phones) <= len(self.phones):
            if self.chat_pulse_thread == None:
                self.chat_pulse_thread = ChatPulseThread(self)
                self.chat_pulse_thread.setDaemon(True)
                self.chat_pulse_thread.start()
        elif len(self.phones) < 3:
            if self.chat_joining_thread == None:
                self.chat_joining_thread = ChatJoiningThread(self)
                self.chat_joining_thread.setDaemon(True)
                self.chat_joining_thread.start()
        
        if len(self.phones) > 0:
            #--> MEMBERS -->#
            if self.members_thread == None:
                self.members_thread = MembersParserThread(self)
                self.members_thread.setDaemon(True)
                self.members_thread.start()
            else:
                logging.debug(f"Members parsing thread for chat {self.id} is running.")
            #--< MEMBERS --<#
            
            #--> MESSAGES -->#
            if self.messages_thread == None:
                self.messages_thread = MessagesParserThread(self)
                self.messages_thread.setDaemon(True)
                self.messages_thread.start()
            else:
                logging.debug(f"Messages parsing thread for chat {self.id} is running.")
            #--< MESSAGES --<#