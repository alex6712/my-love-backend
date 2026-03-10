# 💖 My Love Backend

Романтичное приложение-подарок на 14 февраля от Лёши для Светы.

_Серверная часть. Android-клиент: [My Love Android](https://github.com/alex6712/my-love-android)._
_Web-клиент: [My Love Web](https://github.com/alex6712/my-love-web)._

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![MinIO](https://img.shields.io/badge/MinIO-CF163D?style=for-the-badge&logo=minio&logoColor=white)](https://www.min.io/)

> Личный цифровой сад наших отношений - место для воспоминаний, мечтаний и маленьких секретов вдвоём.

## ✨ Особенности

### 📸 **Личный медиа-архив**
- Загружай фото и видео важных моментов
- Автоматическая сортировка по датам и событиям
- Приватное облачное хранение (доступно только нам двоим)

### 💌 **Тайные записки**
- Вишлисты подарков (чтобы не гадать)
- Список "Когда-нибудь вместе" (мечты и планы)
- Благодарности и теплые слова друг другу
- Контекстные заметки к фотографиям

### 🎮 **Мини-игры для пары**
- Викторина "Как хорошо мы знаем друг друга?"
- Парные головоломки
- Игра в ассоциации для создания новых воспоминаний

### 🔒 **Максимальная приватность**
- Только два пользователя в системе
- Криптография на эллиптических кривых
- Файлы хранятся в приватном бакете
- Аутентификация на JSON Web Tokens (JWT)

## 🚀 Быстрый старт

### Предварительные требования
- Docker и Docker Compose (v2+)
- Python 3.12+ (для локальной разработки)
- OpenSSL

### Запуск в Docker (рекомендуется)

```bash
# Клонируйте репозиторий
git clone https://github.com/alex6712/my-love-backend.git
cd my-love-backend

# Создайте .env файл из примера и отредактируйте его
cp .env.example .env

# Сгенерируйте EC ключи подписи
chmod +x ./scripts/gen_keys.sh
./scripts/gen_keys.sh

# Запустите все сервисы
docker compose --env-file .env up -d --wait

# Примените миграции
docker exec my-love-backend alembic upgrade head
```

Сервисы будут доступны по следующим адресам:
- Backend API: http://localhost:8000
- PostgreSQL: http://localhost:5432
- Redis: http://localhost:6379
- MinIO: http://localhost:9000

Также будет доступна MinIO Console: http://localhost:9001

### Локальная разработка

Рекомендуется установить пакетный менеджер uv (см. [как установить](https://docs.astral.sh/uv/getting-started/installation/)). В ином случае используйте pip.

```bash
# Клонируйте репозиторий
git clone https://github.com/alex6712/my-love-backend.git
cd my-love-backend

# Установите зависимости с помощью менеджера uv
uv sync --group dev

# Или создайте виртуальное окружение
python -m venv ./.venv
# активируйте его
source ./.venv/bin/activate
# и установите зависимости через pip
pip install -r requirements-dev.txt

# Создайте .env файл из примера и отредактируйте его
cp .env.example .env

# Сгенерируйте EC ключи подписи
chmod +x ./scripts/gen_keys.sh
./scripts/gen_keys.sh

# Настройте свои сервисы PostgreSQL, Redis и MinIO или запустите готовые через Docker
docker compose --env-file .env up my-love-database my-love-redis my-love-minio -d --wait

# Примените миграции
alembic upgrade head
# или
uv run alembic upgrade head

# Запустите сервер
fastapi dev ./app/main.py
# или
uv run fastapi dev ./app/main.py
```

## 📁 Структура проекта

```
my-love-backend/                # FastAPI приложение
├── .github/workflows/          # CI/CD workflow (тесты и деплой)
├── alembic/                    # Alembic миграции
├── app/
│   ├── api/                    # Эндпоинты
│   │   └── v1/
│   ├── core/                   # Конфигурация, безопасность
│   │   ├── dependencies/       # Зависимости для DI
│   │   └── exceptions/         # Исключения приложения
│   ├── handlers/               # Обработчики доменных исключений
│   │   ├── client/
│   │   ├── server/
│   │   └── success/
│   ├── infrastructure/         # Инфраструктурные классы
│   ├── models/                 # SQLAlchemy модели
│   ├── repositories/           # Репозитории для работы с БД
│   ├── schemas/                # Pydantic схемы
│   │   ├── dto/                # Схемы DTO
│   │   └── v1/
│   │       ├── requests/       # Схемы запросов
│   │       └── responses/      # Схемы ответов
│   ├── services/               # Бизнес-логика
│   └── tests/                  # Тестирование
│   │   ├── test_api/
│   │   ├── test_repositories/
│   │   ├── test_security/
│   │   └── test_services/
├── keys/                       # Ключи шифрования и подписи
├── scripts/                    # Утилиты для администрирования
├── .env                        # Значения конфигурации приложения
├── pyproject.toml              # Зависимости (uv)
└── docker-compose.yml          # Контейнеры для разработки
```

## 🏗️ Архитектура приложения

Проект построен как слоистый backend на FastAPI с чётким разделением ответственности между API, бизнес-логикой, доступом к данным и инфраструктурой.

**Поток запроса:**  
`HTTP -> Router -> Dependencies -> Service -> Repository + UnitOfWork -> PostgreSQL/Redis/S3 -> Response schema`

### Основные слои

- **API (`app/api/...`)**  
  Роутеры и HTTP-контракты. Принимают запросы, валидируют входные данные и возвращают типизированные ответы.
- **Services (`app/services/...`)**  
  Реализация use-case’ов и бизнес-правил. Здесь находятся сценарии приложения, а не SQL/HTTP-детали.
- **Repositories (`app/repositories/...`)**  
  Изолированный доступ к данным через SQLAlchemy-модели (`app/models/...`).
- **Infrastructure (`app/infrastructure/...`)**  
  Адаптеры внешних систем: PostgreSQL, Redis, S3/MinIO.
- **Core (`app/core/...`)**  
  Базовые зависимости, безопасность, исключения, общие типы и вспомогательная логика.
- **Schemas (`app/schemas/...`)**  
  DTO и API-схемы запросов/ответов, формализующие границы между слоями.

### Ключевые принципы

- **Request-scoped композиция зависимостей:** `ServiceManager` собирает сервисы на один запрос, но не заменяет архитектуру слоёв.
- **Транзакционность через Unit of Work:** согласованная работа репозиториев в рамках одной сессии/транзакции.
- **Явные контракты данных:** разделение DTO внутреннего слоя и публичных API-схем.
- **Единая модель ошибок:** доменные исключения маппятся в предсказуемые HTTP-ответы через handlers.
- **Security by design:** JWT, Argon2, безопасная работа с refresh-токенами и ключами подписи.

### Как расширять систему

1. Добавить endpoint в `app/api/v1/...`.
2. Реализовать use-case в `app/services/...`.
3. Добавить/обновить операции в `app/repositories/...` (и при необходимости модели в `app/models/...`).
4. Обновить схемы в `app/schemas/...`.
5. Если меняется БД - добавить миграцию в `alembic/versions/...`.
6. Покрыть изменения тестами соответствующего уровня (`test_api`, `test_services`, `test_repositories`, `test_security`).

## 📚 API Документация

После запуска сервера доступны:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🎯 Основные эндпоинты

| Метод | Путь | Описание | Авторизация |
|-------|------|----------|-------------|
| GET | `/health` | Healthcheck | ❌ |
| GET | `/app_info` | Информация о приложении | ❌ |
| POST | `/v1/auth/register` | Регистрация | ❌ |
| POST | `/v1/auth/login` | Вход в систему | ❌ |
| GET | `/v1/auth/refresh` | Обновление токена | ✅ |
| POST | `/v1/auth/logout` | Выход из системы | ✅ |
| GET | `/v1/couples/partner` | Информация о партнёре | ✅ |
| POST | `/v1/couples/request` | Запрос на создание пары | ✅ |
| POST | `/v1/couples/{id}/accept` | Принятие запроса | ✅ |
| POST | `/v1/couples/{id}/decline` | Отклонение запроса | ✅ |
| GET | `/v1/couples/pending` | Список запросов | ✅ |
| GET | `/v1/media/files/count` | Подсчёт количества файлов | ✅ |
| POST | `/v1/media/files/upload` | Загрузить файл | ✅ |
| GET | `/v1/media/files/{file_id}/download` | Скачать файл | ✅ |
| GET | `/v1/media/albums` | Список альбомов | ✅ |
| POST | `/v1/media/albums` | Создание альбома | ✅ |

## 🧪 Тестирование

```bash
# Запуск тестов
uv run pytest ./app/tests/

# С покрытием кода (отчёт будет в папке htmlcov)
uv run pytest --cov=app --cov-report html ./app/tests/
```

## 📦 Деплой

### На VPS (например, Ubuntu + Nginx)

```bash
# 1. Клонируйте репозиторий на сервер, например
rsync -az --delete ./ {ssh_user}@{ssh_host}:~/my-love-backend

# 2. Настройте .env для продакшена
# 3. Запустите через Docker Compose
docker compose --env-file .env up -d --wait

# 4. Настройте Nginx как reverse proxy
# 5. Настройте SSL через Let's Encrypt
```

## 🌱 Планы по развитию

- Мобильное приложение (React Native)
- Push-уведомления (напоминания о датах)
- End-to-end шифрование заметок
- Генератор "истории любви" на основе данных
- Интеграция с календарем (повторяющиеся события)
- Экспорт данных (PDF-книга воспоминаний)

## 💝 Особенности для пары

Это приложение создано с мыслью о том, что цифровое пространство может быть таким же тёплым и личным, как бумажный дневник. Здесь нет алгоритмов, нет рекламы, нет слежки - только вы и ваши эмоции.

## 📄 Лицензия

Этот проект лицензирован под MIT License - смотрите файл [LICENSE](LICENSE) для деталей.

---

> _Сделано с ❤️ для одной особенной пары.  
> Код может быть неидеальным, но чувства - настоящие._
