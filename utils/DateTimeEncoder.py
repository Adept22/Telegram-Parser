import json
from datetime import datetime


class DateTimeEncoder(json.JSONEncoder):
    def default(self, item):
        if isinstance(item, datetime):
            return item.isoformat()
        if isinstance(item, bytes):
            return list(item)
        return json.JSONEncoder.default(self, item)
