# Travel Planner

Интеллектуальная веб-система персонализированного планирования путешествий.

## 🚀 Быстрый старт

### 1. Настройка окружения

```bash
# Скопируйте пример .env и настройте при необходимости, заменив `localhost` на имена контейнеров в .env.docker
cp .env.example .env
cp .env.example .env.docker
```

### 2. Запуск приложения в Docker

```bash
docker-compose up -d
```

Auth Service будет доступен: http://localhost:8001

**Swagger UI**: http://localhost:8001/docs

### 3. Запуск для разработки (без Docker)

```bash
# Запустите только БД и Redis в Docker
docker-compose up -d postgres redis

# Установите зависимости
cd services/auth-service
pip install -r requirements.txt

# Запустите auth-service
uvicorn app.main:app --reload --port 8001
```

### 4. Запуск фронтенда

```bash
cd frontend && npm install && npm run dev
```

---

## 🧪 Тестирование

### Запуск тестов Auth Service

```bash
# Запустите БД
docker-compose up -d postgres redis

cd services/auth-service

# Тесты
pytest tests/ -v

# Тесты с покрытием
pytest tests/ --cov=app --cov-report=term-missing
```

Тестовая БД `travel_planner_test` создаётся автоматически.

---

## 📁 Структура проекта

```
travel-planner/
├── services/                    # Backend микросервисы
│   └── auth-service/            # Аутентификация (FastAPI)
│       ├── app/
│       │   ├── routers/        # Endpoints
│       │   ├── config.py       # Настройки
│       │   ├── models.py       # SQLAlchemy модели
│       │   └── ...
│       └── tests/              # pytest
├── frontend/                   # React + Vite
├── docker-compose.yml
├── .env                        # Локальная разработка
├── .env.docker                 # Docker окружение
└── .env.example
```

---

## 🛠 Технологии

| Компонент | Технологии |
|-----------|------------|
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | PostgreSQL 15 |
| Cache/Tokens | Redis 7 |
| Auth | JWT (python-jose), Argon2 |
| Frontend | React, TypeScript, Vite |
| Infrastructure | Docker, Docker Compose |
| Testing | pytest, httpx, fakeredis |

---

## 🔐 API Endpoints

### Auth Service (`:8001`)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/api/auth/register` | Регистрация |
| POST | `/api/auth/login` | Вход |
| POST | `/api/auth/refresh` | Обновление токенов |
| POST | `/api/auth/password/change` | Смена пароля |
| POST | `/api/auth/logout` | Выход |
| POST | `/api/auth/logout-all` | Выход со всех устройств |
| GET | `/api/users/me` | Профиль |
| PUT | `/api/users/me` | Обновление профиля |
| GET | `/api/users/me/preferences` | Предпочтения |
| PUT | `/api/users/me/preferences` | Обновление предпочтений |
| GET | `/health` | Health check |

**Swagger**: http://localhost:8001/docs

---

## 🔧 Переменные окружения

| Переменная | Описание | Локально | Docker |
|------------|----------|----------|--------|
| `DATABASE_URL` | PostgreSQL | `...@localhost:5432/...` | `...@postgres:5432/...` |
| `REDIS_URL` | Redis | `redis://localhost:6379` | `redis://redis:6379` |
| `JWT_SECRET` | Секрет JWT | обязательно | обязательно |
| `CORS_ORIGINS` | CORS origins | `http://localhost:5173` | `http://localhost:5173` |
