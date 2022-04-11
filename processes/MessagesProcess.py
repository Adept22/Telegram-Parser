import multiprocessing
import asyncio
import logging
from telethon import types, errors, functions

from entity.Member import Member
from entity.ChatMember import ChatMember
from entity.ChatMemberRole import ChatMemberRole
from entity.Message import Message

from processes.MessageMediaProcess import MessageMediaProcess

class MessagesProcess(multiprocessing.Process):
    def __init__(self, chat):
        multiprocessing.Process.__init__(self, name=f"MessagesProcess-{chat.id}", daemon=True)
        
        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
        
    async def get_member(self, client, user_id):
        member = Member(internalId=user_id)

        await member.expand(client)

        return member.save()
        
    async def get_chat_member(self, participant, member):
        chat_member = ChatMember(chat=self.chat, member=member)

        await chat_member.expand(participant)

        return chat_member.save()
    
    async def get_chat_member_role(self, participant, chat_member):
        chat_member_role = ChatMemberRole(member=chat_member)

        await chat_member_role.expand(participant)

        return chat_member_role.save()

    async def get_message_participant(self, client, tg_message):
        try:
            participant_request = await client(
                functions.channels.GetParticipantRequest(
                    channel=tg_message.input_chat,
                    participant=tg_message.input_sender
                )
            )
        except (
            errors.ChannelPrivateError,
            errors.ChatAdminRequiredError,
            errors.UserIdInvalidError,
            errors.UserNotParticipantError
        ) as ex:
            logging.error(f"Can't get participant data for {tg_message.from_id.user_id} with chat {self.chat.internal_id}. Exception: {ex}.")
        else:
            return participant_request.participant

        return None
    
    def get_fwd(self, fwd_from):
        fwd_from_id = None
        fwd_from_name = None
        
        if fwd_from != None:
            if fwd_from.from_id != None:
                if type(fwd_from.from_id) == types.PeerChannel:
                    fwd_from_id = fwd_from.from_id.channel_id
                elif type(fwd_from.from_id) == types.PeerUser:
                    fwd_from_id = fwd_from.from_id.user_id
            
            if fwd_from.from_name != None:
                fwd_from_name = fwd_from.from_name
            else:
                fwd_from_name = "Неизвестно"
                
        return fwd_from_id, fwd_from_name

    async def get_entity(self, client):
        try:
            return await client.get_entity(entity=types.PeerChannel(channel_id=self.chat.internal_id))
        except ValueError:
            return await client.get_entity(entity=types.PeerChat(chat_id=self.chat.internal_id))

    async def async_run(self):
        for phone in self.chat.phones:
            logging.info(f"Recieving messages from chat {self.chat.id}.")
            
            try:
                client = await phone.new_client(loop=self.loop)

                tg_chat = await self.get_entity(client)
                
                all_messages = await client.get_messages(entity=tg_chat, limit=0, max_id=0)

                logging.info(f"Chat {self.chat.id} total messages {all_messages.total}.")
                
                async for tg_message in client.iter_messages(entity=tg_chat, max_id=0):
                    logging.debug(f"Chat {self.chat.id}. Receive message {tg_message.id}/{all_messages.total}")
                    
                    if not isinstance(tg_message, types.Message):
                        continue
                    
                    try:
                        logging.debug(f"Saving message '{tg_message.id}' at '{tg_message.date}'")
                        
                        fwd_from_id, fwd_from_name = self.get_fwd(tg_message.fwd_from)

                        chat_member = None
                        reply_to = None

                        if isinstance(tg_message.from_id, types.PeerUser):
                            member = await self.get_member(client, tg_message.from_id.user_id)
                            participant = await self.get_message_participant(client, tg_message)
                            chat_member = await self.get_chat_member(participant, member)
                            chat_member_role = await self.get_chat_member_role(participant, chat_member)

                        if tg_message.reply_to != None:
                            reply_to = Message(internalId=tg_message.reply_to.reply_to_msg_id, chat=self.chat)
                            reply_to.save()

                        message = Message(
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
                    except Exception as ex:
                        logging.error(f"Can't save chat {self.chat.id} message {tg_message.id}.")
                        logging.exception(ex)
                    else:
                        logging.debug(f"Message {message.id} saved.")

                        if tg_message.media != None:
                            meessage_media_proces = MessageMediaProcess(phone, message, tg_message)
                            meessage_media_proces.start()
                else:
                    logging.info(f"Chat {self.chat.id} messages download success.")
            except (
                errors.ChannelInvalidError,
                errors.ChannelPrivateError,
                errors.ChatIdInvalidError,
                errors.PeerIdInvalidError
            ) as ex:
                logging.error(f"Chat {self.chat.id} not available.")
                logging.exception(ex)

                self.chat.is_available = False
            except Exception as ex:
                logging.error(f"Can\'t get chat {self.chat.id} messages using phone {phone.id}.")
                logging.exception(ex)

                self.chat.remove_phone(phone)
                
                continue
            else:
                break
        else:
            logging.error(f"Chat {self.chat.id} messages download failed.")
        
    def run(self):
        asyncio.run(self.async_run())