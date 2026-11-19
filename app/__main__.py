"""Arranque: python -m app  (lee PORT del entorno; Railway lo define solo)."""
import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        proxy_headers=True,          # respeta https detrás del proxy de Railway
        forwarded_allow_ips="*",
    )
