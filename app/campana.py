"""Lógica de negocio compartida por la landing y el MCP (solo lectura)."""
from __future__ import annotations

import re
from datetime import date, timedelta

from sqlalchemy import select

from . import config, db


def reservas_abiertas() -> bool:
    return config.hoy() <= config.FECHA_LIMITE


def dia_reservable(d: date, hoy: date | None = None) -> bool:
    hoy = hoy or config.hoy()
    return d in config.dias_campana() and d >= hoy and hoy <= config.FECHA_LIMITE


def calendario() -> list[dict]:
    """Cada día de campaña con reservados, libres y si se puede reservar."""
    ocupacion = db.reservas_por_dia()
    hoy = config.hoy()
    dias = []
    for d in config.dias_campana():
        reservados = min(ocupacion.get(d, 0), config.CUPOS_POR_DIA)
        libres = config.CUPOS_POR_DIA - reservados
        dias.append({
            "fecha": d,
            "fecha_iso": d.isoformat(),
            "dia_semana": config.DIAS_SEMANA[d.weekday()],
            "etiqueta": config.fecha_larga(d),
            "reservados": reservados,
            "libres": libres,
            "lleno": libres == 0,
            "reservable": libres > 0 and dia_reservable(d, hoy),
        })
    return dias


def normalizar_whatsapp(valor: str) -> str | None:
    """Acepta 8888-8888, 88888888, +506 8888 8888, 506-8888-8888. Devuelve 8 dígitos."""
    if not valor:
        return None
    limpio = valor.strip()
    if re.search(r"[^\d\s\-+().]", limpio):
        return None
    digitos = re.sub(r"\D", "", limpio)
    if len(digitos) == 11 and digitos.startswith("506"):
        digitos = digitos[3:]
    if len(digitos) != 8:
        return None
    return digitos


def enmascarar_whatsapp(wa: str) -> str:
    """88123412 -> 8***-**12"""
    if not wa or len(wa) != 8:
        return "****-****"
    return f"{wa[0]}***-**{wa[-2:]}"


def dias_restantes_limite() -> int:
    return max((config.FECHA_LIMITE - config.hoy()).days, 0)


def estado() -> dict:
    cal = calendario()
    total = len(cal) * config.CUPOS_POR_DIA
    reservados = sum(d["reservados"] for d in cal)
    dias = config.dias_campana()
    return {
        "negocio": config.NEGOCIO,
        "oferta": config.OFERTA,
        "incluye": config.INCLUYE,
        "precio_ancla": config.colones(config.PRECIO_ANCLA),
        "precio_oferta": config.colones(config.PRECIO_OFERTA),
        "descuento_pct": round(100 * (1 - config.PRECIO_OFERTA / config.PRECIO_ANCLA)),
        "primer_dia": dias[0].isoformat(),
        "ultimo_dia": dias[-1].isoformat(),
        "dias_de_atencion": len(dias),
        "horario": "Lunes a sábado (domingos cerrado)",
        "fecha_limite_reserva": config.FECHA_LIMITE.isoformat(),
        "hoy": config.hoy().isoformat(),
        "dias_restantes_hasta_limite": dias_restantes_limite(),
        "reservas_abiertas": reservas_abiertas(),
        "cupos_por_dia": config.CUPOS_POR_DIA,
        "cupos_totales": total,
        "reservados": reservados,
        "libres": total - reservados,
        "ocupacion_pct": round(100 * reservados / total, 1) if total else 0.0,
        "landing_url": config.PUBLIC_URL or None,
    }


def listar(dia: date | None = None, tamano: str | None = None, limite: int = 20) -> list[dict]:
    limite = max(1, min(int(limite or 20), 50))
    q = select(db.leads).order_by(db.leads.c.creado_en.desc()).limit(limite)
    if dia:
        q = q.where(db.leads.c.dia_reserva == dia)
    if tamano:
        q = q.where(db.leads.c.tamano == tamano)
    with db.engine().connect() as c:
        filas = c.execute(q).mappings().all()
    return [
        {
            "id": f["id"],
            "creado_en": f["creado_en"].isoformat() if f["creado_en"] else None,
            "nombre_dueno": f["nombre_dueno"],
            "whatsapp": enmascarar_whatsapp(f["whatsapp"]),
            "mascota": f["mascota"],
            "tamano": config.TAMANOS.get(f["tamano"], f["tamano"]),
            "dia_reserva": db._a_fecha(f["dia_reserva"]).isoformat(),
            "estado": f["estado"],
        }
        for f in filas
    ]


def resumen() -> dict:
    est = estado()
    cal = calendario()
    with db.engine().connect() as c:
        filas = c.execute(select(db.leads.c.tamano, db.leads.c.creado_en)).all()

    por_tamano = {nombre: 0 for nombre in config.TAMANOS.values()}
    hace_7 = config.ahora() - timedelta(days=7)
    ultimos_7 = 0
    for tamano, creado in filas:
        por_tamano[config.TAMANOS.get(tamano, tamano)] = por_tamano.get(config.TAMANOS.get(tamano, tamano), 0) + 1
        if creado is not None:
            if creado.tzinfo is None:  # SQLite devuelve fechas sin zona
                creado = creado.replace(tzinfo=config.TZ)
            if creado >= hace_7:
                ultimos_7 += 1

    por_dia = [
        {"fecha": d["fecha_iso"], "dia_semana": d["dia_semana"], "reservados": d["reservados"], "libres": d["libres"]}
        for d in cal
    ]
    mas_lleno = max(cal, key=lambda d: (d["reservados"], d["fecha"]))
    mas_vacio = min(cal, key=lambda d: (d["reservados"], d["fecha"]))

    return {
        "totales": {
            "leads": len(filas),
            "cupos_totales": est["cupos_totales"],
            "reservados": est["reservados"],
            "libres": est["libres"],
            "ocupacion_pct": est["ocupacion_pct"],
            "dias_restantes_hasta_limite": est["dias_restantes_hasta_limite"],
        },
        "leads_por_dia": por_dia,
        "leads_por_tamano": por_tamano,
        "dia_mas_lleno": {"fecha": mas_lleno["fecha_iso"], "dia": mas_lleno["etiqueta"], "reservados": mas_lleno["reservados"]},
        "dia_mas_vacio": {"fecha": mas_vacio["fecha_iso"], "dia": mas_vacio["etiqueta"], "reservados": mas_vacio["reservados"]},
        "leads_ultimos_7_dias": ultimos_7,
        "sugerencias": sugerencias(cal, por_tamano),
    }


def sugerencias(cal: list[dict], por_tamano: dict[str, int]) -> list[str]:
    abiertos = [d for d in cal if d["reservable"]] or [d for d in cal if not d["lleno"]]
    out: list[str] = []
    if not abiertos:
        return ["Todos los cupos están vendidos: considera abrir una lista de espera."]

    vacios = sorted(abiertos, key=lambda d: (d["reservados"], d["fecha"]))[:3]
    nombres = ", ".join(d["etiqueta"] for d in vacios)
    out.append(
        f"Promociona {nombres}: son los días con más cupos libres "
        f"({', '.join(str(d['libres']) for d in vacios)} disponibles)."
    )

    entre_semana = [d for d in abiertos if d["fecha"].weekday() < 5]
    if entre_semana:
        libres_es = sum(d["libres"] for d in entre_semana)
        out.append(
            f"Entre semana quedan {libres_es} cupos: un post tipo «evita la fila del sábado, "
            f"ven entre semana» puede mover esa demanda."
        )

    casi_llenos = [d for d in abiertos if 0 < d["libres"] <= 3]
    if casi_llenos:
        out.append(
            "Usa urgencia real con " + ", ".join(d["etiqueta"] for d in casi_llenos)
            + ": quedan pocos cupos."
        )
    elif por_tamano:
        menor = min(por_tamano, key=por_tamano.get)
        out.append(f"Pocos perritos de tamaño {menor.lower()} reservados: muéstralos en la foto del post.")
    return out[:3]
