import threading
import asyncio
import logging

class ChatThread(threading.Thread):
    def __init__(self, phone, chat):
        threading.Thread.__init__(self)
        self.phone = phone
        self.chat = chat
        
    async def get_chat(self):
        
        #--> MEMBERS -->#
        logging.debug("Creating users parsing thread for chat {}...".format(self.chat.id))
        print("Creating users parsing thread for chat {}...".format(self.chat.id))
        
        users_thread = UsersParser(phone=self.phone, channel_link=self.chat)
        
        logging.debug("Starting users parsing thread for chat {}...".format(self.chat.id))
        print("Starting users parsing thread for chat {}...".format(self.chat.id))
        
        users_thread.start()
        
        #--< MEMBERS --<#
        #--> HISTORY -->#
        
        logging.debug("Creating history parsing thread for chat {}...".format(self.chat.id))
        print("Creating history parsing thread for chat {}...".format(self.chat.id))
        
        history_thread = HistoryParser(phone=self.phone, channel_link=self.chat)
        
        logging.debug("Starting history parsing thread for chat {}...".format(self.chat.id))
        print("Starting history parsing thread for chat {}...".format(self.chat.id))
        
        history_thread.start()
        
        #--< HISTORY --<#
        
    async def async_run(self):
        while True:
            await self.get_chat()
            
    def run(self):
        print("Starting thread for chat {} \'{}\'.".format(self.chat.id, self.chat.name))
        logging.debug("Starting thread for chat {} \'{}\'.".format(self.chat.id, self.chat.name))
        
        asyncio.run(self.async_run())