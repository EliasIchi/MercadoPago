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
    # Monto grande centrado
    st.markdown(
        f"""
        <div style="text-align:center; font-size:32px; margin-bottom:20px;">
            💲 Monto a pagar: ${st.session_state['monto']:,}
        </div>
        """,
        unsafe_allow_html=True
    )

    # QR centrado
    qr_url = (
        "https://api.qrserver.com/v1/create-qr-code/"
        f"?size=300x300&data={st.session_state['init_point']}"
    )
    st.markdown(
        f'<div style="text-align:center;"><img src="{qr_url}"></div>',
        unsafe_allow_html=True
    )

    try:
        r = requests.get(
            f"{BACKEND_URL}/estado_qr/{st.session_state['ref']}",
            timeout=5
        )
        
        if r.status_code == 200:
            estado = r.json()
            status = estado.get("status", "pending")
        
            if status == "approved":
                # Pago aprobado grande y centrado
                st.markdown(
                    f"""
                    <div style="
                        text-align:center;
                        background-color:#4CAF50;
                        color:white;
                        font-size:50px;
                        padding:50px;
                        border-radius:20px;
                        margin-top:30px;
                    ">
                        ✅ PAGO APROBADO<br>
                        💰 Monto: ${st.session_state['monto']:,}<br>
                        🆔 Ref: {estado.get('transaction_id')}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            elif status == "rejected":
                st.markdown(
                    f"""
                    <div style="
                        text-align:center;
                        background-color:#f44336;
                        color:white;
                        font-size:50px;
                        padding:50px;
                        border-radius:20px;
                        margin-top:30px;
                    ">
                        ❌ PAGO RECHAZADO<br>
                        🆔 Ref: {estado.get('transaction_id')}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.info("⏳ Esperando pago...")
        else:
            st.info("⏳ Esperando confirmación...")
    except Exception as e:
        st.warning("⏳ Aún no hay confirmación del pago")
