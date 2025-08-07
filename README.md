# Procurement Automation Backend

## Системные требования
- Python 3.10+
- PostgreSQL/Redis (для production)
- Docker (опционально)

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/ваш_username/ваш_репозиторий.git
cd procurement_automation
```

2. Создайте и активируйте виртуальное окружение:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.\.venv\Scripts\activate   # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Настройте переменные окружения:
```bash
cp .env.example .env
# Отредактируйте .env файл
```

5. Примените миграции:
```bash
python manage.py migrate
```

6. Создайте суперпользователя:
```bash
python manage.py createsuperuser
```

## Запуск

Разработка:
```bash
python manage.py runserver
```

Production (с использованием Gunicorn):
```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

## API Endpoints

- `POST /api/user/register` - Регистрация
- `POST /api/user/login` - Авторизация
- `POST /api/order/confirm` - Подтверждение заказа
- Полный список API: [API_DOCS.md](API_DOCS.md)

## Деплой с Docker

```bash
docker-compose up -d --build
```