[TALLER_LANDING_MCP_ZERNIO.md](https://github.com/user-attachments/files/35111045/TALLER_LANDING_MCP_ZERNIO.md)
# Taller: Landing + MCP + Zernio — instrucciones para Claude Code

> **Para Claude Code:** este documento describe el proyecto completo. Léelo entero antes de empezar. Trabaja por fases, en orden. Al final de cada fase, muéstrame qué hiciste y **detente** donde diga `⏸️ PAUSA` (son pasos que yo hago a mano). Habla conmigo en español.

---

## 0. Datos del negocio (edítalos si quieres otro negocio)

Negocio ficticio. **No puede ser** ni "Navidad Mágica" ni "Torque Taller Automotriz" (son los ejemplos del curso).

| Campo | Valor |
|---|---|
| Nombre del negocio | **Huellitas Vet** — veterinaria y estética canina |
| Ciudad | San José, Costa Rica |
| Moneda | Colones (₡) |
| Oferta de temporada | **Baño Navideño Completo**: baño, corte de uñas, limpieza de oídos y pañoleta navideña |
| Precio ancla (antes) | ₡25.000 |
| Precio oferta | ₡14.900 |
| Cupos | **10 cupos por día** |
| Días de campaña | Del lunes 1 al sábado 20 de diciembre de 2026 (lunes a sábado; domingos cerrado) |
| Fecha límite para reservar | 18 de diciembre de 2026 |
| Campos del formulario | Nombre del dueño, WhatsApp, nombre de la mascota, tamaño (pequeño / mediano / grande), día preferido |
| Tono | Cálido, cercano, navideño, sin exagerar |

Todo dato de clientes es **ficticio**.

---

## 1. Qué hay que entregar (lo que pide el profesor)

Tres capturas de pantalla:
1. **La landing** publicada y funcionando (URL de Railway).
2. **La red social de prueba conectada a Zernio** + la publicación programada.
3. **Un chat con Claude usando el MCP** (por ejemplo, pidiéndole un reporte de la campaña).

Además, el PDF del taller pide el **repositorio en GitHub**.

Criterios de evaluación: landing con oferta clara y cupos reales (35 %), MCP con herramientas útiles y conectado (35 %), post en Zernio con datos reales y aprobado (20 %), **ninguna clave en el código** (10 %).

---

## 2. Arquitectura (un solo repo, un solo servicio en Railway)

```
Landing (FastAPI + HTML)  ──guarda leads──▶  Postgres (Railway)
                                                 ▲
Servidor MCP (FastMCP, montado en /mcp) ─────────┘  lee los datos
        ▲
Claude (conector personalizado)  +  Zernio (segundo conector) ──▶ publica en red de prueba
```

- **Lenguaje:** Python 3.11+
- **Web:** FastAPI + plantilla HTML (Jinja2) con CSS propio, sin frameworks pesados
- **MCP:** FastMCP (versión actual), transporte HTTP "streamable", montado dentro de la misma app FastAPI
- **Base de datos:** Postgres de Railway vía `DATABASE_URL`. En local, si no hay `DATABASE_URL`, usar SQLite (`leads.db`)
- **Despliegue:** Railway desde el repo de GitHub

> Claude Code: antes de escribir el código del MCP, revisa la documentación actual de FastMCP para la forma correcta de montarlo en FastAPI (p. ej. `mcp.http_app()` y pasar su `lifespan` a FastAPI). No asumas la API de memoria.

### Estructura sugerida
```
huellitas-landing/
├── app/
│   ├── main.py          # FastAPI: rutas de la landing + monta el MCP
│   ├── db.py            # conexión (Postgres o SQLite) y creación de tablas
│   ├── mcp_server.py    # herramientas FastMCP
│   ├── config.py        # lee variables de entorno
│   ├── templates/index.html
│   └── static/styles.css
├── scripts/seed.py      # carga leads ficticios
├── requirements.txt
├── Procfile             # o railway.json con el comando de arranque
├── .env.example         # nombres de variables, SIN valores reales
├── .gitignore           # incluye .env, leads.db, __pycache__
└── README.md
```

---

## 3. Fase 1 — Landing de temporada

**Una sola página, una sola oferta.** Debe tener:

- Encabezado con el nombre del negocio y la oferta.
- **Precio ancla tachado** (₡25.000) y precio oferta grande (₡14.900).
- Qué incluye (lista corta).
- **Cupos reales**: un selector o calendario simple con los días de campaña mostrando "quedan X cupos" calculados desde la base de datos (10 − reservas de ese día). Días llenos aparecen deshabilitados como "Agotado". Domingos no aparecen.
- **Fecha límite** visible (18 de diciembre) con una cuenta regresiva sencilla en JS.
- Formulario con los campos de la sección 0. Validación en servidor:
  - WhatsApp de Costa Rica: 8 dígitos (aceptar con o sin +506 y guiones; guardar normalizado).
  - No aceptar reserva si el día ya está lleno o si pasó la fecha límite.
  - Protección simple anti-spam (campo honeypot oculto).
- Página o mensaje de confirmación tras enviar.
- Diseño móvil primero, colores navideños sobrios, accesible (labels, contraste).
- Pie con "Negocio y datos ficticios — proyecto académico".

**Tabla `leads`:** `id, creado_en, nombre_dueno, whatsapp, mascota, tamano, dia_reserva (date), estado ('nuevo' por defecto)`.

**Seed:** `scripts/seed.py` crea ~25 leads ficticios repartidos de forma desigual (algunos días casi llenos, otros vacíos) para que el reporte tenga algo interesante. Que sea idempotente (no duplique si se corre dos veces).

Endpoint de salud: `GET /health` → `{"ok": true}`.

Prueba local con `uvicorn` y muéstrame que funciona.

---

## 4. Fase 2 — Servidor MCP (FastMCP)

Herramientas (nombres en español, con descripciones claras para que Claude sepa cuándo usarlas):

| Herramienta | Qué devuelve |
|---|---|
| `estado_campana` | Nombre de la oferta, precios, fechas, días restantes hasta la fecha límite, total de cupos, reservados, libres, % de ocupación |
| `cupos_por_dia` | Lista de cada día de campaña: fecha, día de la semana, reservados, libres. Parámetro opcional `solo_con_cupo: bool` |
| `listar_leads` | Leads con filtros opcionales `dia`, `tamano`, `limite` (máx. 50). **WhatsApp enmascarado** (ej. `8***-**12`) |
| `resumen_campana` | Totales, leads por día, por tamaño de mascota, día más lleno, día más vacío, leads de los últimos 7 días, y 2–3 sugerencias de qué días promocionar |

Reglas:
- Solo lectura. Ninguna herramienta modifica ni borra datos.
- Montar en la ruta `/mcp`. Si existe la variable de entorno `MCP_PATH_SECRET`, montarlo en `/mcp-<MCP_PATH_SECRET>` para que la URL no sea adivinable (los conectores personalizados de Claude aceptan servidores sin login; esta es la protección mínima).
- Probar localmente con el cliente de FastMCP o el MCP Inspector antes de desplegar.

---

## 5. Fase 3 — GitHub y Railway

1. Inicializar git, primer commit, revisar que **no** haya `.env` ni claves en ningún archivo (busca con grep patrones como `sk_`, `postgres://`, `password`).
2. Crear el repo en GitHub (público o privado) y subirlo. Si tengo `gh` instalado y autenticado, úsalo; si no, dame los comandos.

`⏸️ PAUSA — Railway (lo hago yo, o tú con la CLI de Railway si ya está logueada):`
- Nuevo proyecto → Deploy from GitHub repo → elegir el repo.
- Agregar un servicio **Postgres** al proyecto. Railway expone `DATABASE_URL`; referenciarla en el servicio web.
- Variables del servicio web: `DATABASE_URL` (referencia), `MCP_PATH_SECRET` (una cadena aleatoria larga).
- Settings → Networking → **Generate Domain**.
- Correr el seed una vez (`railway run python scripts/seed.py` o un comando temporal).

Luego verifica: `https://<dominio>/health`, la landing carga, y una reserva de prueba baja los cupos.

📸 **Captura 1:** la landing en el celular o navegador mostrando oferta, precio tachado y cupos.

---

## 6. Fase 4 — Conectar el MCP a Claude

`⏸️ PAUSA — lo hago yo en claude.ai (web o app):`
- Configuración → **Conectores** → **Agregar conector personalizado**.
- Nombre: `Huellitas Vet`. URL: `https://<dominio>/mcp-<MCP_PATH_SECRET>/` (Claude Code: dime la URL exacta, incluida la barra final si hace falta).
- En un chat nuevo, activar el conector y preguntar, por ejemplo:
  - "¿Qué días de la campaña siguen con más cupos libres?"
  - "Dame un reporte de la campaña del Baño Navideño."

📸 **Captura 3:** el chat donde se ve a Claude usando las herramientas del MCP y el reporte.

---

## 7. Fase 5 — Zernio para publicar

`⏸️ PAUSA — lo hago yo:`
1. Crear cuenta en zernio.com, crear un perfil y **conectar una red social de prueba** (una página/cuenta creada solo para esto, nunca una real del trabajo).
2. En claude.ai: Configuración → Conectores → Agregar conector personalizado → Nombre `Zernio`, URL `https://mcp.zernio.com/mcp` → iniciar sesión con Zernio cuando lo pida (no hace falta API key).
3. En un chat con **ambos conectores activos**, pedir algo como:

> "Revisa con el conector de Huellitas Vet qué días tienen más cupos libres y propón un post para Instagram/Facebook invitando a reservar esos días, con el precio de oferta y el link a la landing. No publiques nada hasta que yo lo apruebe. Cuando lo apruebe, prográmalo con Zernio en mi cuenta de prueba para mañana a las 10:00 a. m. hora de Costa Rica."

4. Revisar el texto, aprobarlo, y confirmar en el panel de Zernio que quedó programado.

📸 **Captura 2:** panel de Zernio con la red de prueba conectada y la publicación programada.

---

## 8. Reglas que no se rompen

- **Cero claves en el código.** Todo en variables de entorno. `.env.example` solo con nombres.
- Solo cuentas de prueba. Nada se publica sin mi aprobación.
- Datos ficticios únicamente.
- El MCP es de solo lectura y enmascara los WhatsApp.

## 9. Al terminar

Actualiza el `README.md` con: qué es el proyecto, URL de la landing, cómo correrlo en local, variables de entorno necesarias (sin valores), lista de herramientas MCP y el flujo:
**Landing capta leads → MCP los expone → Claude analiza y escribe → Zernio publica → más tráfico a la landing.**

Dame al final un checklist con: URL de la landing, URL del repo, URL del conector MCP, y qué capturas me faltan.
