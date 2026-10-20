def test_raiz_redireciona_para_dashboard(client):
    resp = client.get("/")
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/dashboard"


def test_login_renderiza_formulario(client):
    resp = client.get("/login")

    assert resp.status_code == 200
    assert b"form-login" in resp.data
    assert b"supabase-js" in resp.data


def test_dashboard_renderiza_pagina(client):
    resp = client.get("/dashboard")

    assert resp.status_code == 200
    assert b"seletor-municipio" in resp.data
    assert b"grafico-linha" in resp.data
