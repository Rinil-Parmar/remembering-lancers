def test_get_obituaries_returns_latest_distinct_alumni_records(client):
    response = client.get("/get_obituaries")

    assert response.status_code == 200
    payload = response.get_json()
    names = {record["name"] for record in payload}
    assert "Test Alumni" in names
    assert "Second Alumni" in names
    assert "Non Alumni" not in names


def test_search_obituaries_filters_by_query_and_excludes_non_alumni(client):
    response = client.get("/search_obituaries?query=University")

    assert response.status_code == 200
    payload = response.get_json()
    assert [record["name"] for record in payload] == ["Test Alumni"]


def test_search_obituaries_filters_by_city(client):
    response = client.get("/search_obituaries?city=Toronto")

    assert response.status_code == 200
    payload = response.get_json()
    assert [record["name"] for record in payload] == ["Second Alumni"]


def test_publications_grouped_by_year(client):
    response = client.get("/api/publications/grouped-by-year")

    assert response.status_code == 200
    payload = response.get_json()
    assert "2026" in payload
    assert "2024" in payload
    assert "Before 2022" in payload
    assert any(record["name"] == "Test Alumni" for record in payload["2026"])
