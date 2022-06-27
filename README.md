# Celery Telegram Parser

## Установка

```
sudo su
apt install redis
```
```
adduser --disabled-login --no-create-home celery
mkdir -p /opt/celery && cd /opt/celery
```
```
git clone git@gitlab.com:msr-system/telegram-parser.git && cd telegram-parser
```
```
python3 -m venv /opt/celery/telegram-parser/venv
source ./venv/bin/activate
```
```
pip install -r requirements.txt
```
Копируем шаблон переменных окружения и редактируем по необходимости.
```
cp /opt/celery/telegram-parser/conf.d/celery /opt/celery/telegram-parser/conf.d/celery.local
mkdir -p /etc/conf.d && ln -s /opt/celery/telegram-parser/conf.d/celery.local /etc/conf.d/celery
```
```
ln -s /opt/celery/telegram-parser/systemd/celery.service /etc/systemd/system/
```
```
mkdir -p /var/log/celery/ && chown -R celery:celery /var/log/celery/
mkdir -p /var/run/celery/ && chown -R celery:celery /var/run/celery/
```
```
systemctl daemon-reload
systemctl enable celery.service
```
Если нужна веб-морда для celery создаем ссылку на юнит
```
ln -s /opt/celery/telegram-parser/systemd/flower.service /etc/systemd/system/
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
