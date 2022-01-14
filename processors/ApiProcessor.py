import os
import requests
from urllib.parse import urlencode

class ApiProcessor():
    def get_sort(self, body = None):
        if body != None:
            sort_props = ['_start', '_limit', '_order', '_sort']
            
            sort = {}
            
            for key, value in body.items():
                if key in sort_props:
                    sort[key] = value
                    
            if len(sort.items()) > 0:
                for key in sort.keys():
                    del body[key]
                
                return '?' + urlencode(sort)
        return ''

    def get(self, type, body = None):
        if body and 'id' in body:
            method = 'GET'
            url = os.environ['API_URL'] + '/' + type + '/' + body['id']
        else:
            method = 'POST'
            url = os.environ['API_URL'] + '/' + type + '/find' + self.get_sort(body)

        return self.send(method, url, body)

    def set(self, type, body = None):
        if body and 'id' in body:
            method = 'PUT'
            url = os.environ['API_URL'] + '/' + type + '/' + body['id']
        else:
            method = 'POST'
            url = os.environ['API_URL'] + '/' + type

        return self.send(method, url, body)

    def delete(self, type, body = None):
        if not body or not 'id' in body:
            raise Exception('Не указан идентификатор')

        return requests.delete(os.environ['API_URL'] + '/' + type + '/' + body['id'])

    def send(self, method, url, body = None):
        r = requests.request(method, url, json = body, verify = False)
        r.raise_for_status()

        return r.json()