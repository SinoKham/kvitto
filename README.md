# KVITTO Payments API

Сервис приёма оплаты курсов через банк.

**Стек:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x, SQLite/PostgreSQL, Alembic, pytest + httpx.

## Установка

```bash
git clone <url>
cd kvitto

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

## Настройка окружения

```bash
cp .env.example .env
```

Содержимое `.env`:

```
DATABASE_URL=sqlite:///./kvitto.db
```

Для PostgreSQL: `postgresql://user:password@localhost:5432/kvitto_db`.

## Миграции

```bash
alembic upgrade head
```

## Запуск

```bash
uvicorn app.main:app --reload
```

Swagger: http://127.0.0.1:8000/docs

При первом запуске создаются тарифы `basic`, `standard`, `premium`.

## Тесты

```bash
python -m pytest tests/ -v
```

Используется in-memory SQLite, реальная БД не затрагивается.

---

## API

### GET /tariffs

Список тарифов.

```json
[
  {"id": 1, "title": "basic", "price": 990000},
  {"id": 2, "title": "standard", "price": 1990000},
  {"id": 3, "title": "premium", "price": 2990000}
]
```

Все суммы — целые числа в копейках.

### POST /payments

Создаёт платёж.

```json
{
  "tariff_id": 2,
  "email": "student@example.com",
  "method": "card",
  "installment_months": null,
  "promo_code": null
}
```

| Поле | Обязательно | Описание |
|---|---|---|
| `tariff_id` | да | ID тарифа |
| `email` | да | email клиента, валидируется |
| `method` | да | `card`, `sbp`, `installment` |
| `installment_months` | только для `installment` | `3`, `6`, `12` |
| `promo_code` | нет | `KVITTO10` — скидка 10%, регистр не важен |

Заголовок `Idempotency-Key` (опционально): повторный запрос с тем же ключом вернёт существующий платёж с кодом `200`.

Ответ `201 Created`:

```json
{
  "id": 1,
  "status": "pending",
  "tariff_id": 2,
  "amount": 1791000,
  "discount": 199000,
  "method": "card",
  "installment_months": null,
  "schedule": null,
  "email": "student@example.com",
  "created_at": "2026-10-08T12:00:00"
}
```

### GET /payments/{id}

Платёж по ID. `404`, если не найден.

### POST /webhooks/bank

Смена статуса платежа банком.

```json
{"payment_id": 1, "status": "succeeded"}
```

Разрешённые переходы:

```
pending   → succeeded
pending   → failed
succeeded → refunded
```

Иначе — `409 {"error": "invalid_transition"}`, статус не меняется.

Успех: `200 {"result": "ok"}`.

---

## Примеры curl

```bash
curl http://127.0.0.1:8000/tariffs

curl -X POST http://127.0.0.1:8000/payments \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: order-123" \
  -d '{"tariff_id": 2, "email": "student@example.com", "method": "card"}'

curl -X POST http://127.0.0.1:8000/payments \
  -H "Content-Type: application/json" \
  -d '{"tariff_id": 2, "email": "student@example.com", "method": "installment", "installment_months": 6, "promo_code": "KVITTO10"}'

curl http://127.0.0.1:8000/payments/1

curl -X POST http://127.0.0.1:8000/webhooks/bank \
  -H "Content-Type: application/json" \
  -d '{"payment_id": 1, "status": "succeeded"}'

curl -X POST http://127.0.0.1:8000/webhooks/bank \
  -H "Content-Type: application/json" \
  -d '{"payment_id": 1, "status": "refunded"}'
```

---

## Структура

```
app/
  main.py       # FastAPI-приложение, эндпоинты
  database.py   # engine, SessionLocal, get_db
  models.py     # Tariff, Payment
  schemas.py    # Pydantic-схемы
tests/
  conftest.py
  test_payments.py
alembic/
```

---

## Бизнес-логика

**Деньги.** Только целые числа в копейках, никаких `float`. `9 900 ₽ = 990 000`.

**Промокод.** `KVITTO10` (регистр не важен) — скидка 10%. Неизвестный — `422`.

**Рассрочка.** Сумма делится на месяцы, остаток распределяется по первым платежам. Пример: `1 791 001 / 3 → [597001, 597000, 597000]`. Сумма графика равна `amount`.

**Идемпотентность.** Заголовок `Idempotency-Key` + `UNIQUE` на колонке `idempotency_key` — защита от дублей, включая конкурентные запросы.

**Статусы.** Разрешены только переходы из таблицы выше. Любой другой — `409`, статус не меняется.