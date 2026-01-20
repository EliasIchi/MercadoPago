import uuid
import os
from fastapi import FastAPI, Request
import mercadopago
from datetime import datetime

# =============================
# CONFIG
# =============================
MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN")
if not MP_ACCESS_TOKEN:
    raise Exception("No se encontró MP_ACCESS_TOKEN")

BACKEND_URL = os.environ.get(
    "BACKEND_URL",
    "https://mp-backend-4l3x.onrender.com"
)

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
app = FastAPI(title="Backend Mercado Pago")

# =============================
# "DB" EN MEMORIA (REEMPLAZABLE)
# =============================
pagos = {}
# pagos[ref] = {
#   status, monto, payment_id,
#   transaction_id, payment_type,
#   notificado, fecha, full_info
# }

# =============================
# HEALTH
# =============================
@app.get("/")
def health():
    return {"status": "ok"}

# =============================
# CREAR QR
# =============================
@app.post("/crear_qr")
def crear_qr(data: dict):
    monto = float(data.get("monto", 0))
    if monto <= 0:
        return {"error": "Monto inválido"}

    ref = str(uuid.uuid4())

    pref = sdk.preference().create({
        "items": [
            {
                "title": "Cobro",
                "quantity": 1,
                "unit_price": monto
            }
        ],
        "external_reference": ref,
        "notification_url": f"{BACKEND_URL}/webhook"
    })

    pagos[ref] = {
        "status": "pending",
        "monto": monto,
        "payment_id": None,
        "transaction_id": None,
        "payment_type": None,
        "notificado": False,
        "fecha": datetime.now().isoformat(),
        "full_info": pref
    }

    print("📡 QR creado:", ref, "Monto:", monto)

    return {
        "init_point": pref["response"]["init_point"],
        "external_reference": ref
    }

# =============================
# WEBHOOK MP
# =============================
@app.post("/webhook")
async def webhook(request: Request):
    # responder rápido
    response = {"ok": True}

    try:
        data = await request.json()
    except:
        data = {}

    query = dict(request.query_params)
    topic = query.get("topic")
    mp_id = query.get("id")

    print("📬 Webhook recibido:", query)

    if topic == "payment" and mp_id:
        pago_info = sdk.payment().get(mp_id)["response"]
        ref = pago_info.get("external_reference") or str(mp_id)

        pagos[ref] = {
            "status": pago_info.get("status"),
            "monto": pago_info.get("transaction_amount"),
            "payment_id": str(mp_id),
            "transaction_id": pago_info.get(
                "transaction_details", {}
            ).get("transaction_id"),
            "payment_type": pago_info.get("payment_type_id"),
            "notificado": False,
            "fecha": pago_info.get("date_created"),
            "full_info": pago_info
        }

        print("✅ Pago actualizado:", ref, pagos[ref]["status"])

    return response

# =============================
# ESTADO DE UN PAGO
# =============================
@app.get("/estado/{ref}")
def estado_pago(ref: str):
    pago = pagos.get(ref)
    if not pago:
        return {"status": "not_found"}
    return pago

# =============================
# POLLING PRO (POS)
# =============================
@app.get("/pagos_pendientes_popup")
def pagos_pendientes_popup():
    """
    Devuelve SOLO pagos aprobados
    que todavía no fueron notificados
    """
    nuevos = []

    for ref, pago in pagos.items():
        if pago["status"] == "approved" and not pago["notificado"]:
            pago["notificado"] = True
            nuevos.append({
                "referencia": ref,
                "monto": pago["monto"],
                "tipo": pago["payment_type"],
                "fecha": pago["fecha"]
            })

    print(f"🔔 Pagos nuevos para popup: {len(nuevos)}")
    return nuevos

# =============================
# BACKUP MANUAL (POR SI FALLA WEBHOOK)
# =============================
@app.get("/sync_pagos")
def sync_pagos():
    try:
        result = sdk.payment().search({
            "limit": 50,
            "sort": "date_created",
            "criteria": "desc"
        })

        for pago in result["response"]["results"]:
            ref = pago.get("external_reference") or str(pago["id"])

            if ref not in pagos:
                pagos[ref] = {
                    "status": pago.get("status"),
                    "monto": pago.get("transaction_amount"),
                    "payment_id": str(pago["id"]),
                    "transaction_id": pago.get(
                        "transaction_details", {}
                    ).get("transaction_id"),
                    "payment_type": pago.get("payment_type_id"),
                    "notificado": False,
                    "fecha": pago.get("date_created"),
                    "full_info": pago
                }

        return {"ok": True, "total": len(pagos)}

    except Exception as e:
        return {"error": str(e)}
