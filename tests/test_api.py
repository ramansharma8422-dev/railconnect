from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.database import create_db_and_tables

client = TestClient(app)

def token_for(email, password):
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]

def auth(token):
    return {"Authorization": f"Bearer {token}"}

def test_core_booking_flow():
    # Startup creates the configured admin. Tests use unique account emails.
    email = "passenger-test@example.com"
    client.post("/auth/signup", json={"email": email, "full_name": "Test Passenger", "password": "StrongPass123!"})
    token = token_for(email, "StrongPass123!")
    assert client.get("/users/me", headers=auth(token)).status_code == 200
    assert client.post("/auth/login", json={"email": email, "password": "wrong-password"}).status_code == 401
    assert client.post("/admin/stations", json={"code":"NDLS","name":"New Delhi","city":"Delhi"}).status_code in (201, 409)
    assert client.post("/admin/stations", json={"code":"CNB","name":"Kanpur Central","city":"Kanpur"}).status_code in (201, 409)
    admin_token = token_for("admin@example.com", "ChangeThisAdminPassword123!")
    stations = {s["code"]: s["id"] for s in client.get("/stations").json()}
    # A pre-existing train number is handled as a conflict; use a unique number per run.
    train_response = client.post("/admin/trains", headers=auth(admin_token), json={
        "train_number":"TEST-" + str(date.today().strftime("%y%m%d")),
        "name":"Test Express", "origin_station_id":stations["NDLS"],
        "destination_station_id":stations["CNB"], "departure_time":"08:00",
        "arrival_time":"12:30", "fare":500, "total_seats":2
    })
    if train_response.status_code == 409:
        found = client.get("/trains/search", params={"origin":"NDLS","destination":"CNB","journey_date":str(date.today()+timedelta(days=2))}).json()
        train = next(t for t in found if t["name"] == "Test Express")
        train_id = train["train_id"]
    else:
        assert train_response.status_code == 201, train_response.text
        train_id = train_response.json()["id"]
    journey = str(date.today() + timedelta(days=2))
    booking = client.post("/bookings", headers=auth(token), json={"train_id":train_id,"journey_date":journey,"seats":2})
    assert booking.status_code == 201, booking.text
    pnr = booking.json()["pnr"]
    assert len(pnr) == 10
    sold_out = client.post("/bookings", headers=auth(token), json={"train_id":train_id,"journey_date":journey,"seats":1})
    assert sold_out.status_code == 409
    cancelled = client.post(f"/bookings/{pnr}/cancel", headers=auth(token))
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "CANCELLED"
    repeat_cancel = client.post(f"/bookings/{pnr}/cancel", headers=auth(token))
    assert repeat_cancel.status_code == 409
    logout = client.post("/auth/logout", headers=auth(token))
    assert logout.status_code == 200
    assert client.get("/users/me", headers=auth(token)).status_code == 401

def test_admin_access_control():
    email = "ordinary-user-test@example.com"
    client.post("/auth/signup", json={"email": email, "full_name": "Ordinary User", "password": "StrongPass123!"})
    token = token_for(email, "StrongPass123!")
    response = client.post("/admin/stations", headers=auth(token), json={"code":"FAKE","name":"Fake Station","city":"Fake City"})
    assert response.status_code == 403

def test_password_reset_is_single_use():
    email = "reset-test@example.com"
    client.post("/auth/signup", json={"email": email, "full_name": "Reset User", "password": "OldPassword123!"})
    response = client.post("/auth/forgot-password", json={"email": email})
    assert response.status_code == 200
    reset_token = response.json().get("development_reset_token")
    assert reset_token
    reset = client.post("/auth/reset-password", json={"token": reset_token, "new_password":"NewPassword123!"})
    assert reset.status_code == 200
    assert client.post("/auth/reset-password", json={"token": reset_token, "new_password":"AnotherPassword123!"}).status_code == 400
    assert client.post("/auth/login", json={"email":email,"password":"NewPassword123!"}).status_code == 200
