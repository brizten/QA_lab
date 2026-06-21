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

## Backend

Backend находится в директории `backend/` и рассчитан на Python 3.12+.

### Подготовка окружения

Перед запуском должны быть доступны PostgreSQL и Redis из Docker Compose. Создайте виртуальное окружение и установите зависимости:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Примените существующие миграции:

```powershell
alembic upgrade head
```

После изменения SQLAlchemy-моделей создайте новую ревизию и примените её:

```powershell
alembic revision --autogenerate -m "describe schema change"
alembic upgrade head
```

### Запуск API

Из директории `backend/`:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Проверка доступности API: `http://localhost:8000/health`.

### Запуск Celery worker

В отдельном терминале из директории `backend/`:

```powershell
celery -A app.workers.celery_app.celery_app worker --loglevel=INFO --pool=solo
```

## Аутентификация API

API доступно по префиксу `/api`. Пароли сохраняются только в виде bcrypt-хеша, а для авторизации используется JWT access token.

### Регистрация пользователя

Новый пользователь получает роль `QA`.

```powershell
curl.exe -X POST http://localhost:8000/api/auth/register `
  -H "Content-Type: application/json" `
  -d '{"email":"qa@example.com","password":"strong_password","full_name":"QA User"}'
```

### Получение access token

```powershell
curl.exe -X POST http://localhost:8000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"qa@example.com","password":"strong_password"}'
```

Ответ содержит `access_token` и `token_type` со значением `bearer`.

### Текущий пользователь

Передайте токен из ответа login в заголовке `Authorization`:

```powershell
curl.exe http://localhost:8000/api/users/me `
  -H "Authorization: Bearer <access_token>"
```
