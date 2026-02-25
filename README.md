# Travel Planner

Платформа для персонализированного планирования путешествий.

## ✨ Основные возможности

*   **Анкетирование предпочтений при первом входе**: Двухэтапная анкета для новых пользователей (интересы, направления, бюджет, длительность).
*   **Гибкий профиль**: Настройка предпочтений в любой момент.
*   **PWA-Ready**: Оптимизировано для мобильных устройств, поддержка жестов и нативной навигации.
*   **OAuth**: Быстрая авторизация через Яндекс ID.

---

## 🚀 Быстрый старт

### 1. Настройка окружения

```bash
# Скопируйте .env и настройте (в .env.docker замените localhost на имена контейнеров)
cp .env.example .env
cp .env.example .env.docker

# Установите зависимости бэкенда
make install
```

### 2. Запуск в Docker

```bash
make up
```

*   **Frontend**: http://localhost
*   **Auth Service**: http://localhost:8001
*   **Swagger UI**: http://localhost:8001/docs

### 3. Локальная разработка

```bash
# Бэкенд
make dev

# Фронтенд
cd frontend && npm install && npm run dev
```

---

## 🧪 Тестирование и Линтинг

```bash
# Бэкенд тесты
make test

# Проверка линтером (ruff)
make lint

# Фронтенд линтинг и проверка типов
cd frontend && npm run lint && npx tsc --noEmit
```

---

## 📂 Структура проекта

```
travel-planner/
├── services/
│   └── auth-service/           # Сервис авторизации (FastAPI)
│       ├── app/                # Логика приложения (models, schemas, routers)
│       └── tests/              # Набор pytest тестов
├── frontend/                   # React PWA (Vite + Shadcn UI)
│   ├── src/api/                # Функции взаимодействия с API
│   ├── src/pages/              # Страницы (Onboarding, Dashboard, Login)
│   └── src/components/         # UI компоненты
├── docker-compose.yml          # Оркестрация сервисов
└── Makefile                    # Команды для упрощения разработки
```

---

## 🛠 Технологии

| Компонент | Технологии |
|-----------|------------|
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic V2 |
| Database | PostgreSQL 15 |
| Cache/Tokens | Redis 7 |
| Auth | JWT, OAuth 2.0 (Yandex) |
| Frontend | React, TypeScript, Vite, Shadcn UI |
| Styling | TailwindCSS (с поддержкой Liquid Glass UI) |
| Infrastructure | Docker Compose |

---

## 🔐 API Endpoints (Auth Service)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/api/auth/register` | Регистрация |
| POST | `/api/auth/login` | Вход |
| POST | `/api/auth/yandex/authorize` | Авторизация через Яндекс |
| GET | `/api/users/me` | Профиль |
| PUT | `/api/users/me/preferences` | Сохранение анкеты |
| GET | `/api/users/me/preferences` | Получение текущих предпочтений |

---

## 🔧 Makefile команды

| Команда | Описание |
|---------|----------|
| `make up` | Запустить проект в Docker |
| `make build` | Пересобрать Docker образы |
| `make down` | Остановить контейнеры и очистить volumes |
| `make test` | Запустить тесты бэкенда |
| `make lint` | Проверка кода линтером |
| `make install` | Установка Python зависимостей |
