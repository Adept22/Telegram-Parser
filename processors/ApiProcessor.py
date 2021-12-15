import requests
from config import API

class ApiProcessor():
    def __init__(self):
        self.base_url = API['protocol'] + '://' + API['domain'] + '/' + API['path']

    def get(self, type, body = None):
        if body and 'id' in body:
            method = 'GET'
            url = self.base_url + '/' + type + '/' + body['id']
        else:
            method = 'POST'
            url = self.base_url + '/' + type + '/find'

        return self.send(method, url, body)

    def set(self, type, body = None):
        if body and 'id' in body:
            method = 'PUT'
            url = self.base_url + '/' + type + '/' + body['id']
        else:
            method = 'POST'
            url = self.base_url + '/' + type

        return self.send(method, url, body)

    def delete(self, type, body = None):
        if not body or not 'id' in body:
            raise Exception('Не указан идентификатор')

        return requests.delete(self.base_url + '/' + type + '/' + body['id'])

    def send(self, method, url, body):
        print(url)
        r = requests.request(method, url, data = body, verify = False)
        r.raise_for_status()

        return r.json()