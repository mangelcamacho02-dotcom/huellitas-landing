"""App FastAPI: landing de temporada + servidor MCP montado en la misma app."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import campana, config, db
from .mcp_server import mcp
from .seed_data import sembrar_si_vacia

log = logging.getLogger("huellitas")
BASE = Path(__file__).resolve().parent

# App MCP (transporte HTTP streamable). path="/" porque la montamos en un prefijo.
mcp_app = mcp.http_app(path="/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    if config.AUTO_SEED:
        n = sembrar_si_vacia()
        if n:
            log.warning("Tabla leads vacía: se cargaron %s leads ficticios.", n)
    # El lifespan del MCP es obligatorio para que funcione su gestor de sesiones.
    async with mcp_app.lifespan(app):
        yield


app = FastAPI(title="Huellitas Vet — Baño Navideño", lifespan=lifespan, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
app.mount(config.mcp_path(), mcp_app)

templates = Jinja2Templates(directory=BASE / "templates")
templates.env.globals.update(
    colones=config.colones,
    fecha_larga=config.fecha_larga,
    cfg=config,
)


def _contexto(request: Request, errores: dict | None = None, valores: dict | None = None) -> dict:
    dias = config.dias_campana()
    est = campana.estado()
    return {
        "request": request,
        "dias": campana.calendario(),
        "estado": est,
        "primer_dia": dias[0],
        "ultimo_dia": dias[-1],
        "limite_iso": config.limite_dt().isoformat(),
        "abiertas": campana.reservas_abiertas(),
        "errores": errores or {},
        "v": valores or {},
    }


@app.get("/", response_class=HTMLResponse)
def inicio(request: Request):
    return templates.TemplateResponse(request, "index.html", _contexto(request))


@app.post("/reservar", response_class=HTMLResponse)
def reservar(
    request: Request,
    nombre_dueno: str = Form(""),
    whatsapp: str = Form(""),
    mascota: str = Form(""),
    tamano: str = Form(""),
    dia: str = Form(""),
    sitio_web: str = Form(""),  # honeypot: los humanos no lo ven
):
    valores = {"nombre_dueno": nombre_dueno, "whatsapp": whatsapp, "mascota": mascota, "tamano": tamano, "dia": dia}

    # Anti-spam: si un bot llenó el campo oculto, fingimos éxito sin guardar nada.
    if sitio_web.strip():
        return RedirectResponse("/gracias", status_code=303)

    errores: dict[str, str] = {}
    nombre = " ".join(nombre_dueno.split())
    nombre_mascota = " ".join(mascota.split())

    if not campana.reservas_abiertas():
        errores["general"] = "Las reservas cerraron el 18 de diciembre. ¡Gracias por tu interés!"

    if not (2 <= len(nombre) <= 80):
        errores["nombre_dueno"] = "Escribe tu nombre (entre 2 y 80 caracteres)."
    wa = campana.normalizar_whatsapp(whatsapp)
    if not wa:
        errores["whatsapp"] = "Ingresa un WhatsApp de Costa Rica de 8 dígitos (ej. 8888-8888 o +506 8888 8888)."
    elif wa[0] not in "5678":
        errores["whatsapp"] = "Ese número no parece un celular de Costa Rica."
    if not (1 <= len(nombre_mascota) <= 60):
        errores["mascota"] = "Cuéntanos cómo se llama tu mascota."
    if tamano not in config.TAMANOS:
        errores["tamano"] = "Elige el tamaño de tu mascota."

    dia_fecha: date | None = None
    try:
        dia_fecha = date.fromisoformat(dia)
    except ValueError:
        errores["dia"] = "Elige un día para el baño."
    if dia_fecha and "dia" not in errores and "general" not in errores:
        if dia_fecha not in config.dias_campana():
            errores["dia"] = "Ese día no es parte de la campaña."
        elif not campana.dia_reservable(dia_fecha):
            errores["dia"] = "Ese día ya pasó. Elige otro, por favor."

    if not errores:
        try:
            db.crear_reserva(nombre, wa, nombre_mascota, tamano, dia_fecha)
        except db.DiaLleno:
            errores["dia"] = "¡Uy! Ese día se acaba de llenar. Elige otro, por favor."
        except db.Duplicado:
            errores["dia"] = f"{nombre_mascota} ya tiene reserva ese día con este WhatsApp."

    if errores:
        return templates.TemplateResponse(
            request, "index.html", _contexto(request, errores, valores), status_code=400
        )

    qs = urlencode({"mascota": nombre_mascota, "dia": dia_fecha.isoformat()})
    return RedirectResponse(f"/gracias?{qs}", status_code=303)


@app.get("/gracias", response_class=HTMLResponse)
def gracias(request: Request, mascota: str = "", dia: str = ""):
    try:
        d = date.fromisoformat(dia) if dia else None
    except ValueError:
        d = None
    return templates.TemplateResponse(
        request, "gracias.html", {"request": request, "mascota": mascota[:60], "dia": d}
    )


@app.get("/health")
def health():
    return JSONResponse({"ok": True})
