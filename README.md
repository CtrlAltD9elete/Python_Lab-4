# GeoIP FastAPI Service

REST API сервіс для визначення геолокації IP-адреси з реєстрацією користувачів, JWT-авторизацією та збереженням історії запитів у MongoDB.

## Запуск

1. Встановіть залежності:

```powershell
python -m pip install -r requirements.txt
```

2. Запустіть MongoDB локально або в Docker:

```powershell
docker run --name lab4-mongo -p 27017:27017 -d mongo:7
```

3. За потреби задайте змінні середовища:

```powershell
$env:MONGO_URL="mongodb://localhost:27017"
$env:MONGO_DB="lab4_geoip"
$env:JWT_SECRET="replace-this-secret-in-production"
```

4. Запустіть FastAPI:

```powershell
python -m uvicorn main:app --reload
```

Вебінтерфейс: `http://127.0.0.1:8000`

Swagger-документація: `http://127.0.0.1:8000/docs`

## Основні маршрути

- `POST /api/auth/register` - реєстрація користувача.
- `POST /api/auth/login` - вхід за логіном або email.
- `POST /api/auth/token` - OAuth2-сумісний вхід для Swagger.
- `GET /api/me` - поточний користувач.
- `POST /api/geoip` - пошук геолокації IP-адреси.
- `GET /api/history` - історія запитів користувача.
- `GET /api/health` - стан сервісу та MongoDB.

## Приклад запиту

```json
{
  "ip_address": "8.8.8.8"
}
```

Сервіс перевіряє формат IP-адреси, відхиляє локальні та службові адреси, отримує дані з `ipwho.is` і записує результат у колекцію `lookups`.
