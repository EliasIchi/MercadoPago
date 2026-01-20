import os
import uuid
from fastapi import FastAPI, Request
from datetime import datetime
import mercadopago

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
app = FastAPI(title="Backend Mercado Pago PRO")

# =============================
# "DB" EN MEMORIA (REEMPLAZABLE)
# =============================
pagos = {}
# key: payment_id (str)
# value: info normalizada

# =============================
# HEALTH
# =============================
@app.get("/")
def health():
    return {"status": "ok"}

# =============================
# CREAR QR (OPCIONAL)
# =============================
@app.post("/crear_qr")
def crear_qr(data: dict):
    monto = float(data.get("monto", 0))
    if monto <= 0:
        return {"error": "Monto inválido"}

    ref = f"mp-qr-{uuid.uuid4()}"

    pref = sdk.preference().create({
        "items": [{
            "title": "Cobro",
            "quantity": 1,
            "unit_price": monto
        }],
        "external_reference": ref,
        "notification_url": f"{BACKEND_URL}/webhook"
    })

    return {
        "init_point": pref["response"]["init_point"],
        "external_reference": ref
    }

# =============================
# NORMALIZADOR DE PAGO
# =============================
def normalizar_pago(pago, origen="webhook"):
    payment_id = str(pago.get("id"))

    return {
        "mp_payment_id": payment_id,
        "status": pago.get("status"),
        "monto": pago.get("transaction_amount"),
        "tipo": pago.get("payment_type_id"),
        "referencia": pago.get("external_reference") or payment_id,
        "transaction_id": pago.get("transaction_details", {}).get("transaction_id"),
        "fecha": pago.get("date_created"),
        "origen": origen,
        "popup_mostrado": False,
        "full_info": pago
    }

# =============================
# WEBHOOK MP
# =============================
@app.post("/webhook")
async def webhook(request: Request):
    try:
        query = dict(request.query_params)
        topic = query.get("topic")
        mp_id = query.get("id")

        print("📬 Webhook:", query)

        if topic == "payment" and mp_id:
            pago_info = sdk.payment().get(mp_id)["response"]
            payment_id = str(pago_info["id"])

            pagos[payment_id] = normalizar_pago(
                pago_info,
                origen="webhook"
            )

            print("✅ Pago guardado (webhook):", payment_id)

    except Exception as e:
        print("❌ Webhook error:", e)

    return {"ok": True}

# =============================
# SYNC TOTAL MP (SIN FILTROS)
# =============================
@app.get("/sync_mp_all")
def sync_mp_all():
    try:
        result = sdk.payment().search({
            "limit": 50,
            "sort": "date_created",
            "criteria": "desc"
        })

        nuevos = []

        for pago in result["response"]["results"]:
            payment_id = str(pago["id"])

            if payment_id in pagos:
                continue

            pagos[payment_id] = normalizar_pago(
                pago,
                origen="sync"
            )
            nuevos.append(pagos[payment_id])

        print(f"🔄 Sync MP OK – {len(nuevos)} nuevos")
        return nuevos

    except Exception as e:
        print("❌ Sync MP error:", e)
        return {"error": str(e)}

# =============================
# DEVOLVER TODOS LOS PAGOS
# =============================
@app.get("/pagos")
def obtener_pagos():
    return list(pagos.values())

# =============================
# PARA POPUPS DEL POS
# =============================


@app.get("/pagos_pendientes_popup")
@app.get("/pagos_pendientes_popup")
def pagos_pendientes_popup():
    pendientes = []

    for payment_id, p in pagos.items():
        if p.get("status") == "approved" and not p.get("popup_mostrado"):
            p["popup_mostrado"] = True
            pendientes.append({
                "mp_payment_id": p.get("mp_payment_id"),   # ✅ CLAVE
                "monto": p.get("monto"),
                "tipo": p.get("tipo"),
                "referencia": p.get("referencia"),
            })

    return pendientes


@app.get("/estado_qr/{external_reference}")
def estado_qr(external_reference: str):
    pago = buscar_pago_qr(external_reference)

    if not pago:
        return {"status": "pending"}

    if pago["status"] == "approved":
        marcar_visto_qr(pago["id"])
        return {
            "status": "approved",
            "transaction_id": pago["mp_payment_id"]
        }

    if pago["status"] == "rejected":
        marcar_visto_qr(pago["id"])
        return {"status": "rejected"}

    return {"status": "pending"}


