import signal
import logging
import os
import asyncio
import json
import sys
import celery
from enum import Enum, auto
import psycopg2
import psycopg2.extensions


class Action(Enum):
    insert = auto()
    update = auto()
    delete = auto()


class Table(Enum):
    chats = auto()
    phones = auto()
    chats_tasks = auto()


class TaskStatus(Enum):
    created = 0
    started = 1
    success = 2
    failure = 3
    revoked = 4


class TaskType(Enum):
    task_member = 0
    task_message = 1
    task_monitoring = 2
    task_chat_media = 3


class PGNotify:
    class Payload:
        def __init__(self, table, action, schema, record, data):
            self.table = Table[table]
            self.action = Action[action]
            self.schema = schema
            self.record = record
            self.data = data

    def __init__(self) -> None:
        self.logger = self._init_logger()

        self.logger.info('Initialization PGNotify service instance')

        self.loop = asyncio.new_event_loop()
        self.loop.set_exception_handler(self._ex_handler)

        signal.signal(signal.SIGTERM, self._handle_sig)
        signal.signal(signal.SIGINT, self._handle_sig)

        self._init_django()

        self.connection = self._init_db_connection()
        self.app = self._init_celery_app()

        self.logger.info('PGNotify instance created')

    def _init_logger(self):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.INFO)
        stdout_handler.setFormatter(formatter)

        logger.addHandler(stdout_handler)

        return logger

    def _handle_sig(self, sig, frame):
        self.logger.warning(f'{signal.Signals(sig).name} received...')

        self.stop()

    def _init_django(self):
        import django

        self.logger.info('Django setup...')

        os.environ["DJANGO_SETTINGS_MODULE"] = "project.settings"
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

        django.setup()

        from base import models

        self.models = models

    def _init_db_connection(self):
        from django.db import connection

        self.logger.info('Listen postgresql notifies initialization...')

        crs = connection.cursor()
        pg_con = connection.connection
        pg_con.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        crs.execute("LISTEN entity_event;")

        return pg_con

    def _init_celery_app(self):
        self.logger.info('Celery initialization...')

        app = celery.Celery('project')
        app.config_from_object('django.conf:settings', namespace='CELERY')
        app.autodiscover_tasks()

        return app

    def _handle(self):
        self.connection.poll()

        while self.connection.notifies:
            notify = self.connection.notifies.pop(0)

            payload = PGNotify.Payload(**json.loads(notify.payload))

            self.logger.info(f'Handle new pg notification {notify.payload}')

            if payload.table == Table.chats:
                if payload.action == Action.insert:
                    self.logger.debug('Sending ChatResolveTask...')

                    try:
                        chat = self.models.Chat.objects.get(id=payload.record['id'])
                    except self.models.Chat.DoesNotExist:
                        self.logger.warning(f'Chat ({payload.record["id"]}) is not found...')

                        continue

                    self.app.send_task(
                        "ChatResolveTask",
                        (chat.id,),
                        time_limit=60,
                        task_id=payload.record['id'],
                        queue='high_prio'
                    )

                elif payload.action == Action.delete:
                    self.app.control.revoke(payload.record['id'], terminate=True)

            elif payload.table == Table.phones:
                if payload.action == Action.insert:

                    try:
                        phone = self.models.Phone.objects.get(id=payload.record['id'])
                    except self.models.Phone.DoesNotExist:
                        self.logger.warning(f'Phone ({payload.record["id"]}) is not found...')

                        continue

                    self.logger.debug('Sending PhoneAuthorizationTask...')

                    self.app.send_task(
                        "PhoneAuthorizationTask",
                        (phone.id,),
                        time_limit=600,
                        task_id=payload.record['id'],
                        queue="high_prio"
                    )

                elif payload.action == Action.delete:
                    self.app.control.revoke(payload.record['id'], terminate=True)

            elif payload.table == Table.chats_tasks:
                if payload.action == Action.insert:
                    try:
                        chat = self.models.Chat.objects.get(id=payload.record['chat_id'])
                    except self.models.Chat.DoesNotExist:
                        self.logger.warning(f'Chat ({payload.record["chat_id"]}) is not found...')

                        continue

                    sig = None

                    if TaskType(payload.record['type']) == TaskType.task_member:
                        self.logger.debug('Creating ParseMembersTask signature...')

                        sig = celery.signature(
                            "ParseMembersTask",
                            (chat.id,),
                            queue="low_prio",
                            task_id=payload.record['id'],
                            immutable=True
                        )

                    elif TaskType(payload.record['type']) == TaskType.task_message:
                        self.logger.debug('Creating ParseMessagesTask signature...')

                        sig = celery.signature(
                            "ParseMessagesTask",
                            (chat.id,),
                            queue="low_prio",
                            task_id=payload.record['id'],
                            immutable=True
                        )

                    elif TaskType(payload.record['type']) == TaskType.task_monitoring:
                        self.logger.debug('Creating MonitoringChatTask signature...')

                        sig = celery.signature(
                            "MonitoringChatTask",
                            (chat.id,),
                            queue="high_prio",
                            task_id=payload.record['id'],
                            immutable=True
                        )

                    elif TaskType(payload.record['type']) == TaskType.task_chat_media:
                        self.logger.debug('Creating ChatMediaTask signature...')

                        sig = celery.signature(
                            "ChatMediaTask",
                            (chat.id,),
                            queue="high_prio",
                            task_id=payload.record['id'],
                            immutable=True
                        )

                    phones = chat.get_chat_phones()

                    self.logger.debug(f'Phones len {len(phones)}')

                    if phones:
                        self.logger.debug('Sending celery chord')

                        celery.chord([
                            celery.signature(
                                'JoinChatTask',
                                args=(chat.id, phone.id),
                                queue='high_prio',
                                immutable=True,
                                time_limit=60
                            ) for phone in phones
                        ])(sig)
                    else:
                        self.logger.debug('Sending celery standalone task')

                        sig.delay()

                elif payload.action == Action.update:
                    if TaskStatus(payload.record['status']) == TaskStatus.revoked:
                        self.app.control.revoke(payload.record['id'], terminate=True)

                elif payload.action == Action.delete:
                    self.app.control.revoke(payload.record['id'], terminate=True)

    def _ex_handler(self, loop, context):
        loop.default_exception_handler(context)

        self.stop(1)

    def start(self):
        self.logger.info('Starting PGNotify service')

        self.loop.add_reader(self.connection, self._handle)

        self.loop.run_forever()

    def stop(self, code: 'int' = 0):
        self.logger.info(f'Stopping PGNotify service with code {code}.')
        self.logger.info('Cleaning up...')

        self.loop.stop()

        sys.exit(code)


if __name__ == '__main__':
    service = PGNotify()
    service.start()
