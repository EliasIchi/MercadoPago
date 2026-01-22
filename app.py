import streamlit as st
import requests
from streamlit_autorefresh import st_autorefresh

BACKEND_URL = "https://mp-backend-4l3x.onrender.com"

st.set_page_config(page_title="Cobro con QR", layout="centered")
st.title("📲 Cobro con QR Mercado Pago")

# -------------------------
# Session state
# -------------------------
for key in ["init_point", "ref", "monto", "sonido_ok", "pago_realizado"]:
    if key not in st.session_state:
        if key == "monto":
            st.session_state[key] = 0
        elif key == "sonido_ok":
            st.session_state[key] = False
        elif key == "pago_realizado":
            st.session_state[key] = False
        else:
            st.session_state[key] = None

# -------------------------
# Función reiniciar cobro
# -------------------------
def nuevo_cobro():
    st.session_state["init_point"] = None
    st.session_state["ref"] = None
    st.session_state["sonido_ok"] = False
    st.session_state["pago_realizado"] = False
    st.session_state["monto"] = 0

# -------------------------
# Input de monto y generar QR
# -------------------------
if not st.session_state["init_point"] and not st.session_state["pago_realizado"]:
    monto = st.number_input("Monto a cobrar", min_value=1, step=100, format="%d", key="input_monto")
    st.session_state["monto"] = monto

    if st.button("Generar QR"):
        if monto <= 0:
            st.error("❌ Monto inválido")
        else:
            try:
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
            except Exception as e:
                st.error(f"❌ Error conectando con backend: {e}")

# -------------------------
# Autorefresh mientras haya QR activo
# -------------------------
if st.session_state["ref"] and st.session_state["init_point"]:
    st_autorefresh(interval=3000, key="polling")

# -------------------------
# Mostrar QR y monto mientras no se pague
# -------------------------
if st.session_state["init_point"]:
    st.markdown(
        f"""
        <div style="text-align:center;">
            <h3>💲 Monto a pagar: ${st.session_state['monto']:,}</h3>
            <img src="https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={st.session_state['init_point']}" />
        </div>
        """,
        unsafe_allow_html=True
    )

# -------------------------
# Chequear estado del pago
# -------------------------
if st.session_state["ref"] and not st.session_state["pago_realizado"]:
    try:
        r = requests.get(
            f"{BACKEND_URL}/estado_qr/{st.session_state['ref']}",
            timeout=5
        )

        if r.status_code == 200:
            estado = r.json()
            status = estado.get("status", "pending")
            transaction_id = estado.get("transaction_id", st.session_state["ref"])

            if status == "approved":
                st.session_state["init_point"] = None
                st.session_state["pago_realizado"] = True

                # Pantalla verde gigante
                st.markdown(
                    f"""
                    <div style="
                        background-color:#4CAF50;
                        color:white;
                        font-size:50px;
                        text-align:center;
                        padding:50px;
                        border-radius:20px;
                        margin-top:50px;
                    ">
                        ✅ PAGO APROBADO<br>
                        💰 Monto: ${st.session_state['monto']:,}<br>
                        🆔 Ref: {transaction_id}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # reproducir sonido solo una vez
                if not st.session_state["sonido_ok"]:
                    try:
                        with open("cash.wav", "rb") as audio_file:
                            st.audio(audio_file.read(), format="audio/wav")
                        st.session_state["sonido_ok"] = True
                    except:
                        pass

            elif status == "rejected":
                st.session_state["init_point"] = None
                st.session_state["pago_realizado"] = True

                # Pantalla roja gigante
                st.markdown(
                    f"""
                    <div style="
                        background-color:#f44336;
                        color:white;
                        font-size:50px;
                        text-align:center;
                        padding:50px;
                        border-radius:20px;
                        margin-top:50px;
                    ">
                        ❌ PAGO RECHAZADO<br>
                        🆔 Ref: {transaction_id}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        else:
            st.info("⏳ Esperando confirmación...")

    except Exception as e:
        st.warning(f"⏳ Aún no hay confirmación del pago: {e}")

# -------------------------
# Botón para nuevo cobro
# -------------------------
if st.session_state["pago_realizado"]:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💳 Nuevo cobro", on_click=nuevo_cobro):
        st.experimental_rerun()
