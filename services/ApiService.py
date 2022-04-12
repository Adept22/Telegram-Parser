import math, os, requests, logging
from urllib.parse import urlencode

import exceptions

class ApiService():
    def get_sort(self, body=None):
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

    def get(self, type, body=None):
        if body and body.get('id') != None:
            method = 'GET'
            url = os.environ['API_URL'] + '/' + type + '/' + body['id']
        else:
            method = 'POST'
            url = os.environ['API_URL'] + '/' + type + '/find' + self.get_sort(body)

        return self.send(method, url, body)

    def set(self, type, body=None):
        if body and body.get('id') != None:
            method = 'PUT'
            url = os.environ['API_URL'] + '/' + type + '/' + body['id']
        else:
            method = 'POST'
            url = os.environ['API_URL'] + '/' + type
        
        try:
            return self.send(method, url, body)
        except requests.exceptions.HTTPError as ex:
            if ex.response.status_code == 409:
                raise exceptions.UniqueConstraintViolationError(ex)
            else:
                raise ex

    def delete(self, type, body=None):
        if not body or body.get('id') == None:
            raise Exception('Не указан идентификатор')

        return self.send("DELETE", os.environ['API_URL'] + '/' + type + '/' + body['id'])

    def upload(self, type, body, file):
        if not body or body.get('id') == None:
            raise Exception('Не указан идентификатор')

        return self.send("POST", os.environ['API_URL'] + '/' + type + '/' + body['id'] + '/upload', files={'file': open(file, 'rb')})

    def chunked(self, type, body, file, chunk_size=1048576):
        if not body or body.get('id') == None:
            raise Exception('Не указан идентификатор')

        total_size = os.path.getsize(file)
        total_chunks = math.ceil(total_size / chunk_size)
        filename = os.path.basename(file)
        chunk_number = 0

        with open(file, 'rb') as infile:
            while (chunk := infile.read(chunk_size)):
                self._chunk(type, body, filename, chunk, chunk_number, chunk_size, total_chunks, total_size)

                chunk_number += 1

        return None

    def _check_chunk(self, type, body, filename, chunk_number, chunk_size):
        logging.debug(f"Checking chunk {chunk_number} of {filename}.")
        
        try:
            self.send(
                "GET", 
                os.environ['API_URL'] + '/' + type + '/' + body['id'] + '/chunk', 
                params={
                    "filename": filename, 
                    "chunkNumber": chunk_number, 
                    "chunkSize": chunk_size
                }
            )
        except requests.exceptions.HTTPError as ex:
            if ex.response.status_code == 404:
                return False
            else:
                raise ex
        else:
            return True

    def _chunk(self, type, body, filename, chunk, chunk_number, chunk_size, total_chunks, total_size):
        if self._check_chunk(type, body, filename, chunk_number, chunk_size) == True:
            return

        logging.debug(f"Sending chunk {chunk_number}/{total_chunks}.")

        self.send(
            "POST", 
            os.environ['API_URL'] + '/' + type + '/' + body['id'] + '/chunk', 
            params={
                "filename": filename, 
                "chunkNumber": chunk_number, 
                "totalChunks": total_chunks, 
                "totalSize": total_size
            },
            files={ 'chunk': chunk }
        )

    def send(self, method, url, body=None, params=None, files=None):
        r = requests.request(
            method, 
            url, 
            headers={'Accept': 'application/json'}, 
            json=body, 
            params=params, 
            files=files, 
            verify=False
        )
        r.raise_for_status()
        
        if r.status_code == 204:
            return None

        return r.json()