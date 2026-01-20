from fastapi import FastAPI, Request
import mercadopago

MP_ACCESS_TOKEN = "APP_USR-5249994394996474-011214-398ad97c27842a3a4d81a9bd045f32fb-145557542"

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
app = FastAPI()

ultimo_pago = {
    "status": "pending",
    "payment_id": None,
    "transaction_id": None
}

@app.post("/webhook")
async def webhook(request: Request):
    # 1️⃣ Query params (FORMA CORRECTA)
    payment_id = request.query_params.get("id")
    topic = request.query_params.get("topic")

    print("QUERY:", request.query_params)

    # 2️⃣ Intentar leer JSON (si viene)
    try:
        body = await request.json()
        print("BODY:", body)

        if not payment_id:
            payment_id = body.get("data", {}).get("id")

    except:
        body = None

    # 3️⃣ Procesar solo pagos
    if topic == "payment" and payment_id:
        pago = sdk.payment().get(payment_id)["response"]

        ultimo_pago["status"] = pago["status"]
        ultimo_pago["payment_id"] = payment_id
        ultimo_pago["transaction_id"] = (
            pago.get("transaction_details", {})
                .get("transaction_id")
        )

        print("PAGO ACTUALIZADO:", ultimo_pago)

    # 4️⃣ RESPUESTA RÁPIDA (CLAVE)
    return {"ok": True}
