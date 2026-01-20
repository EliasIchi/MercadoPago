# backend_debug.py

import uuid, os
from fastapi import FastAPI, Request
import mercadopago

# -----------------------------
# TOKEN de MP desde variables de entorno
# -----------------------------
MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN")
if not MP_ACCESS_TOKEN:
    raise Exception("No se encontró MP_ACCESS_TOKEN")

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
app = FastAPI(title="Backend Mercado Pago DEBUG")

# -----------------------------
# Diccionario temporal de pagos (simula la DB)
# -----------------------------
pagos = {}  # key = external_reference o id de MP

# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.get("/")
def health():
    return {"status": "ok"}

# -----------------------------
# CREAR QR / PREFERENCIA (POST)
# -----------------------------
@app.post("/crear_qr")
def crear_qr(data: dict):
    monto = float(data.get("monto", 0))
    if monto <= 0:
        return {"error": "Monto inválido"}

    ref = str(uuid.uuid4())
    base_url = os.environ.get("BACKEND_URL", "https://mp-backend-4l3x.onrender.com")
    notification_url = f"{base_url.rstrip('/')}/webhook"

    pref = sdk.preference().create({
        "items": [{"title": "Cobro", "quantity": 1, "unit_price": monto}],
        "external_reference": ref,
        "notification_url": notification_url
    })

    # Guardar pago pendiente
    pagos[ref] = {
        "status": "pending",
        "payment_id": None,
        "transaction_id": None,
        "full_info": pref  # Guardamos toda la info de la preferencia
    }

    # DEBUG
    print("📡 /crear_qr llamado")
    print("Monto:", monto)
    print("Referencia:", ref)
    print("Respuesta MP completa:", pref)

    return {"init_point": pref["response"]["init_point"],
            "external_reference": ref,
            "full_response": pref}

# -----------------------------
# WEBHOOK DE MERCADO PAGO (POST)
# -----------------------------
@app.post("/webhook")
async def webhook(request: Request):
    try: data = await request.json()
    except: data = {}

    query = dict(request.query_params)
    print("📬 /webhook recibido")
    print("Query params:", query)
    print("Body:", data)

    topic = query.get("topic")
    mp_id = query.get("id")

    if topic == "payment" and mp_id:
        pago_info = sdk.payment().get(mp_id)["response"]
        ref = pago_info.get("external_reference") or str(mp_id)

        pagos[ref] = {
            "status": pago_info.get("status"),
            "payment_id": str(mp_id),
            "transaction_id": pago_info.get("transaction_details", {}).get("transaction_id"),
            "payment_type": pago_info.get("payment_type_id"),
            "full_info": pago_info  # Guardamos todo lo que trae MP
        }

        print(f"✅ Pago actualizado: {ref}")
        print("Info completa del pago:", pago_info)

    print("📊 Pagos actuales en memoria:", pagos)
    return {"ok": True, "query": query, "body": data}

# -----------------------------
# CONSULTAR ESTADO DE UN PAGO (GET)
# -----------------------------
@app.get("/estado/{ref}")
def estado(ref: str):
    pago = pagos.get(ref)
    print(f"🔎 /estado llamado para ref={ref}")
    print("Pago encontrado:", pago)
    if not pago:
        return {"status": "not_found"}
    return pago

# -----------------------------
# SINCRONIZAR PAGOS MANUAL (GET)
# -----------------------------
@app.get("/sync_pagos")
def sync_pagos():
    try:
        result = sdk.payment().search({"limit": 100, "sort": "date_created", "criteria": "desc"})
        pagos_mp = result["response"]["results"]

        for pago in pagos_mp:
            ref = pago.get("external_reference") or str(pago.get("id"))
            pagos[ref] = {
                "status": pago.get("status"),
                "payment_id": str(pago.get("id")),
                "transaction_id": pago.get("transaction_details", {}).get("transaction_id"),
                "payment_type": pago.get("payment_type_id"),
                "full_info": pago
            }

        print(f"🔄 /sync_pagos completado: {len(pagos_mp)} pagos traídos")
        return {"ok": True, "pagos_sync": len(pagos_mp), "full_list": pagos_mp}
    except Exception as e:
        print("❌ Error en /sync_pagos:", e)
        return {"error": str(e)}

# -----------------------------
# LISTAR TODOS LOS PAGOS EN MEMORIA (GET)
# -----------------------------
@app.get("/pagos_nuevos")
def pagos_nuevos():
    print("📃 /pagos_nuevos llamado")
    return list(pagos.values())
