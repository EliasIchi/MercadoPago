import uuid
from fastapi import FastAPI, Request
import mercadopago

# -----------------------------
# Inicializar SDK de Mercado Pago
# -----------------------------
MP_ACCESS_TOKEN = "APP_USR-5249994394996474-011214-398ad97c27842a3a4d81a9bd045f32fb-145557542"
sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

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
# CREAR QR / PREFERENCIA
# -----------------------------
@app.post("/crear_qr")
def crear_qr(data: dict):
    monto = float(data.get("monto", 0))
    if monto <= 0:
        return {"error": "Monto inválido"}

    ref = str(uuid.uuid4())
    pref = sdk.preference().create({
        "items": [{
            "title": "Cobro",
            "quantity": 1,
            "unit_price": monto
        }],
        "external_reference": ref,
        "notification_url": os.getenv("RENDER_URL", "https://TU_RENDER_URL") + "/webhook"
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
# WEBHOOK MP
# -----------------------------
@app.post("/webhook")
async def webhook(request: Request):
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
# EJECUTAR SERVIDOR LOCAL
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
