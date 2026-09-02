from decimal import Decimal

from fastapi.testclient import TestClient


def _register_and_login(client: TestClient, email: str) -> dict[str, str]:
    password = "StrongPass123!"
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}


def _create_category(
    client: TestClient,
    headers: dict[str, str],
    name: str,
    category_type: str,
) -> str:
    response = client.post(
        "/api/v1/categories",
        headers=headers,
        json={"name": name, "type": category_type},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_transaction(
    client: TestClient,
    headers: dict[str, str],
    category_id: str,
    amount: str,
    transaction_date: str,
) -> None:
    response = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "description": "Summary transaction",
            "amount": amount,
            "date": transaction_date,
            "category_id": category_id,
        },
    )
    assert response.status_code == 201


def _decimal(value: str) -> Decimal:
    return Decimal(value)


def test_summary_totals_balance_and_totals_by_category(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    salary_id = _create_category(client, auth_headers, "Salary", "income")
    freelance_id = _create_category(client, auth_headers, "Freelance", "income")
    housing_id = _create_category(client, auth_headers, "Housing", "expense")

    _create_transaction(client, auth_headers, salary_id, "3000.10", "2026-01-10")
    _create_transaction(client, auth_headers, salary_id, "250.20", "2026-01-15")
    _create_transaction(client, auth_headers, freelance_id, "499.70", "2026-01-20")
    _create_transaction(client, auth_headers, housing_id, "1200.55", "2026-01-22")

    response = client.get("/api/v1/summary", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    total_income = _decimal(data["total_income"])
    total_expense = _decimal(data["total_expense"])
    balance = _decimal(data["balance"])
    assert total_income == Decimal("3750.00")
    assert total_expense == Decimal("1200.55")
    assert balance == Decimal("2549.45")
    assert balance == total_income - total_expense

    by_category = {item["name"]: item for item in data["by_category"]}
    assert by_category == {
        "Freelance": {"name": "Freelance", "type": "income", "total": "499.70"},
        "Housing": {"name": "Housing", "type": "expense", "total": "1200.55"},
        "Salary": {"name": "Salary", "type": "income", "total": "3250.30"},
    }


def test_summary_can_have_negative_balance(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    income_id = _create_category(client, auth_headers, "Small income", "income")
    expense_id = _create_category(client, auth_headers, "Large expense", "expense")
    _create_transaction(client, auth_headers, income_id, "10.00", "2026-02-01")
    _create_transaction(client, auth_headers, expense_id, "25.50", "2026-02-02")

    data = client.get("/api/v1/summary", headers=auth_headers).json()

    assert data["balance"] == "-15.50"
    assert _decimal(data["balance"]) == (
        _decimal(data["total_income"]) - _decimal(data["total_expense"])
    )


def test_summary_without_transactions_returns_zeros_and_empty_list(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/api/v1/summary", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {
        "total_income": "0.00",
        "total_expense": "0.00",
        "balance": "0.00",
        "by_category": [],
    }


def test_summary_filters_by_start_date(client: TestClient, auth_headers: dict[str, str]) -> None:
    category_id = _create_category(client, auth_headers, "Start filter", "income")
    _create_transaction(client, auth_headers, category_id, "10.00", "2026-03-01")
    _create_transaction(client, auth_headers, category_id, "20.00", "2026-03-15")

    response = client.get("/api/v1/summary?start_date=2026-03-10", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["total_income"] == "20.00"


def test_summary_filters_by_end_date(client: TestClient, auth_headers: dict[str, str]) -> None:
    category_id = _create_category(client, auth_headers, "End filter", "expense")
    _create_transaction(client, auth_headers, category_id, "12.25", "2026-04-05")
    _create_transaction(client, auth_headers, category_id, "30.00", "2026-04-20")

    response = client.get("/api/v1/summary?end_date=2026-04-10", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["total_expense"] == "12.25"


def test_summary_combines_start_and_end_date_filters(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    category_id = _create_category(client, auth_headers, "Date range", "income")
    _create_transaction(client, auth_headers, category_id, "10.00", "2026-05-01")
    _create_transaction(client, auth_headers, category_id, "20.00", "2026-05-10")
    _create_transaction(client, auth_headers, category_id, "30.00", "2026-05-20")
    _create_transaction(client, auth_headers, category_id, "40.00", "2026-05-31")

    response = client.get(
        "/api/v1/summary?start_date=2026-05-10&end_date=2026-05-20",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_income"] == "50.00"
    assert data["by_category"][0]["total"] == "50.00"


def test_summary_only_includes_authenticated_user_transactions(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    own_category_id = _create_category(client, auth_headers, "Own salary", "income")
    _create_transaction(client, auth_headers, own_category_id, "100.00", "2026-06-01")

    other_headers = _register_and_login(client, "summary-other@example.com")
    other_category_id = _create_category(client, other_headers, "Other salary", "income")
    _create_transaction(client, other_headers, other_category_id, "9000.00", "2026-06-01")

    response = client.get("/api/v1/summary", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total_income"] == "100.00"
    assert data["by_category"] == [{"name": "Own salary", "type": "income", "total": "100.00"}]


def test_summary_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/summary")

    assert response.status_code == 401
