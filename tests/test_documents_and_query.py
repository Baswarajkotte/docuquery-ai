LEAVE_POLICY = b"""Leave Policy 2026.
Every full-time employee gets 24 days of paid annual leave per year.
Unused annual leave of up to 10 days can be carried forward to the next year.
Sick leave is 12 days per year and needs a medical certificate after 2 days.
Work from home is allowed two days a week with manager approval.
"""

EXPENSE_POLICY = b"""Travel and Expense Policy.
Employees can claim hotel stays up to 4000 rupees per night in metro cities.
Claims must be submitted within 30 days with receipts attached.
"""


def upload(client, headers, name, data, content_type="text/plain"):
    return client.post("/documents", headers=headers, files={"file": (name, data, content_type)})


def test_upload_list_and_delete(client, auth_headers):
    res = upload(client, auth_headers, "leave.txt", LEAVE_POLICY)
    assert res.status_code == 201
    doc = res.json()
    assert doc["filename"] == "leave.txt"
    assert doc["chunk_count"] >= 1
    assert doc["word_count"] > 30

    listed = client.get("/documents", headers=auth_headers).json()
    assert [d["id"] for d in listed] == [doc["id"]]

    assert client.delete(f"/documents/{doc['id']}", headers=auth_headers).status_code == 204
    assert client.get("/documents", headers=auth_headers).json() == []


def test_rejects_unsupported_and_empty_files(client, auth_headers):
    res = upload(client, auth_headers, "photo.png", b"\x89PNG", "image/png")
    assert res.status_code == 422
    res = upload(client, auth_headers, "empty.txt", b"   \n  ")
    assert res.status_code == 422


def test_query_returns_cited_answer_from_right_document(client, auth_headers):
    upload(client, auth_headers, "leave.txt", LEAVE_POLICY)
    upload(client, auth_headers, "expenses.txt", EXPENSE_POLICY)

    res = client.post(
        "/query", headers=auth_headers, json={"question": "How many days of sick leave do I get?"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["mode"] == "extractive"
    assert "12 days" in body["answer"]
    assert body["sources"][0]["filename"] == "leave.txt"
    assert body["sources"][0]["page"] == 1


def test_query_can_be_limited_to_documents(client, auth_headers):
    leave = upload(client, auth_headers, "leave.txt", LEAVE_POLICY).json()
    expense = upload(client, auth_headers, "expenses.txt", EXPENSE_POLICY).json()

    res = client.post(
        "/query",
        headers=auth_headers,
        json={"question": "hotel limit per night", "document_ids": [leave["id"]]},
    )
    assert all(s["document_id"] == leave["id"] for s in res.json()["sources"])

    res = client.post(
        "/query",
        headers=auth_headers,
        json={"question": "hotel limit per night", "document_ids": [expense["id"]]},
    )
    assert "4000" in res.json()["answer"]


def test_users_cannot_see_each_others_documents(client, auth_headers, other_headers):
    doc = upload(client, auth_headers, "leave.txt", LEAVE_POLICY).json()

    assert client.get(f"/documents/{doc['id']}", headers=other_headers).status_code == 404
    assert client.delete(f"/documents/{doc['id']}", headers=other_headers).status_code == 404
    res = client.post("/query", headers=other_headers, json={"question": "sick leave days"})
    assert res.json()["sources"] == []


def test_history_records_questions(client, auth_headers):
    upload(client, auth_headers, "leave.txt", LEAVE_POLICY)
    client.post("/query", headers=auth_headers, json={"question": "work from home rules"})
    history = client.get("/history", headers=auth_headers).json()
    assert len(history) == 1
    assert history[0]["question"] == "work from home rules"
