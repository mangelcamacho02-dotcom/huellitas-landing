"""Pruebas: python -m pytest -q   (usa una base SQLite temporal)."""
import os
import tempfile
from datetime import date

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ.pop("MCP_PATH_SECRET", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import campana, config  # noqa: E402
from app.main import app  # noqa: E402
from app.seed_data import LEADS_FICTICIOS, sembrar  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # arranca el lifespan -> auto-seed
        yield c


def form(**kw):
    base = {"nombre_dueno": "Ana Prueba", "whatsapp": "8888-1234", "mascota": "Pelusa",
            "tamano": "pequeno", "dia": "2026-12-03"}
    base.update(kw)
    return base


def test_health(client):
    assert client.get("/health").json() == {"ok": True}


def test_auto_seed_e_idempotencia(client):
    assert len(campana.listar(limite=50)) == len(LEADS_FICTICIOS)
    assert sembrar() == 0


def test_landing(client):
    html = client.get("/").text
    assert "<s>₡25.000</s>" in html and "₡14.900" in html
    assert "2026-12-06" not in html  # domingo
    assert "Negocio y datos ficticios" in html


def test_whatsapp():
    assert campana.normalizar_whatsapp("+506 8888-1234") == "88881234"
    assert campana.normalizar_whatsapp("506-8888-1234") == "88881234"
    assert campana.normalizar_whatsapp("8888 1234") == "88881234"
    assert campana.normalizar_whatsapp("1234567") is None
    assert campana.normalizar_whatsapp("8888abcd") is None
    assert campana.enmascarar_whatsapp("88881234") == "8***-**34"


def test_reserva_y_cupos(client):
    antes = {d["fecha_iso"]: d["libres"] for d in campana.calendario()}["2026-12-03"]
    r = client.post("/reservar", data=form(), follow_redirects=False)
    assert r.status_code == 303
    despues = {d["fecha_iso"]: d["libres"] for d in campana.calendario()}["2026-12-03"]
    assert despues == antes - 1


def test_dia_lleno(client):
    for i in range(10):
        client.post("/reservar", data=form(whatsapp=f"7000000{i}", mascota=f"P{i}", dia="2026-12-09"))
    r = client.post("/reservar", data=form(whatsapp="60000000", dia="2026-12-09"))
    assert r.status_code == 400 and "llenar" in r.text


def test_honeypot_no_guarda(client):
    n = len(campana.listar(limite=50, dia=date(2026, 12, 10)))
    r = client.post("/reservar", data=form(dia="2026-12-10", sitio_web="x"), follow_redirects=False)
    assert r.status_code == 303
    assert len(campana.listar(limite=50, dia=date(2026, 12, 10))) == n


def test_fecha_limite(client, monkeypatch):
    monkeypatch.setattr(config, "hoy", lambda: date(2026, 12, 19))
    r = client.post("/reservar", data=form(dia="2026-12-19", whatsapp="61112222"))
    assert r.status_code == 400 and "cerraron" in r.text


def test_dia_pasado(client, monkeypatch):
    monkeypatch.setattr(config, "hoy", lambda: date(2026, 12, 8))
    r = client.post("/reservar", data=form(dia="2026-12-07", whatsapp="61113333"))
    assert r.status_code == 400 and "ya pasó" in r.text


def test_mcp_montado(client):
    r = client.post("/mcp/", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}},
        headers={"Accept": "application/json, text/event-stream"})
    assert r.status_code == 200 and "Huellitas Vet" in r.text
