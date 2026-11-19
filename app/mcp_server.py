"""Servidor MCP de Huellitas Vet (FastMCP). Todas las herramientas son de SOLO LECTURA."""
from __future__ import annotations

import unicodedata
from datetime import date
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from . import campana, config

mcp = FastMCP(
    name="Huellitas Vet",
    instructions=(
        "Datos en vivo de la campaña 'Baño Navideño Completo' de Huellitas Vet "
        "(veterinaria ficticia en San José, Costa Rica; precios en colones). "
        "Usa estas herramientas para consultar cupos, reservas (leads) y armar reportes "
        "o ideas de publicaciones. Todo es de solo lectura y los WhatsApp vienen enmascarados."
    ),
)

SOLO_LECTURA = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}


def _quitar_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _parse_dia(dia: str | None) -> date | None:
    if not dia:
        return None
    try:
        d = date.fromisoformat(dia.strip())
    except ValueError as e:
        raise ToolError("El día debe tener formato AAAA-MM-DD, por ejemplo 2026-12-05.") from e
    if d not in config.dias_campana():
        raise ToolError(f"{d.isoformat()} no es un día de la campaña (1–19 de diciembre de 2026, sin domingos).")
    return d


def _parse_tamano(tamano: str | None) -> str | None:
    if not tamano:
        return None
    t = _quitar_tildes(tamano.strip().lower())
    if t not in config.TAMANOS:
        raise ToolError("Tamaño inválido. Usa: pequeño, mediano o grande.")
    return t


@mcp.tool(annotations=SOLO_LECTURA)
def estado_campana() -> dict:
    """Estado general de la campaña del Baño Navideño: nombre de la oferta, precio ancla y
    precio de oferta, fechas, días que faltan para la fecha límite de reserva, cupos totales,
    reservados, libres y porcentaje de ocupación. Úsala para una vista rápida de cómo va la campaña."""
    return campana.estado()


@mcp.tool(annotations=SOLO_LECTURA)
def cupos_por_dia(
    solo_con_cupo: Annotated[bool, Field(description="Si es true, devuelve solo los días que aún tienen cupos libres.")] = False,
) -> list[dict]:
    """Lista cada día de atención de la campaña con fecha, día de la semana, cupos reservados,
    cupos libres y si todavía se puede reservar. Úsala para saber qué días promocionar o cuáles están agotados."""
    filas = campana.calendario()
    if solo_con_cupo:
        filas = [d for d in filas if d["libres"] > 0]
    return [
        {
            "fecha": d["fecha_iso"],
            "dia_semana": d["dia_semana"],
            "reservados": d["reservados"],
            "libres": d["libres"],
            "reservable": d["reservable"],
        }
        for d in filas
    ]


@mcp.tool(annotations=SOLO_LECTURA)
def listar_leads(
    dia: Annotated[str | None, Field(description="Filtra por día de reserva, formato AAAA-MM-DD (ej. 2026-12-12).")] = None,
    tamano: Annotated[str | None, Field(description="Filtra por tamaño de mascota: pequeño, mediano o grande.")] = None,
    limite: Annotated[int, Field(ge=1, le=50, description="Máximo de leads a devolver (1 a 50).")] = 20,
) -> dict:
    """Lista las reservas (leads) más recientes con nombre del dueño, mascota, tamaño, día reservado
    y estado. El WhatsApp siempre viene enmascarado (ej. 8***-**12) para proteger la privacidad."""
    d = _parse_dia(dia)
    t = _parse_tamano(tamano)
    filas = campana.listar(dia=d, tamano=t, limite=limite)
    return {"cantidad": len(filas), "filtros": {"dia": dia, "tamano": tamano, "limite": limite}, "leads": filas}


@mcp.tool(annotations=SOLO_LECTURA)
def resumen_campana() -> dict:
    """Reporte completo de la campaña: totales, reservas por día, por tamaño de mascota, día más lleno,
    día más vacío, leads de los últimos 7 días y 2–3 sugerencias de qué días promocionar.
    Úsala cuando pidan un reporte, análisis o ideas para una publicación en redes."""
    return campana.resumen()
