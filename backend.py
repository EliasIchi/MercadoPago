# backend.py

import uuid
import os
from fastapi import FastAPI, Request
import mercadopago

# -----------------------------
# Variables de entorno
# -----------------------------
MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN")
BACKEND_URL = os.environ.get("BACKEND_URL")  # ej: https://mp-backend-4l3x.onrender.com
PORT = int(os.environ.get("PORT", 8000))

if not MP_ACCESS_TOKEN:
    raise Exception("No se encontró la variable de entorno MP_ACCESS_TOKEN")
if not BACKEND_URL:
    raise Exception("No se encontró la variable de entorno BACKEND_URL")

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# -----------------------------
# App FastAPI
# -----------------------------
app = FastAPI()

# -----------------------------
# Diccionario temporal de pagos
# -----------------------------
pagos = {}

# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.get("/")
def health():
    return {"status": "ok"}

# -----------------------------
# CREAR QR / PREFERENCIA
# -----------------------------
@app.post("/crear_qr")
def crear_qr(data: dict):
    monto = float(data.get("monto", 0))
    if monto <= 0:
        return {"error": "Monto inválido"}

    ref = str(uuid.uuid4())

    pref = sdk.preference().create({
        "items": [{"title": "Cobro", "quantity": 1, "unit_price": monto}],
        "external_reference": ref,
        "notification_url": f"{BACKEND_URL}/webhook"
    })

    pagos[ref] = {"status": "pending", "payment_id": None, "transaction_id": None}

    return {
        "init_point": pref["response"]["init_point"],
        "external_reference": ref
