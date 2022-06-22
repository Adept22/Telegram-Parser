# Celery Telegram Parser

## Установка

```
sudo api install redis
sudo adduser --disabled-login --no-create-home celery
mkdir -p /opt/celery && cd /opt/celery
```
```
git clone git@gitlab.com:msr-system/telegram-parser.git
```
```
python3 -m venv /opt/celery/telegram-parser/venv
source /opt/celery/telegram-parser/venv/bin/activate
```
```
cd telegram-parser
pip install -r requirements.txt
```

```
sudo mkdir /etc/conf.d
sudo cp conf.d/celery /etc/conf.d/
sudo cp systemd/celery.service /etc/systemd/system/
```

```
sudo systemctl daemon-reload
sudo systemctl enable celery.service
```

## Запуск

```
sudo systemctl start celery.service
```