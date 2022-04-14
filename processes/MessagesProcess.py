import multiprocessing, asyncio, logging, telethon
import entities, processes, exceptions, helpers

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from telethon import TelegramClient

class MessagesProcess(multiprocessing.Process):
    def __init__(self, chat: 'entities.TypeChat'):
        multiprocessing.Process.__init__(self, name=f"MessagesProcess-{chat.id}")
        
        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
        
    async def get_member(self, client: 'TelegramClient', user_id: 'int') -> 'entities.TypeMember':
        member = entities.Member(internalId=user_id)

        await member.expand(client)

        return member.save()
        
    async def get_chat_member(self, participant, member):
        chat_member = entities.ChatMember(chat=self.chat, member=member)

        await chat_member.expand(participant)

        return chat_member.save()
    
    async def get_chat_member_role(self, participant, chat_member):
        chat_member_role = entities.ChatMemberRole(member=chat_member)

        await chat_member_role.expand(participant)

        return chat_member_role.save()

    async def get_message_participant(self, client: 'TelegramClient', input_chat, sender):
        try:
            participants = await client.get_participants(
                entity=input_chat, 
                search=sender.username if sender.username != None else f"{sender.first_name} {sender.last_name}"
            )
        except telethon.errors.RPCError as ex:
            logging.error(f"Can't get participant data for {sender.id} with chat {self.chat.internalId}. Exception: {ex}.")
        else:
            if len(participants) > 0:
                return participants[0].participant

        return None
    
    def get_fwd(self, fwd_from):
        fwd_from_id = None
        fwd_from_name = None
        
        if fwd_from != None:
            if fwd_from.from_id != None:
                if type(fwd_from.from_id) == telethon.types.PeerChannel:
                    fwd_from_id = fwd_from.from_id.channel_id
                elif type(fwd_from.from_id) == telethon.types.PeerUser:
                    fwd_from_id = fwd_from.from_id.user_id
            
            if fwd_from.from_name != None:
                fwd_from_name = fwd_from.from_name
            else:
                fwd_from_name = "Неизвестно"
                
        return fwd_from_id, fwd_from_name

    async def async_run(self):
        if len(self.chat.phones) == 0:
            logging.warning(f"No phones for chat {self.chat.id}.")

            return

        for phone in self.chat.phones:
            logging.info(f"Recieving messages from chat {self.chat.id}.")

            try:
                client = await phone.new_client(loop=self.loop)
            except exceptions.ClientNotAvailableError as ex:
                logging.error(f"Phone {phone.id} client not available.")

                self.chat.remove_phone(phone)
                self.chat.save()
                
                continue

            try:
                tg_chat = await helpers.get_entity(client, self.chat)
            except ValueError as ex:
                logging.error(f"Can\'t get chat {self.chat.id} using phone {phone.id}. Exception {ex}")

                self.chat.isAvailable = False
                self.chat.save()

                break
            else:
                new_internal_id = telethon.utils.get_peer_id(tg_chat)
                
                if self.chat.internalId != new_internal_id:
                    logging.info(f"Chat {self.chat.id} internal ID changed. Old ID {self.chat.internalId}. New ID {new_internal_id}.")
                    
                    self.chat.internalId = new_internal_id

                    self.chat.save()

            try:
                async for tg_message in client.iter_messages(entity=tg_chat, max_id=0):
                    logging.debug(f"Chat {self.chat.id}. Receive message {tg_message.id}.")
                    
                    if not isinstance(tg_message, telethon.types.Message):
                        continue
                    
                    try:
                        logging.debug(f"Saving message '{tg_message.id}' at '{tg_message.date}'")
                        
                        fwd_from_id, fwd_from_name = self.get_fwd(tg_message.fwd_from)

                        chat_member = None
                        reply_to = None

                        if isinstance(tg_message.from_id, telethon.types.PeerUser):
                            member = await self.get_member(client, tg_message.from_id.user_id)
                            participant = await self.get_message_participant(client, tg_message.input_chat, tg_message.sender)
                            chat_member = await self.get_chat_member(participant, member)
                            chat_member_role = await self.get_chat_member_role(participant, chat_member)

                        if tg_message.reply_to != None:
                            reply_to = entities.Message(internalId=tg_message.reply_to.reply_to_msg_id, chat=self.chat)
                            reply_to.save()

                        message = entities.Message(
                            internalId=tg_message.id, 
                            text=tg_message.message, 
                            chat=self.chat, 
                            member=chat_member,
                            replyTo=reply_to, 
                            isPinned=tg_message.pinned,     
                            forwardedFromId=fwd_from_id, 
                            forwardedFromName=fwd_from_name, 
                            groupedId=tg_message.grouped_id, 
                            date=tg_message.date.isoformat() 
                        )
                        message.save()
                    except exceptions.RequestException as ex:
                        logging.error(f"Can't save chat {self.chat.id} message {tg_message.id}. Exception {ex}")
                    else:
                        logging.debug(f"Message {message.id} saved.")

                        if tg_message.media != None:
                            meessage_media_proces = processes.MessageMediaProcess(phone, message, tg_message)
                            meessage_media_proces.start()
                else:
                    logging.info(f"Chat {self.chat.id} messages download success.")
            except telethon.errors.RPCError as ex:
                logging.error(f"Chat {self.chat.id} not available. Exception {ex}")

                self.chat.isAvailable = False
                self.chat.save()

            break
        else:
            logging.error(f"Chat {self.chat.id} messages download failed.")
        
    def run(self):
        asyncio.run(self.async_run())