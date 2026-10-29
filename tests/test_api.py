
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Employee Performance Management API"


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_dashboard_summary():
    response = client.get("/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["employees"] == 3000
    assert data["goals"] == 10000
    assert data["check_ins"] == 20000
    assert data["reviews"] == 3000


def test_list_employees():
    response = client.get("/employees?limit=5")
    assert response.status_code == 200
    assert len(response.json()) == 5


def test_get_existing_employee():
    response = client.get("/employees/EMP-000001")
    assert response.status_code == 200
    assert response.json()["employee_id"] == "EMP-000001"


def test_missing_employee_returns_404():
    response = client.get("/employees/EMP-NOT-FOUND")
    assert response.status_code == 404


def test_list_goals():
    response = client.get("/goals?limit=5")
    assert response.status_code == 200
    assert len(response.json()) == 5


def test_get_existing_goal():
    response = client.get("/goals/GOAL-000001")
    assert response.status_code == 200
    data = response.json()
    assert data["goal_id"] == "GOAL-000001"
    assert "key_results" in data
    assert "check_ins" in data


def test_missing_goal_returns_404():
    response = client.get("/goals/GOAL-NOT-FOUND")
    assert response.status_code == 404


def test_list_reviews():
    response = client.get("/reviews?limit=5")
    assert response.status_code == 200
    assert len(response.json()) == 5


def test_missing_review_returns_404():
    response = client.get("/reviews/REV-NOT-FOUND")
    assert response.status_code == 404


def test_list_approvals():
    response = client.get("/approvals?limit=5")
    assert response.status_code == 200
    assert len(response.json()) == 5


def test_invalid_limit_is_rejected():
    response = client.get("/employees?limit=500")
    assert response.status_code == 422