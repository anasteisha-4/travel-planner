from decimal import Decimal


class TestCreateExpense:
    def test_create_success(self, client, auth_headers, trip_data):
        trip_resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        trip_id = trip_resp.json()["id"]

        expense_data = {
            "amount": "25.50",
            "currency": "EUR",
            "category": "food",
            "description": "Ужин в ресторане",
            "expense_date": "2026-06-05",
        }
        response = client.post(f"/api/trips/{trip_id}/expenses", json=expense_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert Decimal(data["amount"]) == Decimal("25.50")
        assert data["currency"] == "EUR"
        assert data["category"] == "food"
        assert data["description"] == "Ужин в ресторане"
        assert data["expense_date"] == "2026-06-05"
        assert "id" in data

    def test_create_minimal(self, client, auth_headers, trip_data):
        trip_resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        trip_id = trip_resp.json()["id"]

        expense_data = {"amount": "100", "currency": "RUB", "category": "transport"}
        response = client.post(f"/api/trips/{trip_id}/expenses", json=expense_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["description"] is None
        assert data["expense_date"] is None

    def test_create_airfare_category(self, client, auth_headers, trip_data):
        trip_resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        trip_id = trip_resp.json()["id"]

        expense_data = {"amount": "300", "currency": "EUR", "category": "travel_to_destination"}
        response = client.post(f"/api/trips/{trip_id}/expenses", json=expense_data, headers=auth_headers)

        assert response.status_code == 201
        data = response.json()
        assert data["category"] == "travel_to_destination"

    def test_create_no_auth(self, client, trip_data):
        response = client.post(
            "/api/trips/00000000-0000-0000-0000-000000000000/expenses",
            json={
                "amount": "10",
                "currency": "RUB",
                "category": "food",
            },
        )
        assert response.status_code == 401

    def test_create_other_users_trip(self, client, auth_headers, other_user_headers, trip_data):
        trip_resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        trip_id = trip_resp.json()["id"]

        expense_data = {"amount": "10", "currency": "RUB", "category": "food"}
        response = client.post(f"/api/trips/{trip_id}/expenses", json=expense_data, headers=other_user_headers)
        assert response.status_code == 404


class TestListExpenses:
    def test_list_empty(self, client, auth_headers, trip_data):
        trip_resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        trip_id = trip_resp.json()["id"]

        response = client.get(f"/api/trips/{trip_id}/expenses", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_with_expenses(self, client, auth_headers, trip_data):
        trip_resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        trip_id = trip_resp.json()["id"]

        client.post(
            f"/api/trips/{trip_id}/expenses",
            json={
                "amount": "25",
                "currency": "EUR",
                "category": "food",
                "expense_date": "2026-06-05",
            },
            headers=auth_headers,
        )
        client.post(
            f"/api/trips/{trip_id}/expenses",
            json={
                "amount": "50",
                "currency": "EUR",
                "category": "transport",
                "expense_date": "2026-06-06",
            },
            headers=auth_headers,
        )

        response = client.get(f"/api/trips/{trip_id}/expenses", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_filter_by_category(self, client, auth_headers, trip_data):
        trip_resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        trip_id = trip_resp.json()["id"]

        client.post(
            f"/api/trips/{trip_id}/expenses",
            json={
                "amount": "25",
                "currency": "EUR",
                "category": "food",
            },
            headers=auth_headers,
        )
        client.post(
            f"/api/trips/{trip_id}/expenses",
            json={
                "amount": "50",
                "currency": "EUR",
                "category": "transport",
            },
            headers=auth_headers,
        )

        response = client.get(f"/api/trips/{trip_id}/expenses?category=food", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["category"] == "food"

    def test_filter_by_date_range(self, client, auth_headers, trip_data):
        trip_resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        trip_id = trip_resp.json()["id"]

        client.post(
            f"/api/trips/{trip_id}/expenses",
            json={
                "amount": "25",
                "currency": "EUR",
                "category": "food",
                "expense_date": "2026-06-01",
            },
            headers=auth_headers,
        )
        client.post(
            f"/api/trips/{trip_id}/expenses",
            json={
                "amount": "50",
                "currency": "EUR",
                "category": "transport",
                "expense_date": "2026-06-10",
            },
            headers=auth_headers,
        )

        response = client.get(
            f"/api/trips/{trip_id}/expenses?date_from=2026-06-05&date_to=2026-06-15",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestUpdateExpense:
    def test_update_amount(self, client, auth_headers, trip_data):
        trip_resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        trip_id = trip_resp.json()["id"]

        exp_resp = client.post(
            f"/api/trips/{trip_id}/expenses",
            json={
                "amount": "25",
                "currency": "EUR",
                "category": "food",
            },
            headers=auth_headers,
        )
        expense_id = exp_resp.json()["id"]

        response = client.put(f"/api/expenses/{expense_id}", json={"amount": "30"}, headers=auth_headers)
        assert response.status_code == 200
        assert Decimal(response.json()["amount"]) == Decimal("30")

    def test_update_not_found(self, client, auth_headers):
        response = client.put(
            "/api/expenses/00000000-0000-0000-0000-000000000000",
            json={"amount": "10"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_update_other_users_expense(self, client, auth_headers, other_user_headers, trip_data):
        trip_resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        trip_id = trip_resp.json()["id"]

        exp_resp = client.post(
            f"/api/trips/{trip_id}/expenses",
            json={
                "amount": "25",
                "currency": "EUR",
                "category": "food",
            },
            headers=auth_headers,
        )
        expense_id = exp_resp.json()["id"]

        response = client.put(f"/api/expenses/{expense_id}", json={"amount": "99"}, headers=other_user_headers)
        assert response.status_code == 404


class TestDeleteExpense:
    def test_delete_success(self, client, auth_headers, trip_data):
        trip_resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        trip_id = trip_resp.json()["id"]

        exp_resp = client.post(
            f"/api/trips/{trip_id}/expenses",
            json={
                "amount": "25",
                "currency": "EUR",
                "category": "food",
            },
            headers=auth_headers,
        )
        expense_id = exp_resp.json()["id"]

        response = client.delete(f"/api/expenses/{expense_id}", headers=auth_headers)
        assert response.status_code == 204

        response = client.get(f"/api/trips/{trip_id}/expenses", headers=auth_headers)
        assert len(response.json()) == 0

    def test_delete_not_found(self, client, auth_headers):
        response = client.delete("/api/expenses/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_other_users_expense(self, client, auth_headers, other_user_headers, trip_data):
        trip_resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        trip_id = trip_resp.json()["id"]

        exp_resp = client.post(
            f"/api/trips/{trip_id}/expenses",
            json={
                "amount": "25",
                "currency": "EUR",
                "category": "food",
            },
            headers=auth_headers,
        )
        expense_id = exp_resp.json()["id"]

        response = client.delete(f"/api/expenses/{expense_id}", headers=other_user_headers)
        assert response.status_code == 404

        response = client.get(f"/api/trips/{trip_id}/expenses", headers=auth_headers)
        assert len(response.json()) == 1


class TestExpenseSummary:
    def test_summary_empty(self, client, auth_headers, trip_data):
        trip_resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        trip_id = trip_resp.json()["id"]

        response = client.get(f"/api/trips/{trip_id}/expenses/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["total"]) == Decimal("0")
        assert data["by_category"] == {}

    def test_summary_with_expenses(self, client, auth_headers, trip_data):
        trip_resp = client.post("/api/trips/", json=trip_data, headers=auth_headers)
        trip_id = trip_resp.json()["id"]

        client.post(
            f"/api/trips/{trip_id}/expenses",
            json={
                "amount": "120",
                "currency": "EUR",
                "category": "food",
            },
            headers=auth_headers,
        )
        client.post(
            f"/api/trips/{trip_id}/expenses",
            json={
                "amount": "60",
                "currency": "EUR",
                "category": "transport",
            },
            headers=auth_headers,
        )
        client.post(
            f"/api/trips/{trip_id}/expenses",
            json={
                "amount": "300",
                "currency": "EUR",
                "category": "housing",
            },
            headers=auth_headers,
        )
        client.post(
            f"/api/trips/{trip_id}/expenses",
            json={
                "amount": "30",
                "currency": "EUR",
                "category": "food",
            },
            headers=auth_headers,
        )

        response = client.get(f"/api/trips/{trip_id}/expenses/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["total"]) == Decimal("510")
        assert Decimal(data["by_category"]["food"]) == Decimal("150")
        assert Decimal(data["by_category"]["transport"]) == Decimal("60")
        assert Decimal(data["by_category"]["housing"]) == Decimal("300")
