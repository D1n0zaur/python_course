# Marketplace API - Курсовая работа
## Описание проекта
API для маркетплейса с несколькими продавцами, реализующее:

Каталог товаров с полными CRUD операциями

Систему заказов с автоматической привязкой к аутентифицированным пользователям

Систему комиссий для продавцов

JWT-аутентификацию с разделением прав доступа (администраторы/пользователи)

Веб-интерфейс для тестирования функциональности

## Быстрый старт
Предварительные требования
Python 3.11 или выше

Git (для клонирования репозитория)

Установка и запуск локально
Клонируйте репозиторий

bash
git clone <ваш-репозиторий>
cd marketplace-api
Создайте виртуальное окружение и активируйте его

bash
### Для Windows:
python -m venv venv
venv\Scripts\activate

### Для Linux/Mac:
python -m venv venv
source venv/bin/activate
Установите зависимости

bash
pip install -r requirements.txt
Создайте файл .env

bash
### Создайте файл .env в корневой директории
SECRET_KEY=ваш-секретный-ключ-для-jwt-изменяйте-это-значение
DATABASE_URL=sqlite+aiosqlite:///marketplace.db
ACCESS_TOKEN_EXPIRE_MINUTES=30
Запустите сервер

bash
uvicorn app.main:app --reload
Приложение будет доступно по адресу: http://localhost:8000

## Документация API
После запуска доступна автоматически сгенерированная документация:

Swagger UI (интерактивная): http://localhost:8000/docs

ReDoc (альтернативная): http://localhost:8000/redoc

## Архитектура проекта
Структура каталогов
text
marketplace/
├── app/                    # Основное приложение
│   ├── main.py            # Точка входа FastAPI (все эндпоинты)
│   ├── database.py        # Настройка асинхронной БД
│   ├── jwt_manager.py     # Управление JWT токенами
│   ├── security.py        # Хеширование паролей (bcrypt)
│   └── dependencies.py    # Зависимости для аутентификации
├── models/                # Модели SQLAlchemy
│   ├── user.py           # Пользователи
│   ├── seller.py         # Продавцы
│   ├── product.py        # Товары
│   └── order.py          # Заказы (упрощенная модель)
├── schemas/              # Схемы Pydantic
│   ├── auth.py           # Аутентификация
│   ├── user.py           # Пользователи
│   ├── seller.py         # Продавцы
│   ├── product.py        # Товары
│   └── order.py          # Заказы
├── .env                  # Переменные окружения
├── requirements.txt      # Зависимости Python
└── README.md            # Документация
## Модели базы данных
Пользователь (User)
python
id: Integer (PK)
username: String (unique)
email: String (unique)
hashed_password: String
is_admin: Boolean (default=False)
Продавец (Seller)
python
id: Integer (PK)
name: String
commission_percent: Float
Товар (Product)
python
id: Integer (PK)
name: String
price: Float
seller_id: Integer (FK -> Seller.id)
Заказ (Order) - упрощенная модель
python
id: Integer (PK)
user_id: Integer (FK -> User.id)
product_id: Integer (FK -> Product.id)
count: Integer (количество товара)
created_at: DateTime (автоматически)
## Система аутентификации и авторизации
## Уровни доступа
1. Гости (неаутентифицированные пользователи)
Просмотр товаров (GET /products, GET /products/{id})

Просмотр продавцов (GET /sellers, GET /sellers/{id})

Регистрация (POST /register)

Вход в систему (POST /login)

2. Аутентифицированные пользователи
Все права гостей

Создание заказов (POST /orders)

Просмотр своих заказов (GET /my-orders) - доступен через веб-интерфейс

Просмотр информации о себе (GET /me)

3. Администраторы
Все права пользователей

Создание, обновление и удаление товаров (POST/PUT/DELETE /products)

Создание продавцов (POST /sellers)

Просмотр всех заказов (GET /orders)

Доступ к админ-панели (/admin-page)

Тестовый администратор
При первом запуске автоматически создаётся администратор:

Email: admin@example.com

Пароль: admin123

## Веб-интерфейс
Для удобства тестирования реализован веб-интерфейс:

/ - Главная страница с навигацией

/login-page - Страница входа в систему

/register-page - Страница регистрации

/me-page - Личный кабинет с отображением JWT токена

/main - Основная страница приложения с описанием API

/admin-page - Админ-панель (только для администраторов)

## Основные эндпоинты API
Аутентификация
Метод	Эндпоинт	Описание	Права доступа
POST	/register	Регистрация нового пользователя	Все
POST	/login	Вход в систему, получение JWT токена	Все
GET	/me	Информация о текущем пользователе	Аутентифицированные
Товары (Products)
Метод	Эндпоинт	Описание	Права доступа
GET	/products	Получить список товаров	Все
GET	/products/{id}	Получить товар по ID	Все
POST	/products	Создать новый товар	Администраторы
PUT	/products/{id}	Обновить товар	Администраторы
DELETE	/products/{id}	Удалить товар	Администраторы
Продавцы (Sellers)
Метод	Эндпоинт	Описание	Права доступа
GET	/sellers	Получить список продавцов	Все
GET	/sellers/{id}	Получить продавца по ID	Все
POST	/sellers	Создать нового продавца	Администраторы
Заказы (Orders)
Метод	Эндпоинт	Описание	Права доступа
GET	/orders	Получить все заказы (панель администратора)	Администраторы
GET	/orders/{id}	Получить заказ по ID	Администраторы
POST	/orders	Создать новый заказ	Аутентифицированные
## Тестирование
Тестовые данные
При первом запуске автоматически создаются:

Администратор: admin@example.com / admin123

5 продавцов с различными комиссиями

Тестовые товары для демонстрации

Примеры запросов
Регистрация пользователя:

bash
curl -X POST "https://marketplace-api.onrender.com/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "testpass123"}'
Вход в систему:

bash
curl -X POST "https://marketplace-api.onrender.com/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}'
Создание заказа (с токеном):

bash
curl -X POST "https://marketplace-api.onrender.com/orders" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ваш_jwt_токен" \
  -d '{"product_id": 1, "count": 2}'
## Технические особенности
Асинхронная архитектура
Используется асинхронное программирование (async/await)

Асинхронные операции с базой данных через SQLAlchemy 2.0

Высокая производительность при одновременных запросах

Безопасность
Пароли хешируются с использованием bcrypt

JWT токены с ограниченным временем жизни

Валидация всех входных данных через Pydantic

Защита от SQL-инъекций через ORM

Масштабируемость
Чистая архитектура с разделением ответственности

Легкость добавления новых эндпоинтов

Возможность замены SQLite на PostgreSQL


## Дополнительные функции:
Веб-интерфейс для тестирования

Система комиссий для продавцов

Автоматическое создание тестовых данных

Развертывание на облачной платформе

## Автор
Новожеев Дмитрий Андреевич
Студент группы ИВТ-201
Курсовая работа по дисциплине "Программирование"