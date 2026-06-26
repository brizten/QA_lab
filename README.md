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

# Get a report with the test case, module, steps, result and error_message
curl.exe http://localhost:8000/api/test-runs/<run_id>/report `
  -H "Authorization: Bearer <access_token>"
```

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
