# Celery Telegram Parser

## Установка

```
sudo su
apt install redis
adduser --disabled-login --no-create-home celery
mkdir -p /opt/celery && cd /opt/celery
```
```
git clone git@gitlab.com:msr-system/telegram-parser.git && cd telegram-parser
```
```
python3 -m venv /opt/celery/telegram-parser/venv
source /opt/celery/telegram-parser/venv/bin/activate
```
```
pip install -r requirements.txt
```
Копируем шаблон переменных окружения и редактируем по необходимости.
```
mkdir /etc/conf.d
ln -s conf.d/prod/celery /etc/conf.d/celery
```
```
ln -s systemd/prod/celery.service /etc/systemd/system/
```
```
mkdir -p /var/log/celery/ && chown -R celery:celery /var/log/celery/
mkdir -p /var/run/celery/ && chown -R celery:celery /var/run/celery/
```
```
systemctl daemon-reload
systemctl enable celery.service
```
Если нужна веб морда для celery создаем ссылку на юнит
```
ln -s systemd/prod/flower.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable flower.service
```

## Запуск

```
systemctl start celery.service
```

Веб морда
```
systemctl start flower.service
```
