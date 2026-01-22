import streamlit as st
import requests
from streamlit_autorefresh import st_autorefresh

# -------------------------
# Config
# -------------------------
BACKEND_URL = "https://mp-backend-4l3x.onrender.com"

st.set_page_config(page_title="Cobro con QR", layout="centered")
st.title("📲 Cobro con QR Mercado Pago", anchor=None)

# -------------------------
# Session state
# -------------------------
for key in ["init_point", "ref", "monto", "sonido_ok"]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "monto" else 0
        if key == "sonido_ok":
            st.session_state[key] = False

# -------------------------
# Input de monto
# -------------------------
if st.session_state["init_point"] is None:
    monto = st.number_input("Monto a cobrar", min_value=1, step=100, format="%d", key="input_monto")
    st.session_state["monto"] = monto

# -------------------------
# Botón para generar QR
# -------------------------
if st.session_state["init_point"] is None and st.button("Generar QR"):
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
# Auto refresh mientras haya QR activo
# -------------------------
if st.session_state["ref"] and st.session_state["init_point"]:
    st_autorefresh(interval=3000, key="polling")

# -------------------------
# Mostrar QR y estado del pago
# -------------------------
if st.session_state["init_point"]:

    # Centrar todo usando HTML
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
    # Chequear estado del pago desde backend
    # -------------------------
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
                # Limpiar QR
                st.session_state["init_point"] = None

                # Pantalla gigante verde y centrada
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
                        pass  # si es móvil no pasa nada

                # detener polling
                st.stop()

            elif status == "rejected":
                # Limpiar QR
                st.session_state["init_point"] = None

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
                st.info("⏳ Esperando pago...")

        else:
            st.info("⏳ Esperando confirmación...")

    except Exception as e:
        st.warning(f"⏳ Aún no hay confirmación del pago: {e}")
