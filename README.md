# Huellitas Vet — Landing + MCP + Zernio 🐾🎄

Proyecto académico: landing de temporada para **Huellitas Vet** (veterinaria y estética canina ficticia en San José, Costa Rica) con la oferta **Baño Navideño Completo** (₡25.000 → **₡14.900**, 10 cupos por día), más un **servidor MCP** que expone los datos de la campaña a Claude para analizarlos y preparar publicaciones que luego se programan con **Zernio**.

> Negocio y datos ficticios — proyecto académico.

**Landing:** `https://<tu-dominio>.up.railway.app` *(completar tras el despliegue)*

## Flujo

**Landing capta leads → MCP los expone → Claude analiza y escribe → Zernio publica → más tráfico a la landing.**

```
Landing (FastAPI + HTML)  ──guarda leads──▶  Postgres (Railway)
                                                 ▲
Servidor MCP (FastMCP, en /mcp-<secreto>/) ──────┘  lee los datos (solo lectura)
        ▲
Claude (conector personalizado)  +  Zernio (segundo conector) ──▶ publica en red de prueba
```

## Qué incluye

- **Landing** (una sola oferta): precio ancla tachado, qué incluye, cuenta regresiva a la fecha límite (18 de diciembre), selector de días con **cupos reales** desde la base de datos (días llenos = "Agotado", domingos no aparecen), formulario con validación en servidor (WhatsApp CR de 8 dígitos con o sin +506, día lleno, fecha límite, día pasado, duplicados) y honeypot anti‑spam.
- **Base de datos:** Postgres en Railway (`DATABASE_URL`); SQLite (`leads.db`) en local si no hay `DATABASE_URL`.
- **Leads ficticios automáticos:** al arrancar, si la tabla `leads` está vacía, se cargan ~25 leads ficticios repartidos de forma desigual. `scripts/seed.py` hace lo mismo a mano y es idempotente.
- **MCP** (FastMCP, HTTP streamable) montado en la misma app.
- `GET /health` → `{"ok": true}`.

> Nota de calendario: el 1 de diciembre de 2026 es martes y el 20 es domingo, así que los días de atención (lunes a sábado) van del **martes 1 al sábado 19 de diciembre**: 17 días, 170 cupos.

## Herramientas MCP (todas de solo lectura)

| Herramienta | Qué devuelve |
|---|---|
| `estado_campana` | Oferta, precios, fechas, días restantes a la fecha límite, cupos totales, reservados, libres y % de ocupación |
| `cupos_por_dia` | Cada día de campaña: fecha, día de la semana, reservados, libres. Parámetro opcional `solo_con_cupo` |
| `listar_leads` | Leads con filtros `dia` (AAAA‑MM‑DD), `tamano` (pequeño/mediano/grande), `limite` (máx. 50). WhatsApp enmascarado (`8***-**12`) |
| `resumen_campana` | Totales, leads por día y por tamaño, día más lleno y más vacío, leads de los últimos 7 días y sugerencias de qué días promocionar |

URL del conector: `https://<tu-dominio>/mcp-<MCP_PATH_SECRET>/` (con la barra final). Sin `MCP_PATH_SECRET`, queda en `/mcp/`.

## Variables de entorno (sin valores en el repo)

| Variable | Para qué |
|---|---|
| `DATABASE_URL` | Conexión a Postgres. En Railway: `${{Postgres.DATABASE_URL}}`. Vacía = SQLite local |
| `MCP_PATH_SECRET` | Cadena aleatoria larga; el MCP queda en `/mcp-<secreto>/` |
| `AUTO_SEED` | `true` por defecto: carga leads ficticios si la tabla está vacía |
| `PUBLIC_URL` | Opcional: URL pública de la landing (el MCP la devuelve para los posts) |
| `PORT` | La define Railway sola |

Ver `.env.example`.

## Correr en local

Requiere Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app                    # http://localhost:8000  ·  MCP en http://localhost:8000/mcp/
```

Pruebas:

```bash
pip install pytest httpx
python -m pytest -q
```

## Despliegue en Railway

1. New Project → Deploy from GitHub repo → este repo.
2. Agregar un servicio **Postgres**.
3. En el servicio web, variables: `DATABASE_URL=${{Postgres.DATABASE_URL}}`, `MCP_PATH_SECRET=<cadena aleatoria>`, `PUBLIC_URL=https://<dominio>`.
4. Comando de arranque: `python -m app` (ya está en `railway.json` y `Procfile`). Healthcheck: `/health`.
5. Settings → Networking → **Generate Domain**.

No hace falta correr el seed: la app lo hace sola al primer arranque.

## Estructura

```
app/
  main.py         FastAPI: landing, /reservar, /gracias, /health y monta el MCP
  mcp_server.py   Herramientas FastMCP (solo lectura)
  campana.py      Lógica de cupos, validación y reportes
  db.py           Conexión Postgres/SQLite y tabla leads
  seed_data.py    Leads ficticios + carga automática
  config.py       Datos de la campaña y variables de entorno
  templates/      index.html, gracias.html, base.html
  static/         styles.css
scripts/seed.py   Carga manual de leads ficticios (opcional)
tests/            Pruebas con pytest
```
