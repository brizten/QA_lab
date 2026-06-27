# Autotest Platform User Guide

Этот документ объясняет, как пользоваться Autotest Platform после того, как проект уже запущен. Техническая установка, Docker Compose, миграции и команды запуска описаны в `README.md`; здесь фокус на ролях, тест-кейсах, запусках, отчетах и правилах работы с платформой.

## 1. Overview

Autotest Platform - это сервис для запуска автотестов по запросу. Платформа позволяет autotesters регистрировать test cases, а manual QA, developers и business users запускать готовые сценарии через Web UI или API с нужными параметрами.

Проблема, которую решает платформа:

- тесты не нужно запускать вручную из IDE или с локальной машины autotester-а;
- manual QA и business users могут запускать разрешенные сценарии сами;
- результаты сохраняются в PostgreSQL и доступны через report endpoint;
- запуск идет асинхронно, поэтому API быстро возвращает `run_id`, а выполнение делает Celery worker;
- один и тот же тест можно запускать в разных environments с разными parameters.

### Почему один endpoint для всех тестов

В платформе нет отдельного endpoint-а на каждый автотест. Вместо этого используется один endpoint:

```text
POST /api/test-runs
```

Пользователь передает `test_case_code`, например `cards.issue_virtual_card`, а worker сам находит соответствующий runner class в registry.

Такой подход лучше, потому что:

- API остается стабильным, даже если autotesters добавляют новые тесты;
- не нужно создавать новый route для каждого сценария;
- права, валидация параметров, логирование и отчеты работают одинаково для всех тестов;
- frontend может показывать список test cases из базы и запускать любой из них одним механизмом.

### Основной поток

```text
User -> Web UI/API -> TestRun QUEUED -> Celery Worker -> Runner -> Report
```

1. Пользователь выбирает test case.
2. Пользователь передает environment и parameters.
3. API создает `TestRun` со статусом `QUEUED`.
4. Celery worker забирает задачу из Redis.
5. Worker находит runner по `TestCase.code`.
6. Runner выполняет steps и сохраняет request/response/error details.
7. Report endpoint возвращает итоговый статус, результат и список steps.

## 2. Main Concepts

| Concept | Что это значит |
| --- | --- |
| Module | Группа test cases по домену или системе: `cards`, `k2`, `crm`, `aml`. |
| Test Case | Описание тестового сценария в базе: code, name, module, input_schema, tags, active flag. |
| Test Run | Один конкретный запуск test case с environment, parameters, статусом и результатом. |
| Test Run Step | Один шаг внутри запуска: name, status, duration, request_json, response_json, error_message. |
| Runner | Python-класс, который реально выполняет автотест. |
| Input Schema | JSON-описание ожидаемых параметров запуска и их типов. |
| Tags | Метки для фильтрации и правил доступа: `smoke`, `business`, `critical`. |
| Environment | Среда запуска: `dev`, `test`, `stage`, `preprod`. |
| Report | Структурированный отчет по запуску: run, test_case, module, started_by, steps, result. |

### Module

Module помогает сгруппировать тесты по продукту, системе или бизнес-домену. Например:

- `cards` - карточные сценарии;
- `k2` - платежные сценарии;
- `crm` - клиентские данные;
- `aml` - проверки AML;
- `nbportal` - портал;
- `iso20022` - платежные сообщения.

### Test Case

Test Case - это metadata. Он не содержит весь код автотеста, но описывает, какой сценарий существует и как его можно запускать.

Главные поля:

- `code` - стабильный идентификатор, например `cards.issue_virtual_card`;
- `name` - понятное имя;
- `module_id` - связь с module;
- `input_schema` - какие parameters нужны;
- `tags` - для фильтрации и RBAC;
- `is_active` - можно ли запускать test case.

### Runner

Runner - это Python-класс в `backend/app/runner/tests/`. Его `code` должен совпадать с `TestCase.code` в базе. Если в базе есть test case, но runner не зарегистрирован, запуск завершится как `BROKEN`.

## 3. Roles And Permissions

| Role | Может | Не может | Основные экраны/API |
| --- | --- | --- | --- |
| ADMIN | Все операции | Нет ограничений в MVP | Все экраны и endpoints |
| AUTOTESTER | Создавать modules/test cases, запускать тесты, смотреть отчеты | Управлять пользователями пока вне MVP | Modules, Test Cases, Run Test, Test Runs, Reports |
| QA | Запускать активные test cases, смотреть test cases и reports | Создавать/редактировать modules и test cases | Test Cases, Run Test, Test Runs, Reports |
| BUSINESS | Запускать только test cases с tag `business`, смотреть свои reports | Запускать technical-only tests, смотреть чужие runs | Test Cases, Run Test, свои Reports |
| VIEWER | Смотреть test cases и reports | Запускать тесты и менять metadata | Test Cases, Test Runs, Reports |

### ADMIN

ADMIN нужен для локальной настройки, seed data, проверки прав и поддержки платформы.

Может:

- создавать, редактировать и удалять modules;
- создавать, редактировать и удалять test cases;
- запускать любые активные test cases;
- смотреть все reports;
- проверять поведение других ролей.

Ограничения:

- в MVP нет отдельного UI для управления пользователями;
- первый admin создается seed script-ом.

### AUTOTESTER

AUTOTESTER отвечает за качество test metadata и runner-кодов.

Может:

- создавать module;
- создавать test case;
- писать runner-класс;
- задавать `input_schema`;
- задавать tags;
- запускать tests для проверки;
- смотреть reports.

Не должен:

- менять metadata чужого домена без согласования;
- создавать test cases без runner-а;
- добавлять tag `business`, если сценарий не готов для business users.

### QA

QA использует платформу для ручной проверки через готовые автотесты.

Может:

- смотреть список test cases;
- фильтровать по module/tag/is_active;
- запускать активные test cases;
- смотреть reports.

Не может:

- создавать или редактировать modules;
- создавать или редактировать test cases;
- удалять metadata.

### BUSINESS

BUSINESS user запускает только готовые бизнес-сценарии.

Может:

- видеть test cases;
- запускать активные test cases с tag `business`;
- смотреть только свои test runs и reports.

Не может:

- запускать technical-only test cases без tag `business`;
- смотреть чужие reports;
- создавать или редактировать modules/test cases;
- видеть технические детали, если UI в будущем будет их скрывать.

### VIEWER

VIEWER нужен для read-only доступа.

Может:

- смотреть modules;
- смотреть test cases;
- смотреть reports.

Не может:

- запускать tests;
- создавать или редактировать metadata;
- удалять modules/test cases.

## 4. How Test Cases Are Grouped

Test cases группируются по modules. Module должен отражать понятную область продукта или интеграции.

Примеры modules:

| Module | Пример назначения |
| --- | --- |
| `cards` | Выпуск, блокировка, статус карт |
| `k2` | Платежи и платежные статусы |
| `crm` | Данные клиента |
| `aml` | AML проверки |
| `nbportal` | Сценарии портала |
| `iso20022` | ISO20022 сообщения |

### Naming Convention

Рекомендуемый формат:

```text
module.action_expected_result
```

Хорошие примеры:

- `cards.issue_virtual_card`
- `cards.block_card`
- `k2.create_payment`
- `aml.archive_client`
- `crm.update_client_phone`

Плохие примеры:

- `test1`
- `check`
- `cards_test`
- `my_new_test`

Почему плохие:

- не видно module;
- непонятно, что проверяется;
- сложно искать и поддерживать;
- неудобно строить отчеты и фильтры.

## 5. Tags Convention

Tags нужны для фильтрации, запуска групп тестов и правил доступа.

Примеры tags:

- `smoke`
- `regression`
- `business`
- `critical`
- `api`
- `db`
- `kafka`
- `nightly`
- `manual-trigger`
- `release-check`

| Tag | Когда использовать |
| --- | --- |
| `smoke` | Быстрая проверка ключевого сценария. |
| `regression` | Полный регрессионный набор. |
| `business` | Сценарий можно запускать business users. |
| `critical` | Важный бизнес-сценарий или высокорисковая проверка. |
| `api` | Тест проверяет API. |
| `db` | Тест читает или проверяет данные в БД. |
| `kafka` | Тест связан с Kafka/messages. |
| `nightly` | Тест подходит для ночного запуска. |
| `manual-trigger` | Тест лучше запускать вручную по необходимости. |
| `release-check` | Тест нужен перед release. |

Правила:

- business users могут запускать только test cases с tag `business`;
- `smoke` должен быть быстрым и надежным;
- `regression` может быть длиннее и шире;
- `critical` используйте только для действительно важных сценариев;
- tags должны быть lowercase и без пробелов.

## 6. Environments

Environment показывает, против какой среды выполняется тест.

| Environment | Назначение |
| --- | --- |
| `dev` | Разработка, нестабильная среда, быстрые проверки. |
| `test` | Основная тестовая среда QA. |
| `stage` | Предрелизная среда, ближе к production. |
| `preprod` | Максимально близко к production, требует осторожности. |

Environment влияет на:

- base URLs внешних сервисов;
- credentials;
- test data;
- integrations;
- допустимые операции;
- риск изменения данных.

Правила:

- не запускайте тесты против production случайно;
- для manual QA обычно подходит `test`;
- для проверки перед release может использоваться `stage`;
- `preprod` используйте только по согласованному процессу;
- dangerous tests должны иметь cleanup или работать на тестовых данных.

В текущем frontend select доступны `dev`, `test`, `stage`. Через API можно передать и другое значение, если backend и runner готовы его обработать.

## 7. How To Use The Platform As Manual QA

Manual QA использует платформу для запуска уже зарегистрированных сценариев.

Пошаговый сценарий:

1. Откройте frontend: `http://localhost:5173`.
2. Выполните login.
3. Откройте экран `Test Cases`.
4. Найдите test case по module, tag или активности.
5. Проверьте `code`, `name`, `tags` и `is_active`.
6. Откройте `Run Test`.
7. Выберите test case.
8. Выберите environment: обычно `test`.
9. Заполните `Parameters JSON`.
10. Нажмите `Queue Run`.
11. Откройте report по ссылке.
12. Проверьте общий status и steps.

### Parameters For cards.issue_virtual_card

```json
{
  "iin": "990101300000",
  "product_code": "VIRTUAL_CARD",
  "currency": "KZT"
}
```

### Parameters For k2.create_payment

```json
{
  "iin": "990101300000",
  "amount": 50000,
  "currency": "KZT"
}
```

### Как читать результат QA

- `PASSED` - сценарий прошел успешно.
- `FAILED` - бизнес-проверка не прошла, смотрите failed step и `error_message`.
- `BROKEN` - проблема в тесте, инфраструктуре, mock-е, registry или unexpected exception.
- `QUEUED` - запуск создан, но worker еще не начал выполнение.
- `RUNNING` - worker выполняет тест.

## 8. How To Use The Platform As Business User

Business user не пишет код и не настраивает metadata. Его задача - запускать готовые бизнес-сценарии и понимать результат.

Business test case должен иметь tag:

```text
business
```

Business user может:

- открыть список test cases;
- выбрать разрешенный business scenario;
- заполнить понятные business parameters;
- запустить тест;
- открыть свой report.

Business user не может:

- запускать technical-only tests;
- смотреть чужие test runs;
- менять modules/test cases;
- редактировать `input_schema`.

Пошагово:

1. Login.
2. Откройте `Test Cases`.
3. Найдите сценарии с tag `business`.
4. Выберите сценарий, например `cards.issue_virtual_card`.
5. Откройте `Run Test`.
6. Заполните allowed parameters.
7. Нажмите `Queue Run`.
8. Откройте report.
9. Посмотрите status.

Business-friendly interpretation:

- `PASSED` - бизнес-сценарий прошел.
- `FAILED` - бизнес-проверка не прошла.
- `BROKEN` - сломался автотест, инфраструктура или техническая интеграция.
- `TIMEOUT` - тест не завершился вовремя.

Если report показывает `BROKEN`, business user обычно не должен сам разбирать stack trace. Нужно передать `run_id` QA/autotester-у.

## 9. How To Use The Platform As Developer

Developer использует платформу для быстрой проверки своего модуля перед merge или release.

Developer может:

- найти module, связанный с изменением;
- посмотреть test cases;
- запустить smoke tests;
- открыть report;
- использовать failed step, `error_message`, `request_json`, `response_json` для отладки.

Developer не должен:

- менять test case metadata без autotester/admin;
- добавлять `business` tag без согласования;
- отключать `is_active`, чтобы скрыть проблему;
- менять runner contract без обновления документации и тестов.

Пошагово:

1. Найдите module, например `cards`.
2. Откройте связанные test cases.
3. Запустите `smoke` tests в `test` или `stage`.
4. Если запуск упал, откройте report.
5. Найдите первый failed/broken step.
6. Посмотрите `request_json`, `response_json`, `error_message`.
7. Исправьте продуктовый код или передайте проблему autotester-у, если сломан сам тест.

## 10. How To Use The Platform As Autotester

Autotester отвечает за создание и поддержку автотестов.

Типичный workflow:

1. Создать module, если домена еще нет.
2. Написать runner class.
3. Зарегистрировать runner в registry.
4. Создать TestCase metadata в базе.
5. Задать `input_schema`.
6. Задать tags.
7. Запустить test case через API/UI.
8. Проверить report.
9. Исправить runner или metadata.
10. Поддерживать тест при изменениях продукта.

### Что должно совпадать

| Где | Поле | Пример |
| --- | --- | --- |
| Runner class | `code` | `crm.update_client_phone` |
| TestCase in DB | `code` | `crm.update_client_phone` |
| Request to run | `test_case_code` | `crm.update_client_phone` |

Если эти значения не совпадают, worker не найдет runner и завершит run как `BROKEN`.

### Что проверять перед публикацией test case

- code соответствует naming convention;
- module существует;
- runner зарегистрирован;
- input_schema описывает все обязательные parameters;
- tags помогают найти тест;
- `business` tag стоит только на безопасном бизнес-сценарии;
- report показывает понятные steps;
- при `AssertionError` получается `FAILED`;
- при unexpected exception получается `BROKEN`.

## 11. How To Create A New Module

Module создают ADMIN или AUTOTESTER.

Пример:

```json
{
  "code": "crm",
  "name": "CRM",
  "description": "Client relationship management module"
}
```

Правила для `code`:

- lowercase;
- без пробелов;
- коротко и стабильно;
- отражает домен;
- не менять без необходимости, потому что test cases завязаны на module.

Пример API:

```bash
curl -X POST http://localhost:8000/api/modules \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "crm",
    "name": "CRM",
    "description": "Client relationship management module"
  }'
```

## 12. How To Create A New Test Case

Test Case metadata создают ADMIN или AUTOTESTER.

Пример:

```json
{
  "code": "crm.update_client_phone",
  "name": "Update client phone",
  "description": "Checks that client phone can be updated in CRM",
  "module_id": 3,
  "input_schema": {
    "iin": {"type": "string", "required": true},
    "phone": {"type": "string", "required": true}
  },
  "tags": ["smoke", "crm", "business"],
  "is_active": true
}
```

Поля:

| Field | Объяснение |
| --- | --- |
| `code` | Уникальный идентификатор, должен совпадать с runner `code`. |
| `name` | Человекочитаемое имя. |
| `description` | Что проверяет тест. |
| `module_id` | ID module из `/api/modules`. |
| `owner_id` | Optional. Если не передан, owner - текущий пользователь. |
| `input_schema` | JSON object с правилами parameters. |
| `tags` | JSON array of strings. |
| `is_active` | Только active test cases можно запускать. |

Пример API:

```bash
curl -X POST http://localhost:8000/api/test-cases \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "crm.update_client_phone",
    "name": "Update client phone",
    "description": "Checks that client phone can be updated in CRM",
    "module_id": 3,
    "input_schema": {
      "iin": {"type": "string", "required": true},
      "phone": {"type": "string", "required": true}
    },
    "tags": ["smoke", "crm", "business"],
    "is_active": true
  }'
```

## 13. How To Write A New Autotest Script

Runner contract находится в `backend/app/runner/`.

Минимальные части runner-а:

- наследуется от `BaseTestCase`;
- задает `code`;
- задает `name`;
- задает `module`;
- задает `input_schema`;
- реализует `run(context)`;
- возвращает JSON-serializable dict.

Пример runner-а:

```python
from typing import Any

from app.runner.base import BaseTestCase
from app.runner.context import TestContext


class UpdateClientPhoneTest(BaseTestCase):
    code = "crm.update_client_phone"
    name = "Update client phone"
    module = "crm"

    input_schema = {
        "iin": {"type": "string", "required": True},
        "phone": {"type": "string", "required": True},
    }

    def run(self, context: TestContext) -> dict[str, Any]:
        with context.step("Validate input parameters", request_json=context.params) as step:
            iin = context.params["iin"]
            phone = context.params["phone"]
            step.save_response_json({"message": "Input parameters are valid"})

        with context.step(
            "Mock update client phone",
            request_json={"iin": iin, "phone": phone},
        ) as step:
            response = {"iin": iin, "phone": phone, "status": "UPDATED"}
            step.save_response_json(response)

        with context.step("Validate update status", request_json=response) as step:
            assert response["status"] == "UPDATED", "Client phone was not updated"
            step.save_response_json({"status": response["status"]})

        return {
            "message": "Client phone updated successfully",
            "iin": iin,
            "phone": phone,
            "status": response["status"],
        }
```

### Register Runner

После создания файла runner нужно зарегистрировать в `backend/app/runner/registry.py`:

```python
def register_builtin_tests() -> None:
    from app.runner.tests.cards.issue_virtual_card import IssueVirtualCardTest
    from app.runner.tests.k2.create_payment import CreatePaymentTest
    from app.runner.tests.crm.update_client_phone import UpdateClientPhoneTest

    registry.register(IssueVirtualCardTest)
    registry.register(CreatePaymentTest)
    registry.register(UpdateClientPhoneTest)
```

Правила:

- `code` в script должен совпадать с `TestCase.code` в базе;
- steps должны быть понятными для QA и business users;
- `assert` используется для business validation;
- `AssertionError` означает `FAILED`;
- unexpected exception означает `BROKEN`;
- `request_json` и `response_json` должны помогать отладке, но не содержать секреты.

## 14. Input Schema Guide

`input_schema` описывает, какие parameters принимает test case.

Поддерживаемые типы:

- `string`
- `number`
- `boolean`

Пример:

```json
{
  "iin": {"type": "string", "required": true},
  "amount": {"type": "number", "required": true},
  "force_fail": {"type": "boolean", "required": false}
}
```

Также backend поддерживает JSON Schema-like формат:

```json
{
  "type": "object",
  "required": ["iin", "amount", "currency"],
  "properties": {
    "iin": {"type": "string"},
    "amount": {"type": "number"},
    "currency": {"type": "string"},
    "force_fail": {"type": "boolean"}
  }
}
```

### Required

`required: true` означает, что parameter обязателен. Если пользователь не передаст его, API вернет validation error.

Пример ошибки:

```json
{
  "detail": {
    "message": "Invalid test run parameters",
    "errors": ["Missing required parameter: iin"]
  }
}
```

Почему нельзя принимать любой JSON без схемы:

- пользователь может забыть обязательное поле;
- тип может быть неверным, например `"amount": "50000"` вместо number;
- runner упадет поздно и менее понятно;
- business users не поймут, что именно нужно заполнить;
- UI не сможет генерировать удобные default parameters.

## 15. Report Guide

Report доступен по endpoint:

```text
GET /api/test-runs/{id}/report
```

Report содержит:

- `run`;
- `test_case`;
- `module`;
- `started_by`;
- `steps`.

### TestRun Statuses

| Status | Что значит |
| --- | --- |
| `QUEUED` | Run создан и ждет worker. |
| `RUNNING` | Worker выполняет тест. |
| `PASSED` | Все проверки прошли. |
| `FAILED` | Business/product validation не прошла. |
| `BROKEN` | Сломался тест, код runner-а, mock, connection или инфраструктура. |
| `CANCELLED` | Run отменен. В MVP статус есть, но отдельная отмена не реализована. |
| `TIMEOUT` | Run не завершился вовремя. В MVP статус есть, но timeout logic еще не расширена. |

### FAILED vs BROKEN

`FAILED` - продукт или бизнес-проверка не прошли.

Пример: payment status не стал `COMPLETED`.

`BROKEN` - проблема в самом тесте или инфраструктуре.

Пример:

- runner не зарегистрирован;
- connection refused;
- unexpected exception;
- ошибка в mock logic;
- неправильный import.

### TestRunStep Fields

| Field | Объяснение |
| --- | --- |
| `name` | Название шага. |
| `status` | `RUNNING`, `PASSED`, `FAILED`, `BROKEN`, `SKIPPED`. |
| `duration_ms` | Время выполнения шага. |
| `error_message` | Ошибка, если шаг упал. |
| `request_json` | Что отправляли или какие входные данные использовали. |
| `response_json` | Что получили или рассчитали. |

### Как анализировать report

1. Сначала смотрите общий `run.status`.
2. Если status не `PASSED`, ищите первый step со status `FAILED` или `BROKEN`.
3. Читайте `error_message`.
4. Сравните `request_json` и `response_json`.
5. Если ошибка business validation, заводите defect на продукт.
6. Если ошибка technical, передавайте autotester/developer-у `run_id`.

## 16. Best Practices For Autotesters

- Один test case должен проверять один понятный сценарий.
- Steps должны быть читаемыми: `Validate input parameters`, `Mock issue card`, `Validate card status`.
- Не хардкодьте секреты.
- Не используйте production credentials.
- Не пишите бесконечные циклы.
- Не делайте тест зависимым от порядка запуска других тестов.
- Используйте понятные error messages.
- Добавляйте tags.
- Поддерживайте `input_schema`.
- Отделяйте business validation от infrastructure errors.
- Возвращайте JSON-serializable result.
- Сохраняйте useful `request_json` и `response_json`, но без passwords/tokens/secrets.
- Проверяйте, что `force_fail` или похожие test-only flags не доступны в production-like flows без контроля.

## 17. Bad Practices

Плохие решения, которых нужно избегать:

| Bad practice | Почему плохо |
| --- | --- |
| Один огромный тест на 20 сценариев | Трудно понять причину падения. |
| Code `test1` | Непонятен домен и смысл проверки. |
| Parameters без `input_schema` | Пользователь не знает, что передавать. |
| Hidden hardcoded values | Тест непредсказуем и плохо переносится между environments. |
| Тест меняет данные без cleanup | Следующие запуски могут падать из-за загрязненных данных. |
| Отдельный endpoint на каждый тест | API разрастается и ломает единый flow. |
| Логирование passwords/tokens/secrets | Риск утечки секретов в reports/logs. |
| Tag `business` на техническом тесте | Business users смогут запустить неподходящий сценарий. |
| `BROKEN` вместо понятного `FAILED` | QA не поймет, это defect продукта или дефект теста. |

## 18. API Examples

### Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@local.com","password":"admin"}'
```

Response:

```json
{
  "access_token": "<TOKEN>",
  "token_type": "bearer"
}
```

### Get Modules

```bash
curl http://localhost:8000/api/modules \
  -H "Authorization: Bearer <TOKEN>"
```

### Get Test Cases

```bash
curl "http://localhost:8000/api/test-cases?tag=smoke&is_active=true" \
  -H "Authorization: Bearer <TOKEN>"
```

### Create Test Run

```bash
curl -X POST http://localhost:8000/api/test-runs \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "test_case_code": "cards.issue_virtual_card",
    "environment": "test",
    "parameters": {
      "iin": "990101300000",
      "product_code": "VIRTUAL_CARD",
      "currency": "KZT"
    }
  }'
```

Response:

```json
{
  "run_id": 1,
  "status": "QUEUED"
}
```

### Get Report

```bash
curl http://localhost:8000/api/test-runs/1/report \
  -H "Authorization: Bearer <TOKEN>"
```

### Force Failed Demo Run

Demo runners support `force_fail` for testing report behavior.

```bash
curl -X POST http://localhost:8000/api/test-runs \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "test_case_code": "cards.issue_virtual_card",
    "environment": "test",
    "parameters": {
      "iin": "990101300000",
      "product_code": "VIRTUAL_CARD",
      "currency": "KZT",
      "force_fail": true
    }
  }'
```

## 19. Web UI Guide

Frontend уже реализован и доступен по адресу:

```text
http://localhost:5173
```

### Login Page

На Login page пользователь вводит email и password. После успешного login JWT token сохраняется в `localStorage`, а frontend добавляет `Authorization: Bearer <token>` к API requests.

Demo admin:

```text
admin@local.com / admin
```

### Dashboard

Dashboard показывает краткую сводку:

- modules count;
- test cases count;
- active cases count;
- test runs count;
- queued/running count.

### Modules

Экран `Modules` показывает таблицу:

- id;
- code;
- name;
- description.

Создание/редактирование через UI в MVP ограничено, но API поддерживает CRUD для ADMIN/AUTOTESTER.

### Test Cases

Экран `Test Cases` показывает:

- id;
- code;
- name;
- module;
- tags;
- is_active.

Можно использовать фильтр по tag.

### Run Test

Экран `Run Test` позволяет:

1. выбрать active test case;
2. выбрать environment: `dev`, `test`, `stage`;
3. посмотреть `input_schema`;
4. заполнить `Parameters JSON`;
5. нажать `Queue Run`;
6. открыть report по ссылке.

### Test Runs

Экран `Test Runs` показывает историю запусков:

- id;
- test_case;
- environment;
- status;
- started_by;
- created_at;
- duration_ms;
- link to report.

### Report Page

Report page показывает:

- status;
- test case;
- module;
- environment;
- started_by;
- parameters;
- result;
- error_message;
- steps table.

Для `QUEUED` и `RUNNING` report page автоматически обновляется.

## 20. Troubleshooting

### Cannot Connect To PostgreSQL

Проверьте, что PostgreSQL container запущен:

```bash
docker compose ps
```

Если подключаетесь из pgAdmin внутри Docker network, host должен быть:

```text
postgres
```

Если backend запущен локально на Windows, host обычно:

```text
localhost
```

Если на Windows уже есть локальный PostgreSQL на `localhost:5432`, backend может подключиться не к Docker PostgreSQL. Остановите локальный PostgreSQL или запускайте backend через Docker Compose.

### Redis Connection Refused

Проверьте Redis:

```bash
docker compose ps redis
docker exec autotest_redis redis-cli ping
```

Ожидаемый ответ:

```text
PONG
```

### Celery Worker Is Not Running

Если run завис в `QUEUED`, worker может быть не запущен.

Проверьте:

```bash
docker compose ps worker
docker compose logs worker
```

Локальная команда worker:

```bash
celery -A app.workers.celery_app worker --loglevel=info
```

### TestRun Stuck In QUEUED

Возможные причины:

- worker не запущен;
- Redis недоступен;
- worker смотрит на другой Redis DB;
- task import path сломан;
- backend отправил task, но worker не видит queue.

Проверьте, что worker видит task:

```text
app.workers.tasks.run_test_case
```

### 401 Unauthorized

Причины:

- нет Bearer token;
- token expired;
- token invalid;
- пользователь удален или inactive.

Решение:

1. Выполнить login заново.
2. Передать header:

```text
Authorization: Bearer <TOKEN>
```

### 403 Forbidden

Причины:

- роль не имеет доступа;
- QA пытается создать module;
- BUSINESS пытается запустить test case без tag `business`;
- BUSINESS пытается открыть чужой report.

### TestCase Not Found In Registry

Если report показывает `BROKEN` и error похож на runner not registered, проверьте:

- есть ли runner class;
- совпадает ли runner `code` с `TestCase.code`;
- зарегистрирован ли class в `registry.py`;
- импорт не падает.

### Input Parameters Validation Failed

Проверьте:

- все required fields переданы;
- типы соответствуют schema;
- JSON валидный;
- boolean передан как `true/false`, а не `"true"`/`"false"`;
- number передан как `50000`, а не `"50000"`.

### pgAdmin Host

Внутри pgAdmin host должен быть:

```text
postgres
```

Не используйте `localhost` внутри pgAdmin: там `localhost` означает сам контейнер pgAdmin, а не PostgreSQL container.

## 21. FAQ

### Почему нет endpoint-а на каждый тест?

Потому что платформа запускает все тесты через один стабильный endpoint `POST /api/test-runs`. Новый тест добавляется через runner registry и TestCase metadata, а API остается неизменным.

### Кто может запускать business tests?

`ADMIN`, `AUTOTESTER`, `QA` и `BUSINESS` могут запускать активные test cases. Для `BUSINESS` есть дополнительное ограничение: test case должен иметь tag `business`.

### Как добавить новый module?

ADMIN или AUTOTESTER вызывает `POST /api/modules` или использует будущий UI CRUD. Module code должен быть lowercase и стабильным.

### Как добавить новый автотест?

1. Создать runner class.
2. Зарегистрировать class в `registry.py`.
3. Создать TestCase metadata с таким же `code`.
4. Задать `input_schema`.
5. Задать tags.
6. Запустить тест и проверить report.

### Чем FAILED отличается от BROKEN?

`FAILED` означает, что тест выполнился, но business/product validation не прошла.

`BROKEN` означает, что сломался сам тест, инфраструктура, import, connection, mock или неожиданный кодовый путь.

### Где хранятся результаты?

В PostgreSQL:

- `test_runs`;
- `test_run_steps`.

Report endpoint собирает данные из этих таблиц и связанных `test_cases`, `modules`, `users`.

### Где хранятся test scripts?

Runner scripts находятся в:

```text
backend/app/runner/tests/
```

Примеры:

- `backend/app/runner/tests/cards/issue_virtual_card.py`
- `backend/app/runner/tests/k2/create_payment.py`

### Можно ли запускать тесты против prod?

В MVP UI предлагает `dev`, `test`, `stage`. Запуск против production не должен быть случайным. Если production-like запуск когда-либо понадобится, нужны отдельные правила, credentials, approvals, audit и безопасные тестовые данные.

### Как понять, что проблема в тесте, а не в продукте?

Смотрите report:

- `FAILED` на validation step обычно указывает на продуктовую или бизнес-проблему;
- `BROKEN` обычно указывает на тест, infrastructure или unexpected exception;
- отсутствие runner-а в registry - проблема тестовой платформы;
- connection refused - проблема окружения или интеграции;
- неправильные parameters - проблема запуска или schema.

### Что делать, если test case неактивен?

`is_active=false` означает, что test case нельзя запускать. Причины могут быть разные:

- сценарий временно сломан;
- runner еще не готов;
- тест устарел;
- test data нестабильна.

Обратитесь к AUTOTESTER или ADMIN.

### Что передать autotester-у при проблеме?

Передайте:

- `run_id`;
- `test_case.code`;
- environment;
- parameters без секретов;
- failed/broken step name;
- `error_message`;
- время запуска.
