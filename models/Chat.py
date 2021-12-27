import asyncio
import re
import logging
import random

from utils.bcolors import bcolors
from utils.Chat import get_hash

from processors.ApiProcessor import ApiProcessor
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
        
        self.internal_id = None
        self.members_thread = None
        self.messages_thread = None
        
        self._phones = []
        self.messages = []
        
        self.from_dict(dict)
        
    @property
    def phones(self):
        return self._phones
    
    @phones.setter
    def phones(self, new_value):
        self._phones = []
        
        for phone in new_value:
            if phone['id'] in PhonesManager():
                self._phones.append(PhonesManager()[phone['id']])
    
    def from_dict(self, dict):
        pattern = re.compile(r'(?<!^)(?=[A-Z])')
        
        for key in dict:
            setattr(self, pattern.sub('_', key).lower(), dict[key])
            
        self.dict = dict
        
        return self
    

    def to_dict(self):
        skip_fields = [ 'dict', 'messages', 'members_thread', 'messages_thread' ]
        
        new_dict = {}
        
        for attr, value in self.__dict__.items():
            if key in skip_fields:
                continue
            
            components = attr.split('_')
            key = components[0] + ''.join(x.title() for x in components[1:])
            
            if type(value) == list:
                new_value = []
                
                for item in value:
                    if type(item) == object:
                        new_value.append(item.to_dict())
                    else:
                        new_value.append(item)
                        
                new_dict[key] = value
            elif type(value) == object:
                new_dict[key] = value.to_dict()
            else:
                new_dict[key] = value
                
        return new_dict
    
    def save(self):
        if self.id == None:
            raise Exception('Undefined object id.')
        
        ApiProcessor().set('chat', self.to_dict())
    
    async def init(self):
        if len(self.phones) == 0:
            if len(PhonesManager().items()) > 0:
                to_join = list(sorted(PhonesManager().values(), key=lambda phone: phone.chats_count))
                
                joined_phones = []
                
                for phone in to_join:
                    phone = PhonesManager()[phone['id']]
                    
                    if not await phone.is_participant(self):
                        try:
                            # if len(joined_phones) > 0:
                            #     chat = await joined_phones[0].invite(phone, self)
                            # else:
                            chat = await phone.join(self)
                        except Exception as ex:
                            print(f"{bcolors.FAIL}Chat or channel {self.id} joining phone {phone.id} problem. Exception: {ex}.{bcolors.ENDC}")
                            logging.error(f"Chat or channel {self.id} joining phone {phone.id} problem. Exception: {ex}.")
                            continue
                        else:
                            joined_phones.append(phone)
                            
                            self.is_available = True
                            self.internal_id = chat.id
                            self.access_hash = chat.access_hash
                            
                        await asyncio.sleep(random.randint(2, 5))
                    else:
                        joined_phones.append(phone)
                        
                    if len(joined_phones) == 3:
                        break
                    
                if len(joined_phones) > 0:
                    ApiProcessor().set('chat', { 
                        'id': self.id, 
                        'internalId': self.internal_id, 
                        'accessHash': self.access_hash, 
                        'isAvailable': self.is_available, 
                        'phones': [{ 'id': phone.id } for phone in joined_phones]
                    })
                else:
                    ApiProcessor().set('chat', { 'id': self.id, 'isAvailable': False })
            else:
                ApiProcessor().set('chat', { 'id': self.id, 'isAvailable': False })
        else:
            new_phones = self.phones
            
            joined = []
            to_join = []
            
            for phone in new_phones:
                if await phone.is_participant(self):
                    joined.append(phone)
                else:
                    to_join.append(phone)
            
            for phone in to_join:
                try:
                    # if len(joined) > 0:
                    #     chat = await joined[0].invite(phone, self)
                    # else:
                        chat = await phone.join(self)
                except:
                    i = next((i for i, p in enumerate(new_phones) if p.id == phone.id), None)
                    
                    if i != None:
                        del new_phones[i]
            
            if len(self.phones) != len(new_phones):
                ApiProcessor().set('chat', { 'id': self.id, 'phones': [{ 'id': phone.id } for phone in new_phones] })
            
        return self
    
    def parse(self):
        if not self.is_available:
            return
        
        print(f"Chat {self.id} now starts to parse.")
        logging.debug(f"Chat {self.id} now starts to parse.")
        
        loop = asyncio.new_event_loop()
        
        #--> MEMBERS -->#
        if self.members_thread == None:
            self.members_thread = MembersParserThread(self, self.phones, loop)
            self.members_thread.start()
        else:
            print(f"Members parsing thread for chat {self.id} now is running.")
            logging.debug(f"Members parsing thread for chat {self.id} now is running.")
        #--< MEMBERS --<#
        
        #--> MESSAGES -->#
        if self.messages_thread == None:
            self.messages_thread = MessagesParserThread(self, self.phones, loop)
            self.messages_thread.start()
        else:
            print(f"Messages parsing thread for chat {self.id} now is running.")
            logging.debug(f"Messages parsing thread for chat {self.id} now is running.")
        #--< MESSAGES --<#
    