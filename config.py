from os import path

BASE_DIR = path.dirname(path.abspath(__file__))

API = {
    'protocol': 'http',
    'domain': 'caddy',
    'path': 'api/v1/telegram'
}

API_ID = '8347922'
API_HASH = '766533a46e9e7915f6b91a2de8392ae2'
USERNAME = 'ParseUser'

CHANNELS_LIST_JSON_FILENAME = 'channels.json'
TAGS_LIST_JSON_FILENAME = 'tags.json'

HISTORY_PARSE_DEPTH = 100000000000

USER_FIELDS = {
    'id': 'ID',
    'username': 'Логин',
    'first_name': 'Имя',
    'last_name': 'Фамилия',
    'has_photo': 'Есть фотографии',
    'channel': 'Канал',
}
USERS_XLSX_FILENAME = 'users.xlsx'
USERS_JSON_FILENAME = 'users.json'


MESSAGE_FIELDS = {
    'id': 'ID',
    'date': 'Дата',
    'channel': 'Канал',
    'message': 'Сообщение',
    'tag': 'Ключевое слово',
    'user.id': 'Id автора',
    'user.username': 'Логин автора',
    'user.first_name': 'Имя автора',
    'user.last_name': 'Фамилия автора',
    'user.has_photo': 'Есть фото автора',
    'link': 'Ссылка на сообщение',
}
MESSAGES_XLSX_FILENAME = 'messages.xlsx'
MESSAGES_JSON_FILENAME = 'messages.json'
