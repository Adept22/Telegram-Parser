import math, os, requests
from urllib.parse import urlencode

import exceptions

class ApiService():
    def get_sort(self, body: 'dict' = None) -> 'str':
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

    def get(self, type: 'str', body: 'dict' = None) -> 'dict | list[dict]':
        if body and body.get('id') != None:
            method = 'GET'
            url = os.environ['API_URL'] + '/' + type + '/' + body['id']
        else:
            method = 'POST'
            url = os.environ['API_URL'] + '/' + type + '/find' + self.get_sort(body)

        return self.send(method, url, body)

    def set(self, type: 'str', body: 'dict' = None) -> 'dict':
        if body and body.get('id') != None:
            method = 'PUT'
            url = os.environ['API_URL'] + '/' + type + '/' + body['id']
        else:
            method = 'POST'
            url = os.environ['API_URL'] + '/' + type
        
        return self.send(method, url, body)

    def delete(self, type: 'str', body: 'dict') -> 'None':
        if body.get('id') == None:
            raise Exception('Не указан идентификатор')

        return self.send("DELETE", os.environ['API_URL'] + '/' + type + '/' + body['id'])

    def upload(self, type: 'str', body: 'dict', filepath: 'str') -> 'None':
        if body.get('id') == None:
            raise Exception('Не указан идентификатор')

        return self.send("POST", os.environ['API_URL'] + '/' + type + '/' + body['id'] + '/upload', files={'file': open(filepath, 'rb')})

    def chunked(self, type: 'str', body: 'dict', filepath: 'str', chunk_size: 'int' = 1048576) -> 'None':
        if body.get('id') == None:
            raise Exception('Не указан идентификатор')

        total_size = os.path.getsize(filepath)
        total_chunks = math.ceil(total_size / chunk_size)
        filename = os.path.basename(filepath)
        chunk_number = 0

        with open(filepath, 'rb') as infile:
            while (chunk := infile.read(chunk_size)):
                self._chunk(type, body, filename, chunk, chunk_number, chunk_size, total_chunks, total_size)

                chunk_number += 1

        return None

    def _check_chunk(self, type: 'str', body: 'dict', filename: 'str', chunk_number: 'int', chunk_size: 'int' = 1048576) -> 'bool':
        if body.get('id') == None:
            raise Exception('Не указан идентификатор')

        params = {
            "filename": filename, 
            "chunkNumber": chunk_number, 
            "chunkSize": chunk_size
        }
        
        try:
            self.send("GET", os.environ['API_URL'] + '/' + type + '/' + body['id'] + '/chunk', params=params)
        except requests.exceptions.HTTPError as ex:
            if ex.response.status_code == 404:
                return False
            else:
                raise ex
        else:
            return True

    def _chunk(self, type: 'str', body: 'dict', filename: 'str', chunk: 'bytes', chunk_number: 'int', chunk_size: 'int', total_chunks: 'int', total_size: 'int') -> 'None':
        if self._check_chunk(type, body, filename, chunk_number, chunk_size) == True:
            return

        params={"filename": filename, "chunkNumber": chunk_number, "totalChunks": total_chunks, "totalSize": total_size}
        files={"chunk": chunk}

        self.send("POST", os.environ['API_URL'] + '/' + type + '/' + body['id'] + '/chunk', params=params, files=files)

    def send(self, method: 'str', url: 'str', body: 'dict' = None, params: 'dict' = None, files: 'dict' = None) -> 'dict | list[dict] | None':
        r = requests.request(
            method, 
            url, 
            headers={'Accept': 'application/json'}, 
            json=body, 
            params=params, 
            files=files 
        )
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as ex:
            r = ex.response

            json = r.json()

            if r.status_code == 409:
                raise exceptions.UniqueConstraintViolationError(json["message"])

            raise exceptions.RequestException(json["message"])
        
        if r.status_code == 204:
            return None

        return r.json()
        