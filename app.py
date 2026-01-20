import streamlit as st
import requests

# -------------------------
# Config Backend
# -------------------------
BACKEND_URL = "https://mp-backend-4l3x.onrender.com"

st.set_page_config(page_title="Cobro con QR", layout="centered")
st.title("📲 Cobro con QR Mercado Pago")

# -------------------------
# Inicializar session_state
# -------------------------
for key in ["init_point", "ref", "monto"]:
    if key not in st.session_state:
        st.session_state[key] = None

# -------------------------
# Input de monto
# -------------------------
monto = st.number_input("Monto a cobrar", min_value=1, step=100, format="%d")
st.session_state["monto"] = monto

# -------------------------
# Generar QR
# -------------------------
if st.button("Generar QR"):
    try:
        r = requests.post(f"{BACKEND_URL}/crear_qr", json={"monto": st.session_state["monto"]})
        data = r.json()
        st.session_state["init_point"] = data.get("init_point")
        st.session_state["ref"] = data.get("external_reference")
        st.success("✅ QR generado correctamente")
    except Exception as e:
        st.error(f"❌ Error generando QR: {e}")

# -------------------------
# Auto-refresh cada 3 segundos
# -------------------------
if st.session_state["ref"]:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=3000, limit=None, key="polling")

# -------------------------
# Mostrar QR y estado
# -------------------------
if st.session_state["init_point"]:
    st.subheader("Escaneá para pagar")
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={st.session_state['init_point']}"
    st.image(qr_url)

    try:
        estado = requests.get(f"{BACKEND_URL}/estado/{st.session_state['ref']}").json()
        status = estado.get("status", "pending")

        if status == "approved":
            st.success("✅ PAGO APROBADO")
            st.code(f"Transacción: {estado.get('transaction_id')}")

        elif status == "rejected":
            st.error("❌ PAGO RECHAZADO")
        else:
            st.info("⏳ Esperando pago...")

    except Exception as e:
        st.error(f"❌ Error consultando estado: {e}")
