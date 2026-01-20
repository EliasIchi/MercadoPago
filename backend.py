import uuid
import os
from fastapi import FastAPI, Request
import mercadopago

# -----------------------------
# TOKEN de MP desde variables de entorno
# -----------------------------
MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN")
if not MP_ACCESS_TOKEN:
    raise Exception("No se encontró la variable de entorno MP_ACCESS_TOKEN")

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# -----------------------------
# APP FASTAPI
# -----------------------------
app = FastAPI()

# -----------------------------
# Diccionario temporal de pagos (simula la BD)
# -----------------------------
pagos = {}  # key = external_reference o id de MP

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
            "BACKEND_URL", "https://TU_RENDER_URL"
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
    Endpoint que recibe notificaciones de MP (cualquier tipo: payment, transfer, etc.)
    """
    try:
        data = await request.json()
    except:
        data = {}

    topic = request.query_params.get("topic")
    mp_id = request.query_params.get("id")

    # Si es un pago, traemos info completa
    if topic == "payment" and mp_id:
        pago_info = sdk.payment().get(mp_id)["response"]
        ref = pago_info.get("external_reference") or str(mp_id)

        pagos[ref] = {
            "status": pago_info.get("status"),
            "payment_id": str(mp_id),
            "transaction_id": pago_info.get("transaction_details", {}).get("transaction_id"),
            "payment_type": pago_info.get("payment_type_id")
        }

        print(f"✅ Webhook recibido: {ref} ({pago_info.get('status')})")

    return {"ok": True}

# -----------------------------
# CONSULTAR ESTADO DE UN PAGO
# -----------------------------
@app.get("/estado/{ref}")
def estado(ref: str):
    return pagos.get(ref, {"status": "not_found"})

# -----------------------------
# OBTENER PAGOS NUEVOS (para tu POS)
# -----------------------------
@app.get("/api/pagos/nuevos")
def pagos_nuevos():
    """
    Devuelve todos los pagos registrados para que tu POS los consulte periódicamente
    """
    return list(pagos.values())

# -----------------------------
# SINCRONIZAR PAGOS MP MANUAL
# -----------------------------
@app.get("/sync_pagos")
def sync_pagos():
    """
    Trae los últimos pagos de MP (transferencias, cobros, QR, propinas, etc.)
    """
    try:
        result = sdk.payment().search({
            "limit": 100,
            "sort": "date_created",
            "criteria": "desc"
        })
        pagos_mp = result["response"]["results"]

        for pago in pagos_mp:
            ref = pago.get("external_reference") or str(pago.get("id"))
            pagos[ref] = {
                "status": pago.get("status"),
                "payment_id": str(pago.get("id")),
                "transaction_id": pago.get("transaction_details", {}).get("transaction_id"),
                "payment_type": pago.get("payment_type_id")
            }

        return {"ok": True, "pagos_sync": len(pagos_mp)}

    except Exception as e:
        return {"error": str(e)}

# -----------------------------
# EJECUTAR SERVIDOR
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
