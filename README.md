# Autotest Platform

Локальное окружение проекта поднимается через Docker Compose и включает PostgreSQL 16, Redis 7 и pgAdmin 4.

## Final Quick Start

Ниже самый короткий путь для локального запуска backend и frontend с Docker-инфраструктурой:

```powershell
# 1. Start infrastructure
docker compose up -d postgres redis pgadmin

# 2. Open backend
cd backend

# 3. Create virtual environment
python -m venv .venv

# 4. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 5. Install backend dependencies
pip install -r requirements.txt

# 6. Apply migrations
alembic upgrade head

# 7. Seed demo data
python -m scripts.seed_demo_data

# 8. Start FastAPI
uvicorn app.main:app --reload
```

Если на Windows уже запущен локальный PostgreSQL и он занимает `localhost:5432`, локальный backend может подключиться не к Docker PostgreSQL, а к этому локальному сервису. В таком случае остановите локальный PostgreSQL на время разработки или запускайте backend через Docker Compose.

В отдельном терминале запустите Celery worker:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1

# 9. Start Celery worker
celery -A app.workers.celery_app worker --loglevel=info
```

В третьем терминале запустите frontend:

```powershell
# 10. Open frontend
cd frontend

# 11. Install frontend dependencies
npm install

# 12. Start Vite
npm run dev
```

### Test users

Seed script создаёт demo admin:

```text
Email: admin@local.com
Password: admin
Role: ADMIN
```

Новые пользователи, созданные через `POST /api/auth/register`, получают роль `QA` по умолчанию.

### URLs

- Swagger URL: `http://localhost:8000/docs`
- Backend health: `http://localhost:8000/health`
- pgAdmin URL: `http://localhost:5050`
- Frontend URL: `http://localhost:5173`

### Example test run request

```powershell
$login = curl.exe -s -X POST http://localhost:8000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"admin@local.com","password":"admin"}' | ConvertFrom-Json

curl.exe -X POST http://localhost:8000/api/test-runs `
  -H "Authorization: Bearer $($login.access_token)" `
  -H "Content-Type: application/json" `
  -d '{"test_case_code":"cards.issue_virtual_card","environment":"test","parameters":{"iin":"990101300000","product_code":"VIRTUAL_CARD","currency":"KZT"}}'
```

## Docker Compose

### Запуск только инфраструктуры

Для локальной backend-разработки можно поднять только PostgreSQL, Redis и pgAdmin:

```bash
docker compose up -d postgres redis pgadmin
```

Проверьте, что сервисы запущены:

```bash
docker ps
```

### Запуск всего проекта через Docker Compose

Команда ниже поднимает PostgreSQL, Redis, pgAdmin, FastAPI backend, Celery worker и Vite frontend:

```bash
docker compose up -d --build
```

Если хотите явно отделить docker-переменные от локального `.env`, создайте файл из примера:

```powershell
Copy-Item .env.docker.example .env.docker
docker compose --env-file .env.docker up -d --build
```

Внутри Docker Compose backend и worker всегда подключаются к PostgreSQL по host `postgres`, а к Redis по host `redis`. Поэтому локальный `.env` с `POSTGRES_HOST=localhost` не ломает docker setup.

После первого запуска нового окружения примените миграции и при необходимости создайте demo-данные:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python -m scripts.seed_demo_data
```

Локальные URL:

- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- pgAdmin: `http://localhost:5050`

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

### Запуск backend локально с Docker DB

Поднимите Docker-инфраструктуру:

```powershell
docker compose up -d postgres redis pgadmin
```

Затем создайте виртуальное окружение и установите зависимости:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Для локального backend `.env` должен использовать host `localhost`:

```text
POSTGRES_HOST=localhost
REDIS_HOST=localhost
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

### Backend tests

Тесты находятся в `backend/tests/` и используют отдельную in-memory SQLite базу, поэтому основную PostgreSQL БД они не меняют.

Из директории `backend/`:

```powershell
pip install -r requirements-test.txt
pytest
```

### Запуск Celery worker

В отдельном терминале из директории `backend/`:

```powershell
celery -A app.workers.celery_app worker --loglevel=info
```

### Runner contract

Автотесты подключаются через runner-классы в `backend/app/runner/`, а не через отдельные endpoint-ы. Один endpoint `POST /api/test-runs` запускает любой test case по `code`: Celery берёт `TestCase.code` из PostgreSQL, ищет такой же код в registry и вызывает `test.run(context)`.

Минимальный контракт:

- `BaseTestCase`: `code`, `name`, `module`, `input_schema`, метод `run(context)`.
- `TestContext`: `test_run_id`, `params`, `environment`, `db` session и `step(name)` context manager.
- `context.step(...)`: создаёт `TestRunStep`, сохраняет status, `request_json`, `response_json`, `error_message` и duration.
- `registry`: регистрирует test classes и отдаёт runner по `get_test_by_code(code)`.

Встроенные примеры:

- `cards.issue_virtual_card` — шаги создания клиента и выпуска виртуальной карты.
- `k2.create_payment` — шаги создания платежа и проверки статуса.

Чтобы добавить новый автотест, создайте класс-наследник `BaseTestCase`, реализуйте `run(context)` через `with context.step("Step name") as step:`, зарегистрируйте класс в `backend/app/runner/registry.py` и создайте `TestCase` в БД с таким же `code`.

### Создание локального администратора

Из директории `backend/` создайте локального администратора командой:

```powershell
python -m scripts.create_admin
```

Скрипт создаёт `admin@local.com` с паролем `admin` и ролью `ADMIN`. При повторном запуске существующий пользователь не изменяется и не дублируется.

### Создание demo-данных

Из директории `backend/` можно создать локальные demo-данные:

```powershell
python -m scripts.seed_demo_data
```

Скрипт создаёт admin user `admin@local.com` / `admin`, если его ещё нет; если admin уже существует, он приводится к активной роли `ADMIN` с demo-паролем `admin`. Также создаются modules `cards` и `k2`, а также активные test cases `cards.issue_virtual_card` и `k2.create_payment`. Повторный запуск не создаёт дубли и обновляет demo modules/test cases до ожидаемых значений.

После seed можно проверить основной flow:

```powershell
# Login as admin
curl.exe -X POST http://localhost:8000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"admin@local.com","password":"admin"}'

# List modules
curl.exe http://localhost:8000/api/modules `
  -H "Authorization: Bearer <access_token>"

# List seeded test cases
curl.exe http://localhost:8000/api/test-cases `
  -H "Authorization: Bearer <access_token>"

# Queue seeded cards runner
curl.exe -X POST http://localhost:8000/api/test-runs `
  -H "Authorization: Bearer <access_token>" `
  -H "Content-Type: application/json" `
  -d '{"test_case_code":"cards.issue_virtual_card","environment":"test","parameters":{"iin":"990101300000","product_code":"VIRTUAL_CARD","currency":"KZT"}}'

# Open report
curl.exe http://localhost:8000/api/test-runs/<run_id>/report `
  -H "Authorization: Bearer <access_token>"
```

## Frontend

Frontend находится в директории `frontend/` и использует React, Vite, TypeScript, React Router и Axios. Перед запуском убедитесь, что backend доступен на `http://localhost:8000`.

```powershell
cd frontend
npm install
npm run dev
```

Локальный URL по умолчанию: `http://127.0.0.1:5173`. API base URL задаётся в `frontend/.env`:

```powershell
Copy-Item .env.example .env
```

## Аутентификация API

API доступно по префиксу `/api`. Пароли сохраняются только в виде bcrypt-хеша, а для авторизации используется JWT access token.

### Роли и доступ

- `ADMIN` — полный доступ ко всем API и данным.
- `AUTOTESTER` — создание модулей и test cases, запуск тестов и просмотр всех отчётов.
- `QA` — просмотр test cases, запуск активных test cases и просмотр отчётов.
- `BUSINESS` — просмотр test cases, запуск только активных test cases с тегом `business`, а также просмотр только собственных отчётов.
- `VIEWER` — только просмотр test cases и отчётов.

Просмотр modules, test cases и отчётов доступен всем ролям. Создание, редактирование и удаление modules, а также создание test cases доступны `ADMIN` и `AUTOTESTER`; запуск test runs — `ADMIN`, `AUTOTESTER`, `QA` и `BUSINESS`. При недостатке прав API возвращает `403 Forbidden`.

### Modules API

Во всех запросах ниже замените `<access_token>` на JWT, а `<module_id>` на идентификатор модуля.

```powershell
# List
curl.exe http://localhost:8000/api/modules `
  -H "Authorization: Bearer <access_token>"

# Create (ADMIN or AUTOTESTER)
curl.exe -X POST http://localhost:8000/api/modules `
  -H "Authorization: Bearer <access_token>" `
  -H "Content-Type: application/json" `
  -d '{"code":"PAYMENTS","name":"Payments","description":"Payment test cases"}'

# Get one
curl.exe http://localhost:8000/api/modules/<module_id> `
  -H "Authorization: Bearer <access_token>"

# Update (ADMIN or AUTOTESTER)
curl.exe -X PUT http://localhost:8000/api/modules/<module_id> `
  -H "Authorization: Bearer <access_token>" `
  -H "Content-Type: application/json" `
  -d '{"name":"Payment services"}'

# Delete (ADMIN or AUTOTESTER)
curl.exe -X DELETE http://localhost:8000/api/modules/<module_id> `
  -H "Authorization: Bearer <access_token>"
```

Поле `code` уникально. Удаление модуля, к которому привязаны test cases, возвращает `400`.

### Test Cases API

Во всех запросах ниже замените `<access_token>`, `<module_id>` и `<test_case_id>` на актуальные значения.

```powershell
# List with optional filters: module_id, tag, is_active
curl.exe "http://localhost:8000/api/test-cases?module_id=<module_id>&tag=business&is_active=true" `
  -H "Authorization: Bearer <access_token>"

# Create (ADMIN or AUTOTESTER); owner_id is optional
curl.exe -X POST http://localhost:8000/api/test-cases `
  -H "Authorization: Bearer <access_token>" `
  -H "Content-Type: application/json" `
  -d '{"code":"PAYMENT-REFUND","name":"Payment refund","module_id":<module_id>,"input_schema":{"order_id":"string"},"tags":["business","payments"],"is_active":true}'

# Get one
curl.exe http://localhost:8000/api/test-cases/<test_case_id> `
  -H "Authorization: Bearer <access_token>"

# Update (ADMIN or AUTOTESTER)
curl.exe -X PUT http://localhost:8000/api/test-cases/<test_case_id> `
  -H "Authorization: Bearer <access_token>" `
  -H "Content-Type: application/json" `
  -d '{"tags":["business","smoke"],"is_active":false}'

# Delete (ADMIN or AUTOTESTER)
curl.exe -X DELETE http://localhost:8000/api/test-cases/<test_case_id> `
  -H "Authorization: Bearer <access_token>"
```

`input_schema` принимает только JSON object, а `tags` — JSON array of strings. Удаление test case с существующими test runs возвращает `400`.

### Test Runs API

Запуск сохраняет test run в статусе `QUEUED` и отправляет Celery task `run_test_case(test_run_id)` в Redis. Worker переводит run в `RUNNING`, находит runner-класс по `TestCase.code`, запускает `test.run(context)` и завершает run со статусом `PASSED`, `FAILED` или `BROKEN`. `input_schema` test case поддерживает два базовых формата: JSON Schema-like (`properties` + `required`) и объект правил полей, например `{"iin":{"type":"string","required":true}}`.

```powershell
# Queue a run (ADMIN, AUTOTESTER, QA, or BUSINESS)
curl.exe -X POST http://localhost:8000/api/test-runs `
  -H "Authorization: Bearer <access_token>" `
  -H "Content-Type: application/json" `
  -d '{"test_case_code":"cards.issue_virtual_card","environment":"test","parameters":{"iin":"990101300000","product_code":"VIRTUAL_CARD","currency":"KZT"}}'

# Queue a forced failed mock run
curl.exe -X POST http://localhost:8000/api/test-runs `
  -H "Authorization: Bearer <access_token>" `
  -H "Content-Type: application/json" `
  -d '{"test_case_code":"cards.issue_virtual_card","environment":"test","parameters":{"iin":"990101300000","product_code":"VIRTUAL_CARD","currency":"KZT","force_fail":true}}'

# List reports
curl.exe http://localhost:8000/api/test-runs `
  -H "Authorization: Bearer <access_token>"

# Get a run
curl.exe http://localhost:8000/api/test-runs/<run_id> `
  -H "Authorization: Bearer <access_token>"

# Get a report with run, test_case, module, started_by and sorted steps
curl.exe http://localhost:8000/api/test-runs/<run_id>/report `
  -H "Authorization: Bearer <access_token>"
```

Report endpoint возвращает компактную структуру:

```json
{
  "run": {
    "id": 1,
    "status": "PASSED",
    "environment": "test",
    "parameters": {},
    "result": {},
    "error_message": null,
    "started_at": "2026-06-27T10:00:00Z",
    "finished_at": "2026-06-27T10:00:01Z",
    "duration_ms": 1000
  },
  "test_case": {
    "id": 1,
    "code": "cards.issue_virtual_card",
    "name": "Issue virtual card",
    "tags": ["smoke", "business", "cards"]
  },
  "module": {
    "id": 1,
    "code": "cards",
    "name": "Cards"
  },
  "started_by": {
    "id": 1,
    "email": "admin@local.com",
    "full_name": "Local Admin"
  },
  "steps": [
    {
      "id": 1,
      "name": "Validate input parameters",
      "status": "PASSED",
      "duration_ms": 100,
      "error_message": null,
      "request_json": null,
      "response_json": null
    }
  ]
}
```

Steps в report отсортированы по `id`. `ADMIN`, `AUTOTESTER`, `QA` и `VIEWER` могут смотреть все reports; `BUSINESS` может смотреть только свои test runs.

Проверяются обязательные параметры и типы `string`, `number`, `boolean`. Если runner-класс не найден по `TestCase.code`, run завершается как `BROKEN` с понятным `error_message`. Если тест бросает `AssertionError`, run завершается как `FAILED`; если возникает неожиданная ошибка — как `BROKEN`. В example tests параметр `"force_fail": true` специально бросает `AssertionError` и завершает run со статусом `FAILED`. `BUSINESS` может запускать только активные test cases с тегом `business`; `ADMIN`, `AUTOTESTER` и `QA` — активные test cases согласно своим RBAC-правам.

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
