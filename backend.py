# backend_mp.py
import os
import uuid
from fastapi import FastAPI, Request
from mercadopago import SDK

# -----------------------------
# Variables de entorno
# -----------------------------
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
RENDER_URL = os.getenv("RENDER_URL")
PORT = int(os.getenv("PORT", 8000))

if not MP_ACCESS_TOKEN or not RENDER_URL:
    raise Exception("❌ Variables de entorno MP_ACCESS_TOKEN y RENDER_URL son necesarias")

# -----------------------------
# SDK de Mercado Pago
# -----------------------------
sdk = SDK(MP_ACCESS_TOKEN)

# -----------------------------
# App FastAPI
# -----------------------------
app = FastAPI()

# -----------------------------
# Diccionario temporal de pagos (simula BD)
# -----------------------------
pagos = {}

# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.get("/")
def health():
    return {"status": "ok"}

# -----------------------------
# CREAR PREFERENCIA / QR
# -----------------------------
@app.post("/crear_qr")
def crear_qr(data: dict):
    """
    Crea una preferencia de pago en MP y devuelve el init_point y external_reference.
    """
    monto = float(data.get("monto", 0))
    if monto <= 0:
        return {"error": "Monto inválido"}

    ref = str(uuid.uuid4())

    pref = sdk.preference().create({
        "items": [{"title": "Cobro", "quantity": 1, "unit_price": monto}],
        "external_reference": ref,
        "notification_url": f"{RENDER_URL}/webhook"
    })

    pagos[ref] = {
        "status": "pending",
        "payment_id": None,
        "transaction_id": None
    }

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
    Endpoint que recibe notificaciones de todos los pagos de MP.
    """
    try:
        data = await request.json()
    except:
        data = {}

    # MP envía topic=payment o merchant_order
    topic = request.query_params.get("topic")
    payment_id = request.query_params.get("id")

    if topic == "payment" and payment_id:
        pago_info = sdk.payment().get(payment_id)["response"]
        ref = pago_info.get("external_reference") or str(payment_id)

        pagos[ref] = {
            "status": pago_info.get("status"),
            "payment_id": str(payment_id),
            "transaction_id": pago_info.get("transaction_details", {}).get("transaction_id"),
            "tipo": pago_info.get("payment_type_id"),
            "monto": pago_info.get("transaction_amount")
        }
        print(f"✅ Webhook recibido: {ref} → {pagos[ref]['status']}")

    return {"ok": True}

# -----------------------------
# DEVOLVER ESTADO DE TODOS LOS PAGOS
# -----------------------------
@app.get("/pagos_pendientes")
def pagos_pendientes():
    """
    Devuelve todos los pagos aprobados o pendientes.
    """
    return [ {**{"referencia": k}, **v} for k, v in pagos.items() ]

# -----------------------------
# CONSULTAR ESTADO DE UN PAGO POR REF
# -----------------------------
@app.get("/estado/{ref}")
def estado(ref: str):
    return pagos.get(ref, {"status": "not_found"})

# -----------------------------
# EJECUTAR SERVIDOR
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    print("🚀 Backend MP iniciado en Render...")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
