"""Configuración: datos de la campaña y variables de entorno.

Ninguna clave vive en el código. Todo lo sensible se lee del entorno.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

# --- Variables de entorno -------------------------------------------------

# Railway inyecta DATABASE_URL al referenciar el servicio Postgres.
# Si no existe, se usa SQLite local (leads.db).
DATABASE_URL: str = os.getenv("DATABASE_URL", "").strip()

# Si existe, el MCP se monta en /mcp-<secreto> en vez de /mcp.
MCP_PATH_SECRET: str = os.getenv("MCP_PATH_SECRET", "").strip()

# Carga automática de leads ficticios si la tabla está vacía (por defecto: sí).
AUTO_SEED: bool = os.getenv("AUTO_SEED", "true").strip().lower() not in {"0", "false", "no", "off"}

# URL pública de la landing (opcional; solo se usa en las respuestas del MCP).
PUBLIC_URL: str = os.getenv("PUBLIC_URL", "").strip().rstrip("/")

# --- Datos del negocio y la campaña --------------------------------------

TZ = ZoneInfo("America/Costa_Rica")

NEGOCIO = "Huellitas Vet"
NEGOCIO_DESCRIPCION = "Veterinaria y estética canina"
CIUDAD = "San José, Costa Rica"
OFERTA = "Baño Navideño Completo"
INCLUYE = [
    "Baño con champú suave",
    "Corte de uñas",
    "Limpieza de oídos",
    "Pañoleta navideña de regalo",
]
PRECIO_ANCLA = 25_000
PRECIO_OFERTA = 14_900
CUPOS_POR_DIA = 10
CAMPANA_INICIO = date(2026, 12, 1)
CAMPANA_FIN = date(2026, 12, 20)
FECHA_LIMITE = date(2026, 12, 18)  # último día para reservar (inclusive)

TAMANOS = {
    "pequeno": "Pequeño",
    "mediano": "Mediano",
    "grande": "Grande",
}

DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def dias_campana() -> list[date]:
    """Días de atención de la campaña: lunes a sábado (domingos cerrado)."""
    dias = []
    d = CAMPANA_INICIO
    while d <= CAMPANA_FIN:
        if d.weekday() != 6:
            dias.append(d)
        d += timedelta(days=1)
    return dias


def ahora() -> datetime:
    return datetime.now(TZ)


def hoy() -> date:
    return ahora().date()


def limite_dt() -> datetime:
    """Fin del día límite en hora de Costa Rica."""
    return datetime.combine(FECHA_LIMITE, datetime.max.time(), tzinfo=TZ).replace(microsecond=0)


def colones(monto: int) -> str:
    return "₡" + f"{monto:,}".replace(",", ".")


def fecha_larga(d: date) -> str:
    return f"{DIAS_SEMANA[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


def mcp_path() -> str:
    return f"/mcp-{MCP_PATH_SECRET}" if MCP_PATH_SECRET else "/mcp"
