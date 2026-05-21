# Triply — Travel Planner

Мобильная платформа (PWA) для персонализированного планирования путешествий с ML-рекомендациями направлений.

## ✨ Основные возможности

- **Персонализированные рекомендации направлений**: Content-based ML-scorer ранжирует 1 096 направлений по профилю пользователя — предпочтениям отдыха, бюджету, визовым ограничениям, климату, риск-толерантности и городу вылета. Каждая рекомендация содержит разбивку факторов (score_breakdown) и теги-объяснения.
- **Расширенная анкета предпочтений**: 6-экранный онбординг с 12 вопросами. Ранжирование видов отдыха с порядком выбора (tap-to-order), autocomplete города вылета, multi-select любимых направлений, слайдеры риска и людности, фильтры визового режима и климата.
- **Прогноз бюджета поездки**: Оценка стоимости по направлению, длительности, количеству человек и месяцу. Учитывает стоимость жилья, питания, транспорта и категорию путешественника.
- **Дневник поездки с интерактивной картой**: Добавление посещённых мест на карту Яндекс с геокодингом, заметками, датой и временем визита. Переключение между режимом карты и списком мест.
- **Аналитика завершённых поездок (Итоги)**: Общая сумма расходов, средний расход в день, количество мест, длительность, соответствие бюджету, разбивка по категориям, конфетти-анимация при завершении.
- **Учёт расходов**: Добавление трат в любой валюте с автоматической конвертацией через FXRatesAPI. Прогресс-бар бюджета, фильтрация по категории и дате.
- **Управление поездками**: Создание, редактирование, удаление, статусы (Планируется / В процессе / Завершено).
- **Отзывы о поездках**: Форма обратной связи после завершения поездки (оценки направления, соотношения цена/качество, фактические расходы, готовность вернуться).
- **Авторизация**: Логин/пароль и Яндекс ID (OAuth). Сброс пароля через email.
- **PWA-Ready & iOS First**: Safe Areas, bottom drawers вместо модалок, нативные тач-паттерны, standalone-режим.

---

## 🚀 Быстрый старт

### 1. Подготовка окружения

Для работы проекта необходим **Docker**.

```bash
# Настройте переменные окружения
cp .env.docker.example .env.docker
```

> [!IMPORTANT]
> В `.env.docker` хосты БД и Redis указывайте как имена сервисов Docker (`postgres`, `redis`), а не `localhost`.
> Для карт и геокодинга используйте только серверные `YANDEX_MAPS_API_TOKEN`, `YANDEX_GEOSUGGEST_API_KEY` и `GEOAPIFY_API_KEY`; не добавляйте их в `VITE_*`.
> Для валют: `FXR_API_KEY` (fxratesapi.com).

### 2. Запуск (Docker Compose)

```bash
make build up
```

| Сервис                | URL                        |
| --------------------- | -------------------------- |
| Frontend              | http://localhost           |
| Auth Service API      | http://localhost:8001/docs |
| Trip Service API      | http://localhost:8002/docs |
| ML Service API        | http://localhost:8004/docs |
| Analytics Service API | http://localhost:8005/docs |

### 3. Локальная разработка (Hybrid)

```bash
# Инфраструктура в Docker
docker-compose up -d postgres redis

# Каждый сервис локально
cd services/auth-service && uvicorn app.main:app --reload --port 8001
cd services/trip-service && uvicorn app.main:app --reload --port 8002
cd services/ml-service && uvicorn app.main:app --reload --port 8004
cd services/analytics-service && uvicorn app.main:app --reload --port 8005

# Фронтенд
cd frontend && npm run dev
```

`npm run dev` и `npm run build` для фронтенда читают корневой `.env.docker` через Vite mode `docker`.

---

## 🔐 Безопасность и Валидация

- **Логин**: минимум 3 символа, латиница, цифры, подчеркивание
- **Пароль**: минимум 8 символов, строчные + заглавные + цифры + спецсимволы
- **Email**: обязательная проверка формата

---

## 🧪 Тестирование и Линтинг

```bash
# Бэкенд тесты
make test
make test-cov

# Линтинг (ruff)
make lint

# Фронтенд
cd frontend && npm run lint && npm run typecheck
```

---

## 🗃 Миграции базы данных (Alembic)

Каждый сервис имеет свою версионную таблицу в общей БД.

```bash
# Создать миграцию
docker-compose run --rm trip-service alembic revision --autogenerate -m "описание"

# Применить
docker-compose run --rm auth-service alembic upgrade head
docker-compose run --rm trip-service alembic upgrade head

# Откатить
docker-compose run --rm trip-service alembic downgrade -1
```

> Миграции применяются автоматически при старте контейнеров.

---

## 📂 Структура проекта

### Backend (микросервисы)

| Сервис              | Порт | Ответственность                                               |
| ------------------- | ---- | ------------------------------------------------------------- |
| `auth-service`      | 8001 | JWT (RS256), Yandex OAuth, сброс пароля                       |
| `trip-service`      | 8002 | Trip/Expense/PlaceVisit CRUD, профиль пользователя, онбординг |
| `data-service`      | 8003 | Read-only данные направлений, поиск, итинерарии               |
| `ml-service`        | 8004 | Рекомендации направлений, прогноз бюджета, валидация          |
| `analytics-service` | 8005 | Event tracking, post-trip feedback, user features             |

**Общий PostgreSQL 15**, **Redis 7** для blacklist JWT и кэша.

Nginx проксирует все запросы с фронтенда на нужные сервисы по prefix-match.

### ML Service — как работает рекомендация

1. Загружает профиль пользователя из trip-service (12 полей)
2. Загружает feature-матрицу из data-service (safety, costs, seasonality, activities, visa, popularity, attributes, language, connectivity, infrastructure)
3. Content-based scorer выставляет score каждому из 1 096 направлений по 10 факторам с весами
4. Возвращает топ-N с `score_breakdown` и `explanation_tags`

Модель поддерживает fallback: если LightGBM не обучен — используется content-based scorer.

### Analytics Service — как работает трекинг

Фронтенд батчит события (flush каждые 5 сек или при выходе) и отправляет в `/api/v1/events`. Агрегированные фичи пользователя (просмотренные/кликнутые направления, сессии, история поездок) доступны через `/api/v1/users/{id}/features` и используются ML-сервисом как дополнительный слой сигналов.

### Frontend (Feature-Sliced Design)

```
app/          — роутинг, провайдеры, глобальные стили
pages/        — Dashboard, Login, Register, Onboarding, Profile,
                Trips, TripDetail (О поездке / Итоги / Расходы / Дневник),
                Recommendations
widgets/      — Layout, BottomNav
features/
  auth            — авторизация, регистрация, OAuth callback
  trips           — формы, аналитика, управление
  expenses        — учёт расходов
  places          — дневник мест с картой
  onboarding-v2   — 6-экранная анкета с прогрессивным сохранением
  profile         — просмотр и редактирование профиля
  recommendations — карточки рекомендаций, фильтры, detail sheet
  feedback        — форма отзыва после поездки
entities/     — trip, expense, place, user
shared/
  api/        — типизированный Axios-клиент + analytics.ts (sendEvent)
  lib/        — geocoder, yandex-maps, query-client
  ui/         — UI-kit (Shadcn-based)
  config/     — константы (валюты, типы поездок, предпочтения)
```

---

## 🗄 Данные (data-service)

| Таблица                 | Покрытие          | Содержимое                                                                                       |
| ----------------------- | ----------------- | ------------------------------------------------------------------------------------------------ |
| destinations            | 1 096 активных    | Города и курорты: координаты, регион, население                                                  |
| poi                     | 2 102 960 записей | OTM + OSM Overpass + Heritage; рейтинги, часы работы, категории                                  |
| destination_safety      | 1 096/1 096       | GPI-индекс → safety_score 0–1                                                                    |
| destination_costs       | 1 096/1 096       | Numbeo cost_index + regional defaults                                                            |
| destination_seasonality | 13 152 строк      | 12 месяцев × 1 096 направлений; temp + precip + humidity                                         |
| destination_activities  | 1 092/1 096       | 10 типов (beach, culture, nature, adventure, food, nightlife, wellness, shopping, family, urban) |
| destination_popularity  | 1 056/1 096       | Wikipedia pageviews, crowd_index (сезонный индекс)                                               |
| visa_rules              | 220 492 правил    | Passport Index Jan 2025, 199 гражданств                                                          |
| destination_attributes  | 1 096/1 096       | is_coastal, has_ski, has_thermal, has_mountains и др.                                            |
| language                | 1 096/1 096       | russian/english_speaking_score, script_difficulty                                                |
| connectivity            | 1 096/1 096       | connectivity_score, mir_card_accepted                                                            |
| infrastructure          | 1 096/1 096       | has_metro, internet speed, healthcare score, taxi_app                                            |

Синтетические обучающие данные: 10k профилей пользователей, 100k бюджетных записей, 50k траекторий.

---

## 🛠 Технологии

| Компонент             | Технологии                                                 |
| --------------------- | ---------------------------------------------------------- |
| Backend               | Python 3.11, FastAPI, SQLAlchemy 2.0, Pydantic V2, Alembic |
| ML                    | scikit-learn, LightGBM, numpy, pandas, rapidfuzz           |
| Database              | PostgreSQL 15                                              |
| Cache                 | Redis 7                                                    |
| Auth                  | JWT RS256, OAuth 2.0 (Yandex)                              |
| Frontend              | React 19, TypeScript, Vite 7, TanStack Query v5            |
| Frontend Architecture | Feature-Sliced Design (FSD)                                |
| UI-kit                | Shadcn UI, TailwindCSS, Lucide Icons, canvas-confetti      |
| Карты                 | Яндекс Карты JS API v3, Geoapify                           |
| PWA                   | Vite PWA Plugin, Service Workers                           |

---

## 🔧 Makefile команды

| Команда         | Описание                                            |
| --------------- | --------------------------------------------------- |
| `make up`       | Запустить весь проект в Docker                      |
| `make build`    | Собрать Docker образы                               |
| `make down`     | Остановить контейнеры                               |
| `make migrate`  | Применить миграции всех сервисов                    |
| `make test`     | Тесты auth-service, trip-service, analytics-service |
| `make test-cov` | Тесты с покрытием                                   |
| `make lint`     | Линтинг бэкенда (ruff)                              |
