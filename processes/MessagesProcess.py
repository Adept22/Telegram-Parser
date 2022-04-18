import multiprocessing, setproctitle, typing, asyncio, logging, telethon
import entities, threads, exceptions

if typing.TYPE_CHECKING:
    from telethon import TelegramClient

class MessagesProcess(multiprocessing.Process):
    def __init__(self, chat: 'entities.TypeChat'):
        multiprocessing.Process.__init__(self, name=f"MessagesProcess-{chat.id}", daemon=True)

        setproctitle.setproctitle(self.name)
        
        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
        
    async def get_member(self, client: 'TelegramClient', user: 'telethon.types.TypePeer') -> 'entities.TypeMember':
        member = entities.Member(internalId=user.user_id)

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

    async def get_message_participant(self, client: 'TelegramClient', input_chat, input_sender: 'telethon.types.TypeInputPeer'):
        peer = telethon.utils.get_peer(self.chat.internalId or 0)

        try:
            if isinstance(peer, telethon.types.PeerChannel):
                participant: 'telethon.types.TypeChannelParticipant' = await client(
                    telethon.tl.functions.channels.GetParticipantRequest(input_chat, input_sender)
                )
                return participant.participant
            elif isinstance(peer, telethon.types.PeerChat):
                chat_full: 'telethon.types.TypeChatFull' = await client(telethon.tl.functions.messages.GetFullChatRequest(self.chat.internalId))
                participants = [p.participant for p in chat_full.participants if p.user_id == input_sender.user_id] \
                    if chat_full.participants.participants else []
                return participants[0] if len(participants) > 0 else None
        except telethon.errors.RPCError as ex:
            logging.werning(f"Can't get participant data for {input_sender.user_id} with chat {self.chat.internalId}. Exception: {ex}.")

        return None
    
    def get_fwd(self, fwd_from: 'telethon.types.TypeMessageFwdHeader | None'):
        if fwd_from != None:
            fwd_from_id = None
        
            if fwd_from.from_id != None:
                if isinstance(fwd_from.from_id, telethon.types.PeerChannel):
                    fwd_from_id = fwd_from.from_id.channel_id
                elif isinstance(fwd_from.from_id, telethon.types.PeerUser):
                    fwd_from_id = fwd_from.from_id.user_id
            
            return fwd_from_id, fwd_from.from_name if fwd_from.from_name != None else "Неизвестно"
            
        return None, None

    async def handle_message(self, chat_phone: 'entities.TypePhone', client: 'TelegramClient', tg_message: 'telethon.types.TypeMessage'):
        logging.debug(f"Chat {self.chat.id}. Receive message {tg_message.id}.")
        
        if not isinstance(tg_message, telethon.types.Message):
            return
        
        try:
            fwd_from_id, fwd_from_name = self.get_fwd(tg_message.fwd_from)

            if isinstance(tg_message.from_id, telethon.types.PeerUser):
                member = await self.get_member(client, tg_message.from_id)
                participant = await self.get_message_participant(client, tg_message.input_chat, tg_message.input_sender)
                chat_member = await self.get_chat_member(participant, member)
                chat_member_role = await self.get_chat_member_role(participant, chat_member)
            else:
                chat_member = None

            if tg_message.reply_to != None:
                reply_to = entities.Message(internalId=tg_message.reply_to.reply_to_msg_id, chat=self.chat)
                reply_to.save()
            else:
                reply_to = None

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
                message_media_thread = threads.MessageMediaThread(chat_phone, message, tg_message)
                message_media_thread.start()

            return message

        return None

    async def async_run(self):
        for chat_phone in self.chat.phones:
            chat_phone: 'entities.TypeChatPhone'

            logging.info(f"Recieving messages from chat {self.chat.id}.")

            try:
                client: 'TelegramClient' = await chat_phone.phone.new_client(loop=self.loop)
            except exceptions.ClientNotAvailableError as ex:
                logging.critical(f"Phone {chat_phone.id} client not available.")

                self.chat.phones.remove(chat_phone)
                
                continue

            async def handle_event(event):
                await self.handle_message(chat_phone.phone, client, event.message)

            client.add_event_handler(handle_event, telethon.events.NewMessage(chats=self.chat.internalId, incoming=True))

            while True:
                try:
                    async for tg_message in client.iter_messages(entity=self.chat.internalId, max_id=0):
                        tg_message: 'telethon.types.TypeMessage'
                        
                        await self.handle_message(chat_phone, client, tg_message)
                    else:
                        logging.info(f"Chat {self.chat.id} messages download success.")
                except telethon.errors.FloodWaitError as ex:
                    logging.error(f"Telegram messages request of chat {self.chat.id} must wait {ex.seconds} seconds.")

                    await asyncio.wait(ex.seconds)
                except telethon.errors.RPCError as ex:
                    logging.critical(f"Chat {self.chat.id} not available. Exception {ex}")

                    self.chat.isAvailable = False
                    self.chat.save()

                    break
                else:
                    logging.info(f"Chat \'{self.chat.id}\' participants download success.")
        else:
            logging.error(f"Chat {self.chat.id} messages download failed.")
        
    def run(self):
        asyncio.run(self.async_run())