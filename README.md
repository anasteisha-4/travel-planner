# Travel Planner

Интеллектуальная веб-система персонализированного планирования путешествий.

## 🚀 Быстрый старт

### 1. Настройка окружения

```bash
# Скопируйте .env и настройте (в .env.docker замените localhost на имена контейнеров)
cp .env.example .env
cp .env.example .env.docker

# Установите зависимости
make install
```

### 2. Запуск в Docker

```bash
make up
```

Auth Service: http://localhost:8001  
**Swagger UI**: http://localhost:8001/docs

### 3. Локальная разработка

```bash
make dev
```

### 4. Фронтенд

```bash
cd frontend && npm install && npm run dev
```

---

## 🧪 Тестирование

```bash
# Тесты
make test

# Тесты с покрытием
make test-cov

# Линтер
make lint

# Авто-исправление
make fix
```

Тестовая БД `travel_planner_test` создаётся автоматически.

---

## � Makefile команды

| Команда | Описание |
|---------|----------|
| `make up` | Запустить в Docker |
| `make down` | Остановить + удалить volumes |
| `make build` | Пересобрать образы |
| `make dev` | Локальная разработка |
| `make test` | Тесты |
| `make test-cov` | Тесты с покрытием |
| `make lint` | Проверка ruff |
| `make fix` | Авто-исправление |
| `make install` | Установить зависимости |
| `make clean` | Очистить кеши |

---

## 📁 Структура проекта

```
travel-planner/
├── services/
│   └── auth-service/           # FastAPI
│       ├── app/
│       └── tests/
├── frontend/                   # React + Vite
├── .github/workflows/          # CI/CD
├── docker-compose.yml
├── Makefile
├── .env                        # Локальная разработка
└── .env.docker                 # Docker
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
| CI | GitHub Actions, ruff |

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
