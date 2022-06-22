import asyncio
import os
from core.ClientFactory import ClientFactory
from config import BASE_DIR, USER_FIELDS


class User:
    def __init__(self, user_object):

        self.user_keys = ['first_name', 'last_name', 'username']
        self.user_object = user_object
        self.user_dict = user_object.to_dict()
        self.username = None
        self.last_name = None
        self.first_name = None
        for key in self.user_keys:
            if key in self.user_dict:
                self.__dict__[key] = self.user_dict[key]
        self.client = ClientFactory().get_client()
        self.channel = None
        self.channel_link = None
        self.has_photo = False
        self.id = self.user_dict['id']

    async def enrich(self, channel):

        self.channel = channel.title
        self.channel_link = channel.link
        photos = await self.client.get_profile_photos(self.user_object)
        await asyncio.sleep(1)
        try:
            photo_count = 1
            for photo in photos:
                file = await self.client.download_media(photo, os.path.join(BASE_DIR, f'results/{self.channel}/users/photos/{self.id}-{photo_count}'))
                photo_count += 1
                await asyncio.sleep(1)
                self.has_photo = True
        except IndexError:
            pass
        except OSError as exc:
            if exc.errno == 36:
                self.id = self.user_dict['id']
                photo_count = 1
                for photo in photos:
                    file = await self.client.download_media(photo, os.path.join(BASE_DIR, f'results/{self.channel}/users/photos/{self.id}-{photo_count}'))
                    photo_count += 1
                    await asyncio.sleep(1)
                    self.has_photo = True
            else:
                raise

    def serialize(self):
        result = {}
        for key in USER_FIELDS.keys():
            if key in self.__dict__ and self.__dict__[key]:
                result[key] = self.__dict__[key]
        return result
