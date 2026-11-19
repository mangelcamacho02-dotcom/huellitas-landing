"""Leads ficticios para demostrar la campaña. Todos los datos son inventados."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from . import config, db

# (dueño, whatsapp, mascota, tamaño, día de reserva, hace cuántos días se creó)
LEADS_FICTICIOS = [
    # Sábado 19: casi lleno
    ("María Fernanda Solís", "88123401", "Canela", "pequeno", date(2026, 12, 19), 1),
    ("José Pablo Araya", "87234512", "Thor", "grande", date(2026, 12, 19), 2),
    ("Daniela Vargas", "60345623", "Luna", "mediano", date(2026, 12, 19), 2),
    ("Andrés Mora", "71456734", "Rocky", "grande", date(2026, 12, 19), 3),
    ("Sofía Jiménez", "83567845", "Mía", "pequeno", date(2026, 12, 19), 4),
    ("Luis Diego Rojas", "62678956", "Max", "mediano", date(2026, 12, 19), 5),
    ("Valeria Chaves", "89789067", "Coco", "pequeno", date(2026, 12, 19), 6),
    ("Esteban Quesada", "70890178", "Bruno", "grande", date(2026, 12, 19), 8),
    ("Natalia Brenes", "85901289", "Nala", "mediano", date(2026, 12, 19), 9),
    # Sábado 12: bastante lleno
    ("Carlos Alvarado", "86012390", "Simba", "mediano", date(2026, 12, 12), 1),
    ("Gabriela Ureña", "61123401", "Lola", "pequeno", date(2026, 12, 12), 3),
    ("Fabián Castro", "72234512", "Zeus", "grande", date(2026, 12, 12), 4),
    ("Paola Méndez", "84345623", "Kira", "mediano", date(2026, 12, 12), 7),
    ("Ricardo Salas", "63456734", "Toby", "pequeno", date(2026, 12, 12), 10),
    ("Adriana Calderón", "88567845", "Chispa", "pequeno", date(2026, 12, 12), 11),
    ("Mauricio Porras", "73678956", "Oso", "grande", date(2026, 12, 12), 12),
    # Sábado 5: algo de movimiento
    ("Karla Segura", "87789067", "Pelusa", "pequeno", date(2026, 12, 5), 2),
    ("Jorge Hidalgo", "64890178", "Duque", "grande", date(2026, 12, 5), 6),
    ("Melissa Ramírez", "85901290", "Frida", "mediano", date(2026, 12, 5), 13),
    # Últimos días antes de la fecha límite
    ("Ana Lucía Cordero", "70012301", "Galleta", "pequeno", date(2026, 12, 18), 1),
    ("Diego Monge", "83123412", "Rex", "grande", date(2026, 12, 18), 5),
    ("Silvia Arias", "62234523", "Bombón", "pequeno", date(2026, 12, 17), 3),
    # Días entre semana casi vacíos
    ("Rodrigo Fallas", "89345634", "Pancho", "mediano", date(2026, 12, 4), 9),
    ("Tatiana Navarro", "71456745", "Maya", "mediano", date(2026, 12, 11), 4),
    ("Óscar Villalobos", "86567856", "Copito", "pequeno", date(2026, 12, 15), 0),
]


def sembrar() -> int:
    """Inserta los leads ficticios que falten. Idempotente: no duplica."""
    db.init_db()
    ahora = config.ahora()
    insertados = 0
    with db.engine().begin() as c:
        existentes = {
            (w, db._a_fecha(d))
            for w, d in c.execute(select(db.leads.c.whatsapp, db.leads.c.dia_reserva)).all()
        }
        for i, (nombre, wa, mascota, tamano, dia, hace) in enumerate(LEADS_FICTICIOS):
            if (wa, dia) in existentes:
                continue
            c.execute(
                db.leads.insert().values(
                    creado_en=ahora - timedelta(days=hace, hours=(i * 3) % 9, minutes=(i * 17) % 60),
                    nombre_dueno=nombre,
                    whatsapp=wa,
                    mascota=mascota,
                    tamano=tamano,
                    dia_reserva=dia,
                    estado="nuevo",
                )
            )
            insertados += 1
    return insertados


def sembrar_si_vacia() -> int:
    """Carga los leads ficticios solo si la tabla está vacía."""
    db.init_db()
    if db.total_leads() > 0:
        return 0
    return sembrar()
