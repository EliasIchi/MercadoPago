import uuid
from fastapi import FastAPI, Request
import mercadopago
from fastapi.middleware.cors import CORSMiddleware

MP_ACCESS_TOKEN = "APP_USR-5249994394996474-011214-398ad97c27842a3a4d81a9bd045f32fb-145557542"

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
app = FastAPI()

# Permitir CORS para tu GUI / Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# -------------------------
# BD simulada en memoria
# -------------------------
pagos = {}

# -------------------------
# HEALTH CHECK
# -------------------------
@app.get("/")
def health():
    return {"status": "ok"}

# -------------------------
# CREAR QR (Streamlit)
# -------------------------
@app.post("/crear_qr")
def crear_qr(data: dict):
    monto = float(data["monto"])
    ref = str(uuid.uuid4())

    pref = sdk.preference().create({
        "items": [{"title": "Cobro", "quantity": 1, "unit_price": monto}],
        "external_reference": ref,
        "notification_url": "https://mp-backend-4l3x.onrender.com/webhook"
    })

    pagos[ref] = {
        "status": "pending",
        "payment_id": None,
        "transaction_id": None,
        "tipo": "QR"
    }

    return {
        "init_point": pref["response"]["init_point"],
        "external_reference": ref
    }

# -------------------------
# WEBHOOK MP (detecta todos los pagos)
# -------------------------
@app.post("/webhook")
async def webhook(request: Request):
    payment_id = request.query_params.get("id")
    topic = request.query_params.get("topic")

    if topic == "payment" and payment_id:
        pago = sdk.payment().get(payment_id)["response"]
        ref = pago.get("external_reference") or str(uuid.uuid4())
        tipo = "Mercado Pago"

        # Detectar si es transferencia o QR
        mp_tipo = pago.get("payment_type_id", "").lower()
        if "ticket" in mp_tipo:
            tipo = "QR"
        elif "bank_transfer" in mp_tipo or "atm" in mp_tipo:
            tipo = "Transferencia"

        # Guardar o actualizar
        pagos[ref] = {
            "status": pago["status"],
            "payment_id": payment_id,
            "transaction_id": pago.get("transaction_details", {}).get("transaction_id"),
            "tipo": tipo
        }

    return {"ok": True}

# -------------------------
# ESTADO DE UN PAGO
# -------------------------
@app.get("/estado/{ref}")
def estado(ref: str):
    return pagos.get(ref, {"status": "not_found"})

# -------------------------
# LISTAR PAGOS PENDIENTES / TODOS
# -------------------------
@app.get("/pagos_pendientes")
def pagos_pendientes():
    result = []
    for ref, p in pagos.items():
        if p["status"] in ["pending", "approved"]:
            result.append({
                "referencia": ref,
                "monto": p.get("transaction_amount", 0),
                "tipo": p.get("tipo"),
                "status": p.get("status")
            })
    return result

# -------------------------
# REGISTRAR PAGO MANUAL (opcional)
# -------------------------
@app.post("/registrar_pago_manual")
def registrar_pago_manual(data: dict):
    ref = str(uuid.uuid4())
    pagos[ref] = {
        "status": "approved",
        "payment_id": ref,
        "transaction_id": ref,
        "tipo": data.get("tipo", "Transferencia"),
        "monto": data.get("monto", 0)
    }
    return {"ok": True, "ref": ref}
@app.get("/estado/{ref}")
def estado(ref: str):
    return pagos.get(ref, {"status": "not_found"})
