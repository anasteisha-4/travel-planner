# Triply — Travel Planner

Мобильная платформа (PWA) для персонализированного планирования путешествий.

## ✨ Основные возможности

*   **Анкетирование предпочтений при первом входе**: Двухэтапная анкета онбординга для новых пользователей (интересы, направления, бюджет, длительность и город отправления).
*   **Гибкий профиль**: Настройка предпочтений в любой момент через интуитивно понятный интерфейс.
*   **Управление поездками**: Создание, просмотр, редактирование и удаление поездок с отслеживанием статуса (Планируется, В процессе, Завершено).
*   **Унифицированный UI/UX**: Единый адаптивный дизайн с эффектами размытия фона (glassmorphism), фиксированными шапками (sticky headers) и кастомными компонентами (степперы, удобные календари с проверками при вводе).
*   **PWA-Ready & iOS First**:
    *   Полная поддержка Safe Areas (отступы под вырезы и home indicator) как в портретной, так и в ландшафтной (Landscape) ориентации мобильных устройств.
    *   Адаптивный интерфейс без горизонтальных скроллов.
    *   Автоматическое применение класса `pwa-standalone` для запущенных на домашнем экране приложений.
*   **Валидация форм**: Продвинутая инлайн-валидация на базе Zod (минимальные проверки при входе, строгие правила при регистрации и создании поездок).
*   **Авторизация**: Быстрая авторизация через логин/пароль и Яндекс ID (OAuth).
*   **Сброс пароля через Email**: Безопасный флоу сброса пароля с использованием одноразовых токенов и стилизованных HTML-писем (на базе Jinja2).

---

## 🚀 Быстрый старт

### 1. Подготовка окружения
Для работы проекта необходим **Docker**.

```bash

# 1. Настройте переменные окружения
# Для локального запуска (БД в Docker, код локально)
cp .env.example .env
# Для запуска всего проекта в Docker
cp .env.example .env.docker
```

> [!IMPORTANT]
> В `.env.docker` убедитесь, что хосты баз данных и Redis указаны как имена сервисов (`db` и `redis`), а не `localhost`.

### 2. Запуск проекта (Docker Compose)

```bash
# Сборка и запуск
make build up

# Применение миграций (выполняется автоматически при старте, но можно запустить вручную)
make migrate
```

*   **Frontend**: [http://localhost](http://localhost)
*   **Auth Service**: [http://localhost:8001/docs](http://localhost:8001/docs)
*   **Trip Service**: [http://localhost:8002/docs](http://localhost:8002/docs)

### 3. Локальная разработка (Hybrid)
Для изменений в код бэкенда с hot-reload:

```bash
# 1. Запустите инфраструктуру (БД и Redis)
docker-compose up -d db redis

# 2. Установите зависимости и запустите интересующий сервис
cd services/auth-service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001

# 3. В другом терминале запустите фронтенд
cd frontend
npm install
npm run dev
```

---

## 🔐 Безопасность и Валидация

### Требования к данным (Регистрация):
*   **Логин**: Минимум 3 символа, латиница, цифры и подчеркивание.
*   **Пароль**: Минимум 8 символов, должен содержать строчные и заглавные буквы, цифры и спецсимволы.
*   **Email**: Обязательная проверка формата.

Интерфейс использует «умную» валидацию: ошибки обязательного заполнения имеют приоритет, а формат проверяется при попытке отправки.

---

## 🧪 Тестирование и Линтинг

```bash
# Бэкенд тесты (внутри Docker)
make test
make test-cov

# Линтинг (ruff)
make lint

# Фронтенд: Проверка архитектуры (Steiger), линтинг (ESLint) и типы
cd frontend && npm run lint && npx tsc --noEmit
```

---

## 🗃 Миграции базы данных (Alembic)

Проект использует **Alembic** для управления миграциями. Каждый сервис имеет собственный набор миграций.

```bash
# Создать новую миграцию (после изменения models.py)
docker-compose run --rm auth-service alembic revision --autogenerate -m "описание"
docker-compose run --rm trip-service alembic revision --autogenerate -m "описание"

# Применить миграции
docker-compose run --rm auth-service alembic upgrade head
docker-compose run --rm trip-service alembic upgrade head

# Откатить последнюю миграцию
docker-compose run --rm auth-service alembic downgrade -1
```

> **Примечание**: При запуске Docker-контейнеров миграции применяются автоматически (`alembic upgrade head` в CMD).

---

## 📂 Структура проекта

### Frontend (Feature-Sliced Design)
Проект следует методологии **FSD**:
*   `app/` — Инициализация приложения, глобальные стили и роутинг.
*   `pages/` — Композиция страниц из виджетов и фич (Dashboard, Trips, Profile, Onboarding).
*   `widgets/` — Самостоятельные блоки (Layout, BottomNav).
*   `features/` — Пользовательские сценарии (Auth, Trips Формы).
*   `entities/` — Бизнес-сущности.
*   `shared/` — Переиспользуемый код (API client, UI-kit на базе Shadcn, config).

### Backend
*   `services/auth-service/` — Микросервис авторизации на FastAPI.
*   `services/trip-service/` — Микросервис управления поездок на FastAPI.

---

## 🛠 Технологии

| Компонент | Технологии |
|-----------|------------|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0, Pydantic V2, Alembic, Jinja2 |
| Database | PostgreSQL 15 |
| Cache/Tokens | Redis 7 |
| Auth | JWT, OAuth 2.0 (Yandex) |
| Frontend Architecture | Feature-Sliced Design (FSD) |
| Frontend | React 18, TypeScript, Vite, TanStack Query |
| UI-kit | Shadcn UI, TailwindCSS, Lucide Icons, Framer Motion |
| PWA | Vite PWA Plugin, Service Workers |

---

## 🔧 Makefile команды

| Команда | Описание |
|---------|----------|
| `make dev` | Локальный запуск БД, Redis и Auth Service без Docker фронтенда |
| `make up` | Запустить весь проект в Docker |
| `make build` | Собрать Docker образы |
| `make down` | Остановить и очистить volumes |
| `make test` | Тесты auth-service и trip-service (Docker) |
| `make test-cov` | Тесты с покрытием (Docker) |
| `make lint` | Линтинг auth-service |
| `make install` | Установка зависимостей auth-service |

