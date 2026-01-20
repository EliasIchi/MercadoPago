import streamlit as st
import requests
from streamlit_autorefresh import st_autorefresh

BACKEND_URL = "https://mp-backend-4l3x.onrender.com"

st.set_page_config(page_title="Cobro con QR", layout="centered")
st.title("📲 Cobro con QR Mercado Pago")

# -------------------------
# Session state
# -------------------------
for key in ["init_point", "ref", "monto"]:
    if key not in st.session_state:
        st.session_state[key] = None

# -------------------------
# Monto
# -------------------------
monto = st.number_input("Monto a cobrar", min_value=1, step=100, format="%d")
st.session_state["monto"] = monto

# -------------------------
# Generar QR
# -------------------------
if st.button("Generar QR"):
    if monto <= 0:
        st.error("❌ Monto inválido")
    else:
        r = requests.post(
            f"{BACKEND_URL}/crear_qr",
            json={"monto": monto},
            timeout=5
        )

        if r.status_code == 200:
            data = r.json()
            st.session_state["init_point"] = data["init_point"]
            st.session_state["ref"] = data["external_reference"]
            st.success("✅ QR generado")
        else:
            st.error("❌ Error generando QR")

# -------------------------
# Auto refresh si hay ref
# -------------------------
if st.session_state["ref"]:
    st_autorefresh(interval=3000, key="polling")

# -------------------------
# Mostrar QR + estado
# -------------------------
if st.session_state["init_point"]:
    st.subheader("Escaneá para pagar")

    qr_url = (
        "https://api.qrserver.com/v1/create-qr-code/"
        f"?size=300x300&data={st.session_state['init_point']}"
    )
    st.image(qr_url)

    try:
        r = requests.get(
            f"{BACKEND_URL}/estado_qr/{st.session_state['ref']}",
            timeout=5
        )
        
        if r.status_code == 200:
            estado = r.json()
            status = estado.get("status", "pending")
        
            if status == "approved":
                st.success("✅ PAGO APROBADO")
                st.code(f"Transacción: {estado.get('transaction_id')}")
            elif status == "rejected":
                st.error("❌ PAGO RECHAZADO")
            else:
                st.info("⏳ Esperando pago...")
        else:
            st.info("⏳ Esperando confirmación...")
