# Travel Planner

Мобильная платформа для персонализированного планирования путешествий.

## ✨ Основные возможности

*   **Анкетирование предпочтений при первом входе**: Двухэтапная анкета для новых пользователей (интересы, направления, бюджет, длительность).
*   **Гибкий профиль**: Настройка предпочтений в любой момент.
*   **PWA-Ready & iOS First**: 
    *   Полная поддержка Safe Areas (отступы под вырезы и home indicator).
    *   Адаптивный интерфейс без лишних скроллов.
*   **Валидация форм**: Продвинутая инлайн-валидация на базе Zod (минимальные проверки при входе, строгие правила при регистрации).
*   **OAuth**: Быстрая авторизация через Яндекс ID.
*   **Сброс пароля через Email**: Безопасный флоу сброса пароля с использованием одноразовых токенов и стилизованных HTML-писем (Jinja2).

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
make build up
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

## 🔐 Безопасность и Валидация

### Требования к данным (Регистрация):
*   **Логин**: Минимум 3 символа, латиница, цифры и подчеркивание.
*   **Пароль**: Минимум 8 символов, должен содержать строчные и заглавные буквы, цифры и спецсимволы.
*   **Email**: Обязательная проверка формата.

Интерфейс использует «умную» валидацию: ошибки обязательного заполнения имеют приоритет, а формат проверяется при попытке отправки

---

## 🧪 Тестирование и Линтинг

```bash
# Бэкенд тесты и линтинг (ruff)
make test
make lint

# Фронтенд: Проверка архитектуры (Steiger), линтинг (ESLint) и типы
cd frontend && npm run lint && npx tsc --noEmit
```

---

## 📂 Структура проекта

### Frontend (Feature-Sliced Design)
Проект следует методологии **FSD**:
*   `app/` — Инициализация приложения, глобальные стили и роутинг.
*   `pages/` — Композиция страниц из виджетов и фич.
*   `widgets/` — Самостоятельные блоки страницы (Layout, BottomNav).
*   `features/` — Пользовательские сценарии (Auth, Profile Setup).
*   `entities/` — Бизнес-сущности (User, Trip).
*   `shared/` — Переиспользуемый код (API client, UI-kit, lib).

### Backend
*   `services/auth-service/` — Микросервис авторизации на FastAPI.

---

## 🛠 Технологии

| Компонент | Технологии |
|-----------|------------|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0, Pydantic V2, Jinja2 |
| Database | PostgreSQL 15 |
| Cache/Tokens | Redis 7 |
| Auth | JWT, OAuth 2.0 (Yandex) |
| Frontend Architecture | Feature-Sliced Design (FSD) |
| Frontend | React 18, TypeScript, Vite, TanStack Query |
| UI-kit | Shadcn UI, Lucide Icons, Framer Motion |
| PWA | Vite PWA Plugin, Service Workers |

---

## 🔧 Makefile команды

| Команда | Описание |
|---------|----------|
| `make up` | Запустить проект |
| `make build` | Собрать Docker образы |
| `make down` | Остановить и очистить volumes |
| `make test` | Тесты бэкенда |
| `make lint` | Линтинг бэкенда |
| `make install` | Установка зависимостей |
