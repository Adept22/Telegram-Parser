from core.ClientFactory import ClientFactory
from models.User import User
from processors.UsersJSONProcessor import UsersJSONProcessor
import asyncio
from config import USER_FIELDS, BASE_DIR, USERS_XLSX_FILENAME
import os
from telethon.errors import ChatAdminRequiredError


from processors.XLSXFileProcessor import XLSXFileProcessor


class UsersParser():
    def __init__(self, channel_link):
        self.client = ClientFactory().get_client()
        self.channel_link = channel_link
        self.channel = None

    def parse(self):
        try:
            self.client.loop.run_until_complete(self.get_users())
        except ChatAdminRequiredError:
            print(f"Don't have enough permissions to parse users from {self.channel.title} :(")

    async def get_users(self):
        result_users = []
        self.channel = await self.client.get_entity(self.channel_link)
        self.channel.title = self.channel.title.replace('/', '-')
        self.channel.link = self.channel_link
        await asyncio.sleep(1)
        users = await self.client.get_participants(self.channel)
        await asyncio.sleep(1)
        users_count = len(users)

        for index, user_object in enumerate(users):
            print(f'{self.channel.title}. Receiving users... {index + 1} / {users_count}.')
            user = User(user_object)
            users_processor = UsersJSONProcessor(channel_name=self.channel.title)
            history_user = users_processor.get_item_by_id(user.id)
            if history_user:
                result_users.append(history_user)
            else:
                await user.enrich(channel=self.channel)
                users_processor.add_user(user)
                result_users.append(user.serialize())

        if not len(result_users):
            return
        xlsx_processor = XLSXFileProcessor(fields_config=USER_FIELDS, xlsx_filename=os.path.join(BASE_DIR, f'results/{self.channel.title}/users/{USERS_XLSX_FILENAME}'))
        xlsx_processor.convert(result_users)
        return result_users
