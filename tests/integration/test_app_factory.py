def test_saude_endpoint_responde_ok(client):
    resp = client.get("/api/saude")

    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}
