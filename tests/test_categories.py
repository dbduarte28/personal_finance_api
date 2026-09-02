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
    name: str = "Salary",
    category_type: str = "income",
) -> Response:
    response = client.post(
        "/api/v1/categories",
        headers=headers,
        json={"name": name, "type": category_type},
    )
    assert response.status_code == 201
    return response


def test_category_crud_happy_path(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    create_response = create_category(client, auth_headers)
    category_id = create_response.json()["id"]

    read_response = client.get(
        f"/api/v1/categories/{category_id}",
        headers=auth_headers,
    )
    assert read_response.status_code == 200
    assert read_response.json()["name"] == "Salary"
    assert read_response.json()["type"] == "income"

    list_response = client.get("/api/v1/categories", headers=auth_headers)
    assert list_response.status_code == 200
    assert [category["id"] for category in list_response.json()] == [category_id]

    update_response = client.patch(
        f"/api/v1/categories/{category_id}",
        headers=auth_headers,
        json={"name": "Groceries", "type": "expense"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Groceries"
    assert update_response.json()["type"] == "expense"

    delete_response = client.delete(
        f"/api/v1/categories/{category_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 204
    assert delete_response.content == b""

    missing_response = client.get(
        f"/api/v1/categories/{category_id}",
        headers=auth_headers,
    )
    assert missing_response.status_code == 404


@pytest.mark.parametrize("category_type", ["income", "expense"])
def test_create_category_types(
    client: TestClient,
    auth_headers: dict[str, str],
    category_type: str,
) -> None:
    response = create_category(
        client,
        auth_headers,
        name=f"Category {category_type}",
        category_type=category_type,
    )

    assert response.json()["type"] == category_type


def test_duplicate_name_for_same_user_returns_409(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    create_category(client, auth_headers, name="Salary")

    response = client.post(
        "/api/v1/categories",
        headers=auth_headers,
        json={"name": "Salary", "type": "expense"},
    )

    assert response.status_code == 409


def test_invalid_category_type_returns_422(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/categories",
        headers=auth_headers,
        json={"name": "Invalid", "type": "transfer"},
    )

    assert response.status_code == 422


def test_different_users_can_use_the_same_category_name(client: TestClient) -> None:
    first_headers = create_user_headers(client, "first@example.com")
    second_headers = create_user_headers(client, "second@example.com")

    first_response = create_category(client, first_headers, name="Groceries")
    second_response = create_category(client, second_headers, name="Groceries")

    assert first_response.json()["id"] != second_response.json()["id"]


def test_category_lists_are_isolated_by_user(client: TestClient) -> None:
    first_headers = create_user_headers(client, "first-list@example.com")
    second_headers = create_user_headers(client, "second-list@example.com")
    first_category = create_category(client, first_headers, name="First category")
    second_category = create_category(client, second_headers, name="Second category")

    first_list = client.get("/api/v1/categories", headers=first_headers)
    second_list = client.get("/api/v1/categories", headers=second_headers)

    assert [item["id"] for item in first_list.json()] == [first_category.json()["id"]]
    assert [item["id"] for item in second_list.json()] == [second_category.json()["id"]]


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_other_users_category_returns_404(
    client: TestClient,
    method: str,
) -> None:
    owner_headers = create_user_headers(client, f"owner-{method}@example.com")
    other_headers = create_user_headers(client, f"other-{method}@example.com")
    category_id = create_category(client, owner_headers).json()["id"]
    request_kwargs = {"json": {"name": "Stolen"}} if method == "patch" else {}

    response = client.request(
        method,
        f"/api/v1/categories/{category_id}",
        headers=other_headers,
        **request_kwargs,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Category not found"}
    owner_response = client.get(
        f"/api/v1/categories/{category_id}",
        headers=owner_headers,
    )
    assert owner_response.status_code == 200


@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        ("post", "/api/v1/categories", {"name": "Salary", "type": "income"}),
        ("get", "/api/v1/categories", None),
        ("get", "/api/v1/categories/1", None),
        ("patch", "/api/v1/categories/1", {"name": "Updated"}),
        ("delete", "/api/v1/categories/1", None),
    ],
)
def test_category_endpoints_require_authentication(
    client: TestClient,
    method: str,
    path: str,
    json_body: dict[str, str] | None,
) -> None:
    response = client.request(method, path, json=json_body)

    assert response.status_code == 401
