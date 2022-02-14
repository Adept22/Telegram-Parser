from multiprocessing.connection import wait
import threading
import logging

from models.Chat import Chat
from processors.ApiProcessor import ApiProcessor
from threads.KillableThread import KillableThread

class ChatsThread(KillableThread):
    def __init__(self):
        threading.Thread.__init__(self, name=f'ChatsThread')

        self.chats = {}

    def set_chat(self, chat):
        if chat['isAvailable'] == False:
            if chat['id'] in self.chats:
                del self.chats[chat['id']]
            
            return
        
        if chat['id'] in self.chats:
            logging.debug(f"Updating chat {chat['id']}.")
            
            self.chats[chat['id']].from_dict(chat)
        else:
            logging.debug(f"Setting up new chat {chat['id']}.")

            self.chats[chat['id']] = Chat(chat).run()

    def get_all_chats(self, chats=[], start=0, limit=50):
        new_chats = ApiProcessor().get('chat', {"isAvailable": True, "_start": start, "_limit": limit})

        if len(new_chats) > 0:
            chats += self.get_all_chats(new_chats, start+limit, limit)
        
        return chats

    def run(self):
        chats = self.get_all_chats()

        logging.debug(f"Received {len(chats)} chats.")
        
        for chat in chats:
            self.set_chat(chat)

        while True:
            pass
