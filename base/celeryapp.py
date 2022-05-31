from __future__ import absolute_import
from celery import Celery


app = Celery(
    'base',
    broker='redis://localhost:6379/1',
    include=['base.tasks'],
    backend='db+postgresql+psycopg2://postgres:123@localhost/dev_tg_parser4',
    namespace='CELERY',
    # database_table_names={
    #     'task': 'django_celery_results_taskresult',
    #     'group': 'django_celery_results_groupresult',
    # },

)


if __name__ == '__main__':
    app.start()


