# backend.py

import uuid
from fastapi import FastAPI, Request
import mercadopago
import os

# -----------------------------
# TOKEN de MP desde variables de entorno
# -----------------------------
MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN")
if not MP_ACCESS_TOKEN:
    raise Exception("No se encontró la variable de entorno MP_ACCESS_TOKEN")

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# -----------------------------
# App FastAPI
# -----------------------------
app = FastAPI()

# -----------------------------
# Diccionario temporal de pagos (simula la BD)
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
        "notification_url": os.environ.get(
            "BACKEND_URL", "https://mp-backend-4l3x.onrender.com"
        ) + "/webhook"
    })

    # Guardar pago pendiente
    pagos[ref] = {"status": "pending", "payment_id": None, "transaction_id": None}

    return {
        "init_point": pref["response"]["init_point"],
        "external_reference": ref
    }

# -----------------------------
# WEBHOOK DE MERCADO PAGO
# -----------------------------
@app.post("/webhook")
async def webhook(request: Request):
    """
    Endpoint para recibir notificaciones de Mercado Pago.
    MP envía POST requests aquí.
    """
    try:
        data = await request.json()
    except:
        data = {}

    topic = request.query_params.get("topic")
    payment_id = request.query_params.get("id")

    if topic == "payment" and payment_id:
        pago_info = sdk.payment().get(payment_id)["response"]
        ref = pago_info.get("external_reference")
        if ref:
            pagos[ref] = {
                "status": pago_info.get("status"),
                "payment_id": payment_id,
                "transaction_id": pago_info.get("transaction_details", {}).get("transaction_id")
            }
            print(f"✅ Webhook recibido y pago actualizado: {ref}")

    return {"ok": True}

# -----------------------------
# CONSULTAR ESTADO DE UN PAGO
# -----------------------------
@app.get("/estado/{ref}")
def estado(ref: str):
    return pagos.get(ref, {"status": "not_found"})

# -----------------------------
# EJECUTAR SERVIDOR (Render)
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
