import pytest

def test_get_tariffs(client):
    response=client.get("/tariffs")
    assert response.status_code==200
    assert len(response.json()) == 3

def test_create_payment(client):
    response=client.post("/payments", json={
        "tariff_id":1,
        "email": "test@test.com",
        "method": "card"
    })
    assert response.status_code==201
    data = response.json()
    assert data["status"] == "pending"
    assert data["amount"] == 990000

def test_promo(client):
    response=client.post("/payments", json={
        "tariff_id":1,
        "email": "test@test.com",
        "method": "card",
        "promo_code":"KVITTO10"
    })
    assert response.status_code==201
    data = response.json()
    assert data["amount"]==891000
    assert data["discount"] ==99000

def test_wrong_promo(client):
    response=client.post("/payments", json={
        "tariff_id":1,
        "email": "test@test.com",
        "method": "card",
        "promo_code":"abc"
    })
    assert response.status_code==422
    assert "Unknown promo code" in response.json()["detail"]

@pytest.mark.parametrize("months", [3, 6, 12])
def test_installment_schedule(client, months):
    response = client.post("/payments", json={
        "tariff_id": 3,
        "email": "test@test.com",
        "method": "installment",
        "installment_months": months
    })
    assert response.status_code == 201
    data = response.json()
    schedule = data["schedule"]
    assert len(schedule)==months
    assert sum(schedule) == data["amount"]    
    assert schedule[0] >= schedule[-1]   

def test_idempotency(client):
    response1 = client.post("/payments", json={
        "tariff_id": 1,
        "email": "test@test.com",
        "method": "card"
    }, headers={"Idempotency-Key": "test-key-1"})
    assert response1.status_code == 201
    id1 = response1.json()["id"]
    
    response2 = client.post("/payments", json={
        "tariff_id": 1,
        "email": "test@test.com",
        "method": "card"
    }, headers={"Idempotency-Key": "test-key-1"})
    assert response2.status_code == 200
    id2 = response2.json()["id"]
    assert id1 == id2   

def test_invalid_transition(client):
    create = client.post("/payments", json={
        "tariff_id": 1,
        "email": "test@test.com",
        "method": "card"
        })
    assert create.status_code==201
    payment_id = create.json()["id"]
    assert create.json()["status"] == "pending"
    response = client.post("/webhooks/bank", json={
        "payment_id": payment_id,
        "status": "refunded"
    })
    assert response.status_code == 409
    assert response.json() == {"error": "invalid_transition"}
    check = client.get(f"/payments/{payment_id}")
    assert check.json()["status"] == "pending"

def test_get_nonexistent_payment(client):
    response = client.get("/payments/99999")
    assert response.status_code == 404