"""Carga manual de leads ficticios (opcional: la app ya lo hace sola si la tabla está vacía).

Uso:  python scripts/seed.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.seed_data import sembrar  # noqa: E402

if __name__ == "__main__":
    n = sembrar()
    print(f"Leads ficticios insertados: {n} (si es 0, ya estaban cargados)")
