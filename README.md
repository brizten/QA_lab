# Autotest Platform

Локальное окружение проекта поднимается через Docker Compose и включает PostgreSQL 16, Redis 7 и pgAdmin 4.

## Запуск Docker Compose

При необходимости создайте локальный `.env` из примера:

```bash
cp .env.example .env
```

Запустите контейнеры:

```bash
docker compose up -d
```

Проверьте, что сервисы запущены:

```bash
docker ps
```

## pgAdmin

Откройте pgAdmin в браузере:

```text
http://localhost:5050
```

Данные для входа:

```text
Email: admin@local.com
Password: admin
```

## Подключение PostgreSQL в pgAdmin

1. В pgAdmin нажмите **Add New Server**.
2. На вкладке **General** задайте имя, например `Autotest PostgreSQL`.
3. На вкладке **Connection** укажите:

```text
Host name/address: postgres
Port: 5432
Maintenance database: autotest_platform
Username: autotest_user
Password: autotest_password
```

Внутри pgAdmin в поле `Host name/address` нужно указывать `postgres`, а не `localhost`. Контейнер pgAdmin подключается к PostgreSQL по имени сервиса Docker Compose во внутренней сети. `localhost` внутри pgAdmin будет означать сам контейнер pgAdmin, а не контейнер PostgreSQL.
