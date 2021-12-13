from models.Channel import Channel
from telethon.tl.functions.messages import GetHistoryRequest
from core.ClientFactory import ClientFactory

class LinkParser():
    def __init__(self, channel_link):
        self.client = ClientFactory().get_client()
        self.channel_link = channel_link

    def parse(self):
        return self.client.loop.run_until_complete(self.get_channel())

    async def get_channel(self):
        channel = await self.client.get_entity(self.channel_link)
        return Channel(channel)
        