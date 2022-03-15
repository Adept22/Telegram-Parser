# Микросервис парсинга Telegram

## Построение образа

```
docker build \
    --rm \
    --no-cache \
    --pull \
    --tag=telegram-parser:latest \
    .
```

## Запуск

Создаем в API сущность Host, если нужная отсутствует, далее создаем сущность Parser с указанием хоста.

Копируем сгенерированый UUID и подставляем вместо `{PARSER_UUID}`.

```
docker run -d \
    --name=`{PARSER_UUID}` \
    --restart=unless-stopped \
    --add-host=host.docker.internal:host-gateway \
    --env PARSER_ID=`{PARSER_UUID}` \
    --env API_URL=http://host.docker.internal:47352/api/v1 \
    telegram-parser
```