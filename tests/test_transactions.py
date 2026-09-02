from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from httpx import Response


def create_user_headers(
    client: TestClient,
    email: str,
    password: str = "secure-password",
) -> dict[str, str]:
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


def create_category(
    client: TestClient,
    headers: dict[str, str],
    name: str,
    category_type: str,
) -> int:
    response = client.post(
        "/api/v1/categories",
        headers=headers,
        json={"name": name, "type": category_type},
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_transaction(
    client: TestClient,
    headers: dict[str, str],
    category_id: int,
    amount: str = "123.45",
    transaction_date: str = "2026-01-15",
    description: str | None = "Test transaction",
) -> Response:
    response = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "category_id": category_id,
            "amount": amount,
            "description": description,
            "date": transaction_date,
        },
    )
    assert response.status_code == 201
    return response


def test_transaction_crud_happy_path(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    income_id = create_category(client, auth_headers, "Salary", "income")
    expense_id = create_category(client, auth_headers, "Groceries", "expense")
    create_response = create_transaction(client, auth_headers, income_id)
    transaction_id = create_response.json()["id"]

    assert Decimal(create_response.json()["amount"]) == Decimal("123.45")
    assert create_response.json()["category"]["type"] == "income"

    read_response = client.get(
        f"/api/v1/transactions/{transaction_id}",
        headers=auth_headers,
    )
    assert read_response.status_code == 200
    assert read_response.json()["description"] == "Test transaction"

    list_response = client.get("/api/v1/transactions", headers=auth_headers)
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [transaction_id]

    update_response = client.patch(
        f"/api/v1/transactions/{transaction_id}",
        headers=auth_headers,
        json={
            "category_id": expense_id,
            "amount": "99.90",
            "description": "Updated transaction",
            "date": "2026-01-20",
        },
    )
    assert update_response.status_code == 200
    assert Decimal(update_response.json()["amount"]) == Decimal("99.90")
    assert update_response.json()["category"]["type"] == "expense"

    delete_response = client.delete(
        f"/api/v1/transactions/{transaction_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 204
    assert delete_response.content == b""

    missing_response = client.get(
        f"/api/v1/transactions/{transaction_id}",
        headers=auth_headers,
    )
    assert missing_response.status_code == 404


def test_amount_preserves_two_decimal_places(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    category_id = create_category(client, auth_headers, "Salary", "income")

    response = create_transaction(
        client,
        auth_headers,
        category_id,
        amount="12.30",
    )

    assert response.json()["amount"] == "12.30"
    assert Decimal(response.json()["amount"]) == Decimal("12.30")


@pytest.mark.parametrize("amount", ["0", "-0.01"])
def test_zero_or_negative_amount_returns_422(
    client: TestClient,
    auth_headers: dict[str, str],
    amount: str,
) -> None:
    category_id = create_category(client, auth_headers, "Salary", "income")

    response = client.post(
        "/api/v1/transactions",
        headers=auth_headers,
        json={"category_id": category_id, "amount": amount, "date": "2026-01-15"},
    )

    assert response.status_code == 422


def test_amount_with_more_than_two_decimal_places_returns_422(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    category_id = create_category(client, auth_headers, "Salary", "income")

    response = client.post(
        "/api/v1/transactions",
        headers=auth_headers,
        json={"category_id": category_id, "amount": "1.234", "date": "2026-01-15"},
    )

    assert response.status_code == 422


def test_nonexistent_category_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/transactions",
        headers=auth_headers,
        json={"category_id": 999999, "amount": "10.00", "date": "2026-01-15"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Category not found"}


def test_other_users_category_returns_404(client: TestClient) -> None:
    owner_headers = create_user_headers(client, "category-owner@example.com")
    other_headers = create_user_headers(client, "category-other@example.com")
    category_id = create_category(client, owner_headers, "Private", "expense")

    response = client.post(
        "/api/v1/transactions",
        headers=other_headers,
        json={"category_id": category_id, "amount": "10.00", "date": "2026-01-15"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Category not found"}


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_other_users_transaction_returns_404(
    client: TestClient,
    method: str,
) -> None:
    owner_headers = create_user_headers(client, f"transaction-owner-{method}@example.com")
    other_headers = create_user_headers(client, f"transaction-other-{method}@example.com")
    category_id = create_category(client, owner_headers, "Private", "expense")
    transaction_id = create_transaction(client, owner_headers, category_id).json()["id"]
    request_kwargs = {"json": {"amount": "50.00"}} if method == "patch" else {}

    response = client.request(
        method,
        f"/api/v1/transactions/{transaction_id}",
        headers=other_headers,
        **request_kwargs,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Transaction not found"}
    owner_response = client.get(
        f"/api/v1/transactions/{transaction_id}",
        headers=owner_headers,
    )
    assert owner_response.status_code == 200


def test_transaction_lists_are_isolated_by_user(client: TestClient) -> None:
    first_headers = create_user_headers(client, "first-transactions@example.com")
    second_headers = create_user_headers(client, "second-transactions@example.com")
    first_category = create_category(client, first_headers, "First", "income")
    second_category = create_category(client, second_headers, "Second", "expense")
    first_transaction = create_transaction(client, first_headers, first_category)
    second_transaction = create_transaction(client, second_headers, second_category)

    first_list = client.get("/api/v1/transactions", headers=first_headers)
    second_list = client.get("/api/v1/transactions", headers=second_headers)

    assert [item["id"] for item in first_list.json()] == [first_transaction.json()["id"]]
    assert [item["id"] for item in second_list.json()] == [second_transaction.json()["id"]]


def test_filter_by_date_range_includes_boundaries(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    category_id = create_category(client, auth_headers, "Salary", "income")
    before = create_transaction(
        client, auth_headers, category_id, transaction_date="2026-01-01"
    )
    start = create_transaction(
        client, auth_headers, category_id, transaction_date="2026-01-10"
    )
    end = create_transaction(
        client, auth_headers, category_id, transaction_date="2026-01-20"
    )
    after = create_transaction(
        client, auth_headers, category_id, transaction_date="2026-01-21"
    )

    response = client.get(
        "/api/v1/transactions?start_date=2026-01-10&end_date=2026-01-20",
        headers=auth_headers,
    )

    assert [item["id"] for item in response.json()] == [
        end.json()["id"],
        start.json()["id"],
    ]
    returned_ids = {item["id"] for item in response.json()}
    assert before.json()["id"] not in returned_ids
    assert after.json()["id"] not in returned_ids


def test_filter_by_category(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    salary_id = create_category(client, auth_headers, "Salary", "income")
    groceries_id = create_category(client, auth_headers, "Groceries", "expense")
    salary_transaction = create_transaction(client, auth_headers, salary_id)
    create_transaction(client, auth_headers, groceries_id)

    response = client.get(
        f"/api/v1/transactions?category_id={salary_id}",
        headers=auth_headers,
    )

    assert [item["id"] for item in response.json()] == [
        salary_transaction.json()["id"]
    ]


@pytest.mark.parametrize(
    ("transaction_type", "expected_name"),
    [("income", "Salary"), ("expense", "Groceries")],
)
def test_filter_by_category_type(
    client: TestClient,
    auth_headers: dict[str, str],
    transaction_type: str,
    expected_name: str,
) -> None:
    salary_id = create_category(client, auth_headers, "Salary", "income")
    groceries_id = create_category(client, auth_headers, "Groceries", "expense")
    create_transaction(client, auth_headers, salary_id)
    create_transaction(client, auth_headers, groceries_id)

    response = client.get(
        f"/api/v1/transactions?type={transaction_type}",
        headers=auth_headers,
    )

    assert len(response.json()) == 1
    assert response.json()[0]["category"]["name"] == expected_name


def test_limit_and_offset_paginate_without_overlap(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    category_id = create_category(client, auth_headers, "Salary", "income")
    created_ids = [
        create_transaction(
            client,
            auth_headers,
            category_id,
            transaction_date=f"2026-01-{day:02d}",
        ).json()["id"]
        for day in range(1, 6)
    ]

    first_page = client.get(
        "/api/v1/transactions?limit=2&offset=0",
        headers=auth_headers,
    ).json()
    second_page = client.get(
        "/api/v1/transactions?limit=2&offset=2",
        headers=auth_headers,
    ).json()
    third_page = client.get(
        "/api/v1/transactions?limit=2&offset=4",
        headers=auth_headers,
    ).json()
    paginated_ids = [item["id"] for item in first_page + second_page + third_page]

    assert paginated_ids == list(reversed(created_ids))
    assert len(paginated_ids) == len(set(paginated_ids))


def test_update_to_other_users_category_returns_404(client: TestClient) -> None:
    owner_headers = create_user_headers(client, "update-owner@example.com")
    other_headers = create_user_headers(client, "update-other@example.com")
    owner_category = create_category(client, owner_headers, "Owner", "income")
    other_category = create_category(client, other_headers, "Other", "expense")
    transaction_id = create_transaction(
        client,
        owner_headers,
        owner_category,
    ).json()["id"]

    response = client.patch(
        f"/api/v1/transactions/{transaction_id}",
        headers=owner_headers,
        json={"category_id": other_category},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Category not found"}


def test_category_with_transactions_cannot_be_deleted(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    category_id = create_category(client, auth_headers, "Salary", "income")
    create_transaction(client, auth_headers, category_id)

    response = client.delete(
        f"/api/v1/categories/{category_id}",
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Category cannot be deleted because it has transactions"
    }


@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        (
            "post",
            "/api/v1/transactions",
            {"category_id": 1, "amount": "10.00", "date": "2026-01-15"},
        ),
        ("get", "/api/v1/transactions", None),
        ("get", "/api/v1/transactions/1", None),
        ("patch", "/api/v1/transactions/1", {"amount": "10.00"}),
        ("delete", "/api/v1/transactions/1", None),
    ],
)
def test_transaction_endpoints_require_authentication(
    client: TestClient,
    method: str,
    path: str,
    json_body: dict[str, object] | None,
) -> None:
    response = client.request(method, path, json=json_body)

    assert response.status_code == 401
