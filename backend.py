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
    data = await request.json()

    if data.get("type") == "payment":
        pid = data["data"]["id"]
        pago = sdk.payment().get(pid)["response"]

        ultimo_pago["status"] = pago["status"]
        ultimo_pago["payment_id"] = pid
        ultimo_pago["transaction_id"] = (
            pago.get("transaction_details", {})
                .get("transaction_id")
        )
    return {"ok": True}

@app.get("/estado")
def estado():
    return ultimo_pago
