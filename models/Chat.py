import re
import logging
from utils import get_hash

from core.PhonesManager import PhonesManager
from processors.ApiProcessor import ApiProcessor
from threads.ChatPulseThread import ChatPulseThread
from threads.ChatJoiningThread import ChatJoiningThread
from threads.MembersParserThread import MembersParserThread
from threads.MessagesParserThread import MessagesParserThread
from threads.MessagesPhotoParserThread import MessagesPhotoParserThread
from threads.ChatMediaThread import ChatMediaThread

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
        
        self.chat_pulse_thread = None
        self.joining_thread = None
        self.members_thread = None
        self.medias_thread = None
        self.messages_thread = None
        self.messages_photo_thread = None
        
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
        new_phones = []

        if self.is_available:
            for phone in new_value:
                phone = PhonesManager().get(phone['id'])
                    
                if phone != None:
                    new_phones.append(phone)
                    
            if len(new_phones) < 3:
                if self.joining_thread == None:
                    self.joining_thread = ChatJoiningThread(self)
                    self.joining_thread.setDaemon(True)
                    self.joining_thread.start()
                else:
                    logging.debug(f"Chat joining thread for chat {self.id} is running.")
            else:
                self.joining_thread = None
                
                if self.chat_pulse_thread == None:
                    self.chat_pulse_thread = ChatPulseThread(self, new_phones)
                    self.chat_pulse_thread.start()
                else:
                    logging.debug(f"Chat pulse thread for chat {self.id} is running.")
                    
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
                logging.debug(f"Members parsing thread for chat {self.id} is running.")
            #--< MEMBERS --<#

            #--> CHAT MEDIAS -->#
            # if self.medias_thread == None:
            #     self.medias_thread = ChatMediaThread(self)
            #     self.medias_thread.setDaemon(True)
            #     self.medias_thread.start()
            # else:
                # logging.debug(f"Medias parsing thread for chat {self.id} is running.")
            #--< CHAT MEDIAS --<#
            
            #--> MESSAGES -->#
            if self.messages_thread == None:
                self.messages_thread = MessagesParserThread(self)
                self.messages_thread.setDaemon(True)
                self.messages_thread.start()
            else:
                logging.debug(f"Messages parsing thread for chat {self.id} is running.")
            #--< MESSAGES --<#
            
            #--> MESSAGES PHOTOS -->#
            # if self.messages_photo_thread == None:
            #     self.messages_photo_thread = MessagesPhotoParserThread(self)
            #     self.messages_photo_thread.setDaemon(True)
            #     self.messages_photo_thread.start()
            # else:
            #     logging.debug(f"Messages parsing thread for chat {self.id} is running.")
            #--< MESSAGES PHOTOS --<#
        
        return self