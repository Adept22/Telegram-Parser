import asyncio
from os import name
import random
import re
import logging

from telethon import errors, functions, types

from utils.Chat import get_hash

from models.Phone import Phone
from core.PhonesManager import PhonesManager
from processors.ApiProcessor import ApiProcessor
from threads.ChatPulseThread import ChatPulseThread
from threads.ChatJoiningThread import ChatJoiningThread
from threads.MembersParserThread import MembersParserThread
from threads.MessagesParserThread import MessagesParserThread
from errors.ChatNotAvailableError import ChatNotAvailableError
from errors.ClientNotAvailableError import ClientNotAvailableError
from utils.bcolors import bcolors

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
        self.is_available = False
        self.joining_thread = None
        self.members_thread = None
        self.messages_thread = None
        
        self.valid_phones = []
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
        new_chat = None
        new_phones = []
                
        if self.is_available:
            for phone in new_value:
                phone = PhonesManager().get(phone['id'])
                    
                if phone != None:
                    new_phones.append(phone)
                    
            if len(new_phones) >= 3:
                self.joining_thread = None
                
                chat_pulse_thread = ChatPulseThread(self, new_phones)
                chat_pulse_thread.setDaemon(True)
                chat_pulse_thread.start()
                new_chat, new_phones = chat_pulse_thread.join()
                
                if len(new_phones) != len(new_value):
                    print(f"Chat {self.id} list of phones changed, saving...")
                    logging.debug(f"Chat {self.id} list of phones changed, saving...")
                    
                    ApiProcessor().set('chat', { 
                        'id': self.id, 
                        'phones': [{ 'id': p.id } for p in new_phones] 
                    })
                
                if new_chat != None:
                    if self.internal_id != new_chat.id:
                        print(f"Chat {self.id} \'internalId\' changed, saving...")
                        logging.debug(f"Chat {self.id} \'internalId\' changed, saving...")
                        
                        ApiProcessor().set('chat', { 
                            'id': self.id, 
                            'internalId': new_chat.id,
                            'title': new_chat.title if self.title == None else self.title
                        })
            else:
                if self.joining_thread == None:
                    self.joining_thread = ChatJoiningThread(self)
                    self.joining_thread.setDaemon(True)
                    self.joining_thread.start()
                else:
                    print(f"Chat joining thread for chat {self.id} actually running.")
                    logging.debug(f"Chat joining thread for chat {self.id} actually running.")
        else:
            print(f"Chat {self.id} actually not available.")
            logging.debug(f"Chat {self.id} actually not available.")
                    
        self._phones = new_phones
    
    def from_dict(self, dict):
        pattern = re.compile(r'(?<!^)(?=[A-Z])')
        
        for key in dict:
            setattr(self, pattern.sub('_', key).lower(), dict[key])
            
        self.dict = dict
        
        return self
    
    async def init(self):
        if self.is_available and len(self.phones) > 0:
            #--> MEMBERS -->#
            if self.members_thread == None:
                self.members_thread = MembersParserThread(self)
                self.members_thread.setDaemon(True)
                self.members_thread.start()
            else:
                print(f"Members parsing thread for chat {self.id} actually running.")
                logging.debug(f"Members parsing thread for chat {self.id} actually running.")
            #--< MEMBERS --<#
            
            #--> MESSAGES -->#
            if self.messages_thread == None:
                self.messages_thread = MessagesParserThread(self)
                self.messages_thread.setDaemon(True)
                self.messages_thread.start()
            else:
                print(f"Messages parsing thread for chat {self.id} now is running.")
                logging.debug(f"Messages parsing thread for chat {self.id} now is running.")
            #--< MESSAGES --<#
        
        return self