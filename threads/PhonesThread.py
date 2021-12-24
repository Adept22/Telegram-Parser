import threading
import time
import asyncio
import logging
import traceback
import sys

from telethon import sync, functions, errors, types

from models.Phone import Phone

from core.PhonesManager import PhonesManager

from processors.ApiProcessor import ApiProcessor

phones = PhonesManager()

class PhonesThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        
    async def auth_phone(self):
        for id in phones:
            phone = phones[id]
            
            try:
                is_user_authorized = await phone.client.is_user_authorized()

                logging.debug("Thread phones: phone is_user_authorized {}.".format(is_user_authorized))
                
                if not is_user_authorized:
                    if phone.code != None and phone.code_hash != None:
                        isVerified = False
                        
                        try:
                            await phone.client.sign_in(
                                phone=phone.number, 
                                code=phone.code, 
                                phone_code_hash=phone.code_hash
                            )
                        except Exception as ex:
                            logging.error("Thread phones: cannot authentificate phone {} with code {}. Exception: {}".format(id, phone.code, ex))
                        else:
                            isVerified = True
                            
                        changed_phone = ApiProcessor().set('phone', { 'id': id, 'isVerified': isVerified, 'code': None, 'codeHash': None })
                        
                        phones[id].from_dict(changed_phone)
                    elif phone.code_hash == None:
                        logging.debug("Thread phones: try send code for phone {}.".format(id))
                        
                        phone.send_code_request()
                    else:
                        continue
                else:
                    logging.debug("Thread phones: phone {} ({}) can be used.".format(id, phone.number))
            except Exception as ex:
                print(traceback.format_exc())
                # or
                print(sys.exc_info()[2])
                logging.error("Thread phones: unexpected phone object. Exception: {}".format(ex))
        
    async def async_run(self):
        while True:
            await self.get_phones()
            
    def run(self):
        asyncio.run(self.async_run())