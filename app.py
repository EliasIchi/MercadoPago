
# ================= CONFIG =================

import streamlit as st
import mercadopago
import time
import requests

MP_ACCESS_TOKEN = "APP_USR-5249994394996474-011214-398ad97c27842a3a4d81a9bd045f32fb-145557542"
BACKEND_URL = "https://mp-backend-4l3x.onrender.com"
import streamlit as st
import requests
import time

BACKEND_URL = "https://mp-backend-4l3x.onrender.com"

st.set_page_config(page_title="Cobro con QR", layout="centered")
st.title("📲 Cobro con QR Mercado Pago")

monto = st.number_input(
    "Monto a cobrar",
    min_value=1,
    step=100,
    format="%d"
)

# -------------------------
# GENERAR QR
# -------------------------
if st.button("Generar QR"):
    r = requests.post(
        f"{BACKEND_URL}/crear_qr",
        json={"monto": monto}
    )
    data = r.json()

    st.session_state["init_point"] = data["init_point"]
    st.session_state["ref"] = data["external_reference"]

# -------------------------
# MOSTRAR QR Y ESPERAR
# -------------------------
if "init_point" in st.session_state:
    st.subheader("Escaneá para pagar")

    qr_url = (
        "https://api.qrserver.com/v1/create-qr-code/"
        f"?size=300x300&data={st.session_state['init_point']}"
    )
    st.image(qr_url)

    estado = requests.get(
        f"{BACKEND_URL}/estado/{st.session_state['ref']}"
    ).json()

    if estado["status"] == "approved":
        st.success("✅ PAGO APROBADO")
        st.code(f"Transacción: {estado['transaction_id']}")

    elif estado["status"] == "rejected":
        st.error("❌ PAGO RECHAZADO")

    else:
        st.warning("⏳ Esperando pago...")
        time.sleep(3)
        st.rerun()
