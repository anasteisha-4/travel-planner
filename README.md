# Triply — Travel Planner

Мобильная платформа (PWA) для персонализированного планирования путешествий.

## ✨ Основные возможности

*   **Дневник поездки с интерактивной картой**: Добавление посещённых мест на карту Яндекс с геокодингом, заметками, датой и временем визита. Карточки мест, детальный просмотр, удаление. Переключение между режимом карты и списком мест.
*   **Аналитика завершённых поездок (Итоги)**: Отдельный таб для завершённых поездок — общая сумма расходов, средний расход в день, количество посещённых мест, длительность, соответствие бюджету (с цветовыми тирами), разбивка по категориям. Конфетти-анимация при завершении поездки.
*   **Анкетирование предпочтений при первом входе**: Двухэтапная анкета онбординга для новых пользователей (интересы, направления, бюджет, длительность и город отправления).
*   **Гибкий профиль**: Настройка предпочтений в любой момент через интуитивно понятный интерфейс.
*   **Учёт расходов (Expense Tracker)**: Полноценная система учёта расходов в поездке с автоматической конвертацией валют через внешнее API (FXRatesAPI.com). Добавление трат в любой валюте, автоматическая конвертация в валюту бюджета поездки. Сводка расходов с прогресс-баром бюджета и разбивкой по категориям. Фильтрация по категории и диапазону дат. Валюта расхода по умолчанию совпадает с валютой поездки.
*   **Управление поездками**: Создание, просмотр, редактирование и удаление поездок с отслеживанием статуса (Планируется, В процессе, Завершено). Автоматическая конвертация бюджета при смене валюты в форме.
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

# ВАЖНО: Добавьте API ключ для валют в .env.docker
# FXR_API_KEY=fxr_live_... (получить на fxratesapi.com)
```

> [!IMPORTANT]
> В `.env.docker` убедитесь, что хосты баз данных и Redis указаны как имена сервисов (`db` и `redis`), а не `localhost`.
> Для работы дневника с картой укажите `VITE_YANDEX_MAPS_API_KEY` (Яндекс Карты JS API v3) и `VITE_GEOAPIFY_API_KEY` (геокодинг).

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

# Фронтенд: Проверка архитектуры (Steiger), линтинг (ESLint) и типы (TSC)
cd frontend && npm run lint && npm run typecheck
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
*   `pages/` — Композиция страниц (Dashboard, Trips, Profile, Onboarding, TripDetail с табами: О поездке / Итоги / Расходы / Дневник).
*   `widgets/` — Самостоятельные блоки (Layout, BottomNav).
*   `features/` — Пользовательские сценарии:
    *   `auth` — авторизация и регистрация.
    *   `trips` — формы, аналитика, управление поездками.
    *   `expenses` — учёт расходов.
    *   `places` — дневник мест с картой (AddPlaceSheet, PlaceDiary, PlaceMap, PlaceList).
    *   `profile`, `onboarding` — профиль и онбординг.
*   `entities/` — Бизнес-сущности (trip, expense, place, user).
*   `shared/` — Переиспользуемый код:
    *   `lib/geocoder/` — геокодинг через Яндекс Карты (useGeocode, useReverseGeocode).
    *   `lib/yandex-maps/` — загрузчик SDK Яндекс Карт.
    *   `lib/query-client/` — глобальный инстанс TanStack Query.
    *   `ui/` — UI-kit на базе Shadcn, `confirm-drawer`.
    *   `api/` — типизированный Axios-клиент.

### Backend
*   `services/auth-service/` — Микросервис авторизации на FastAPI.
*   `services/trip-service/` — Микросервис управления поездок, расходов и мест на FastAPI.
    *   `app/models.py` — Модели Trip, Expense, PlaceVisit.
    *   `app/services/` — Сервисный слой (expense_service, place_service).
    *   `app/routers/` — Роутеры (trips, expenses, places).

---

## 🛠 Технологии

| Компонент | Технологии |
|-----------|------------|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0, Pydantic V2, Alembic, Jinja2 |
| Database | PostgreSQL 15 |
| Cache/Tokens | Redis 7 |
| Auth | JWT, OAuth 2.0 (Yandex) |
| Frontend Architecture | Feature-Sliced Design (FSD) |
| Frontend | React 19, TypeScript, Vite 7, TanStack Query v5 |
| UI-kit | Shadcn UI, TailwindCSS, Lucide Icons, Framer Motion, canvas-confetti |
| Карты | Яндекс Карты JS API v3 |
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

