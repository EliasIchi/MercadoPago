import streamlit as st
import requests
import time

# -------------------------
# CONFIG BACKEND
# -------------------------
BACKEND_URL = "https://mp-backend-4l3x.onrender.com"

st.set_page_config(page_title="Cobro con QR", layout="centered")
st.title("📲 Cobro con QR Mercado Pago")

# -------------------------
# INICIALIZAR SESSION_STATE
# -------------------------
if "init_point" not in st.session_state:
    st.session_state["init_point"] = None

if "ref" not in st.session_state:
    st.session_state["ref"] = None

if "monto" not in st.session_state:
    st.session_state["monto"] = 0

# -------------------------
# INGRESO DE MONTO
# -------------------------
monto = st.number_input(
    "Monto a cobrar",
    min_value=1,
    step=100,
    format="%d"
)

st.session_state["monto"] = monto

# -------------------------
# GENERAR QR
# -------------------------
if st.button("Generar QR"):
    try:
        r = requests.post(
            f"{BACKEND_URL}/crear_qr",
            json={"monto": st.session_state["monto"]}
        )
        data = r.json()

        st.session_state["init_point"] = data.get("init_point")
        st.session_state["ref"] = data.get("external_reference")

        st.success("✅ QR generado correctamente")

    except Exception as e:
        st.error(f"❌ Error generando QR: {e}")

# -------------------------
# MOSTRAR QR Y CONSULTAR ESTADO
# -------------------------
if st.session_state["init_point"]:
    st.subheader("Escaneá para pagar")

    qr_url = (
        "https://api.qrserver.com/v1/create-qr-code/"
        f"?size=300x300&data={st.session_state['init_point']}"
    )
    st.image(qr_url)

    if st.session_state["ref"]:
        try:
            estado = requests.get(
                f"{BACKEND_URL}/estado/{st.session_state['ref']}"
            ).json()

            status = estado.get("status", "pending")

            if status == "approved":
                st.success("✅ PAGO APROBADO")
                st.code(f"Transacción: {estado.get('transaction_id')}")

            elif status == "rejected":
                st.error("❌ PAGO RECHAZADO")

            else:
                st.warning("⏳ Esperando pago...")
                # Refresca la página automáticamente para actualizar estado
                time.sleep(3)
                st.experimental_rerun()

        except Exception as e:
            st.error(f"❌ Error consultando estado: {e}")
