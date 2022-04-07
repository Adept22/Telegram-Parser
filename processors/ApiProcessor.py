import math
import os
import tempfile
import requests
import logging
from urllib.parse import urlencode

from errors.UniqueConstraintViolationError import UniqueConstraintViolationError

class ApiProcessor():
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
        if body and 'id' in body:
            method = 'GET'
            url = os.environ['API_URL'] + '/' + type + '/' + body['id']
        else:
            method = 'POST'
            url = os.environ['API_URL'] + '/' + type + '/find' + self.get_sort(body)

        return self.send(method, url, body)

    def set(self, type, body=None):
        if body and 'id' in body:
            method = 'PUT'
            url = os.environ['API_URL'] + '/' + type + '/' + body['id']
        else:
            method = 'POST'
            url = os.environ['API_URL'] + '/' + type
        
        try:
            return self.send(method, url, body)
        except requests.exceptions.HTTPError as ex:
            if ex.response.status_code == 409:
                raise UniqueConstraintViolationError(ex)
            else:
                raise ex

    def delete(self, type, body=None):
        if not body or not 'id' in body:
            raise Exception('Не указан идентификатор')

        return self.send("DELETE", os.environ['API_URL'] + '/' + type + '/' + body['id'])

    def upload(self, type, body, file):
        if not body or not 'id' in body:
            raise Exception('Не указан идентификатор')

        return self.send("POST", os.environ['API_URL'] + '/' + type + '/' + body['id'] + '/upload', files={'file': open(file, 'rb')})

    def chunked(self, type, body, file, chunk_size=1048576):
        if not body or not 'id' in body:
            raise Exception('Не указан идентификатор')

        total_size = os.path.getsize(file)
        total_chunks = math.ceil(total_size / chunk_size)
        chunk_number = 0

        with open(file, 'rb') as infile:
            logging.debug(f"Open file {file} for chunks send")

            while (chunk := infile.read(chunk_size)):
                logging.debug(f"Open chunk {chunk_number}/{total_chunks} of {file}")
                with tempfile.TemporaryFile() as tmp:
                    logging.debug(f"Write chunk of {file} in temp file")

                    tmp.write(chunk)
                    tmp.seek(0)

                    logging.debug(f"Sending chunk {chunk_number}/{total_chunks} of {file}")

                    self.send(
                        "POST", 
                        os.environ['API_URL'] + '/' + type + '/' + body['id'] + '/chunk', 
                        params={
                            "filename": os.path.basename(file), 
                            "chunkNumber": chunk_number, 
                            "totalChunks": total_chunks, 
                            "totalSize": total_size
                        },
                        files={'chunk': tmp}
                    )

                chunk_number += 1

        return None

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