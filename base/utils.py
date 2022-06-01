import re, telethon


class TelegramClient(telethon.TelegramClient):
    import base.models as models
    def __init__(self, phone: 'models.TypePhone', *args, **kwargs):
        from telethon.sessions import StringSession

        self.phone = phone

        super(TelegramClient, self).__init__(*args, **kwargs, connection_retries=-1, retry_delay=5, session=StringSession(phone.session), api_id=phone.parser.api_id, api_hash=phone.parser.api_hash)

    async def start(self):
        from base.exceptions import UnauthorizedError

        if not self.is_connected():
            await self.connect()

        if await self.is_user_authorized() and await self.get_me() != None:
            return self
        else:
            raise UnauthorizedError(f'Phone not authorized')
            
    async def __aenter__(self):
        return await self.start()


class ApiService():
    def get(self, type: 'str', body: 'dict') -> 'dict | list[dict]':
        import urllib.parse

        path = body['id'] + "/" if body.get('id') != None else "?" + urllib.parse.urlencode(body)

        return self.send("GET", type, path, body)

    def set(self, type: 'str', body: 'dict') -> 'dict':
        method = 'PUT' if body.get('id') != None else 'POST'
        path = body['id'] + "/" if body.get('id') != None else ""
        
        return self.send(method, type, path, body)

    def delete(self, type: 'str', body: 'dict') -> 'None':
        if body.get('id') == None:
            raise Exception('Не указан идентификатор')

        return self.send("DELETE", type, body['id'] + "/")

    def _check_chunk(self, type: 'str', body: 'dict', filename: 'str', chunk_number: 'int', chunk_size: 'int' = 1048576) -> 'bool':
        import base.exceptions as exceptions

        if body.get('id') == None:
            raise Exception('Не указан идентификатор')

        try:
            self.send("GET", type, body['id'] + "/chunk/", params={"filename": filename, "chunkNumber": chunk_number, "chunkSize": chunk_size})
        except exceptions.RequestException as ex:
            if ex.code == 404:
                return False
            else:
                raise ex
        else:
            return True

    def _chunk(self, type: 'str', body: 'dict', filename: 'str', chunk: 'bytes', chunk_number: 'int', chunk_size: 'int', total_chunks: 'int', total_size: 'int') -> 'None':
        if self._check_chunk(type, body, filename, chunk_number, chunk_size) == True:
            return

        return self.send("POST", type, body['id'] + '/chunk/', params={"filename": filename, "chunkNumber": chunk_number, "totalChunks": total_chunks, "totalSize": total_size}, files={"chunk": chunk})

    def send(self, method: 'str', type: 'str', path: 'str', body: 'dict' = None, params: 'dict' = None, files: 'dict' = None) -> 'dict | list[dict] | None':
        import os, requests, json
        import base.exceptions as exceptions
        
        try:
            r = requests.request(
                method, 
                os.environ['API_URL'] + '/telegram/' + type + '/' + path, 
                headers={'Accept': 'application/json'}, 
                json=body, 
                params=params, 
                files=files, 
                verify=False
            )
        except requests.exceptions.ConnectionError as ex:
            raise exceptions.RequestException(500, str(ex)) 

        try:
            r.raise_for_status()
        except requests.exceptions.RequestException as ex:
            r: 'requests.Response | None' = ex.response
            
            try:
                _json = r.json()
            except json.decoder.JSONDecodeError as ex:
                content = r.text
            else:
                content = _json["message"]
                
            if r.status_code == 409:
                raise exceptions.UniqueConstraintViolationError(content)
            else:
                raise exceptions.RequestException(r.status_code, content)
        
        if r.status_code == 204:
            return None

        return r.json()


LINK_RE = re.compile(
    r'(?:@|(?:https?:\/\/)?(?:www\.)?(?:telegram\.(?:me|dog)|t\.me)\/(?:@|joinchat\/|\+)?|'
    r'tg:\/\/(?:join|resolve)\?(?:invite=|domain=))'
    r'(?:[a-zA-Z0-9_.-](?:(?!__)\w){3,30}[a-zA-Z0-9_.-]|'
    r'gif|vid|pic|bing|wiki|imdb|bold|vote|like|coub)',
    re.IGNORECASE
)

HTTP_RE = re.compile(r'^(?:@|(?:https?://)?(?:www\.)?(?:telegram\.(?:me|dog)|t\.me))/(\+|joinchat/)?')

TG_RE = re.compile(r'^tg://(?:(join)|resolve)\?(?:invite|domain)=')


def parse_username(link: 'str') -> 'tuple[str | None, str | None]':
    link = link.strip()

    m = re.match(HTTP_RE, link) or re.match(TG_RE, link)

    if m:
        link = link[m.end():]
        is_invite = bool(m.group(1))

        if is_invite:
            return link, True
        else:
            link = link.rstrip('/')

    if telethon.utils.VALID_USERNAME_RE.match(link):
        return link.lower(), False
    else:
        return None, False