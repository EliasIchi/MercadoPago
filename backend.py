from fastapi import FastAPI, Request
import mercadopago
import uuid

MP_ACCESS_TOKEN = "APP_USR-5249994394996474-011214-398ad97c27842a3a4d81a9bd045f32fb-145557542"

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
app = FastAPI()

# Simula BD (después se reemplaza)
pagos = {}

# -------------------------
# HEALTH CHECK
# -------------------------
@app.get("/")
def health():
    return {"status": "ok"}

# -------------------------
# CREAR QR
# -------------------------
@app.post("/crear_qr")
def crear_qr(data: dict):
    monto = float(data["monto"])
    ref = str(uuid.uuid4())

    pref = sdk.preference().create({
        "items": [{
            "title": "Cobro",
            "quantity": 1,
            "unit_price": monto
        }],
        "external_reference": ref,
        "notification_url": "https://mp-backend-4l3x.onrender.com/webhook"
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

# -------------------------
# WEBHOOK MP
# -------------------------
@app.post("/webhook")
async def webhook(request: Request):
    payment_id = request.query_params.get("id")
    topic = request.query_params.get("topic")

    if topic == "payment" and payment_id:
        pago = sdk.payment().get(payment_id)["response"]
        ref = pago.get("external_reference")

        if ref and ref in pagos:
            pagos[ref]["status"] = pago["status"]
            pagos[ref]["payment_id"] = payment_id
            pagos[ref]["transaction_id"] = (
                pago.get("transaction_details", {})
                    .get("transaction_id")
            )

    return {"ok": True}

# -------------------------
# ESTADO DE UN PAGO
# -------------------------
@app.get("/estado/{ref}")
def estado(ref: str):
    return pagos.get(ref, {"status": "not_found"})
