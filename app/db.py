"""Conexión a la base de datos (Postgres en Railway, SQLite en local)."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from sqlalchemy import (
    Column, Date, DateTime, Integer, MetaData, String, Table, create_engine, func, select, text,
)
from sqlalchemy.engine import Engine

from . import config

metadata = MetaData()

leads = Table(
    "leads",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("creado_en", DateTime(timezone=True), nullable=False),
    Column("nombre_dueno", String(80), nullable=False),
    Column("whatsapp", String(8), nullable=False),
    Column("mascota", String(60), nullable=False),
    Column("tamano", String(10), nullable=False),
    Column("dia_reserva", Date, nullable=False, index=True),
    Column("estado", String(20), nullable=False, server_default="nuevo"),
)


def _url() -> str:
    url = config.DATABASE_URL
    if not url:
        ruta = Path(__file__).resolve().parent.parent / "leads.db"
        return f"sqlite:///{ruta}"
    # Railway entrega postgresql:// (o postgres://); usamos el driver psycopg 3.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


_engine: Engine | None = None


def engine() -> Engine:
    global _engine
    if _engine is None:
        url = _url()
        kwargs = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(url, **kwargs)
    return _engine


def es_postgres() -> bool:
    return engine().dialect.name == "postgresql"


def init_db() -> None:
    metadata.create_all(engine())


def total_leads() -> int:
    with engine().connect() as c:
        return c.execute(select(func.count()).select_from(leads)).scalar_one()


def reservas_por_dia() -> dict[date, int]:
    with engine().connect() as c:
        filas = c.execute(
            select(leads.c.dia_reserva, func.count()).group_by(leads.c.dia_reserva)
        ).all()
    return {_a_fecha(d): n for d, n in filas}


def _a_fecha(valor) -> date:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return date.fromisoformat(str(valor))


class DiaLleno(Exception):
    pass


class Duplicado(Exception):
    pass


def crear_reserva(nombre: str, whatsapp: str, mascota: str, tamano: str, dia: date) -> int:
    """Inserta un lead verificando cupo dentro de la misma transacción."""
    with engine().begin() as c:
        if es_postgres():
            # Serializa reservas del mismo día para no sobrevender cupos.
            c.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": dia.toordinal()})
        ocupados = c.execute(
            select(func.count()).select_from(leads).where(leads.c.dia_reserva == dia)
        ).scalar_one()
        if ocupados >= config.CUPOS_POR_DIA:
            raise DiaLleno()
        repetido = c.execute(
            select(func.count()).select_from(leads).where(
                leads.c.dia_reserva == dia,
                leads.c.whatsapp == whatsapp,
                func.lower(leads.c.mascota) == mascota.lower(),
            )
        ).scalar_one()
        if repetido:
            raise Duplicado()
        res = c.execute(
            leads.insert().values(
                creado_en=config.ahora(),
                nombre_dueno=nombre,
                whatsapp=whatsapp,
                mascota=mascota,
                tamano=tamano,
                dia_reserva=dia,
                estado="nuevo",
            )
        )
        return int(res.inserted_primary_key[0])
