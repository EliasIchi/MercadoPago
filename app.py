import streamlit as st
import requests
from streamlit_autorefresh import st_autorefresh

# -------------------------
# Config
# -------------------------
BACKEND_URL = "https://mp-backend-4l3x.onrender.com"

st.set_page_config(page_title="Cobro con QR", layout="centered")
st.title("📲 Cobro con QR Mercado Pago")

# -------------------------
# Session state
# -------------------------
if "init_point" not in st.session_state:
    st.session_state["init_point"] = None

if "ref" not in st.session_state:
    st.session_state["ref"] = None

if "monto" not in st.session_state:
    st.session_state["monto"] = 0

if "sonido_ok" not in st.session_state:
    st.session_state["sonido_ok"] = False

# -------------------------
# Input de monto
# -------------------------
monto = st.number_input("Monto a cobrar", min_value=1, step=100, format="%d")
st.session_state["monto"] = monto

# -------------------------
# Botón para generar QR
# -------------------------
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
if st.session_state["ref"]:
    st_autorefresh(interval=3000, key="polling")

# -------------------------
# Mostrar QR y estado del pago
# -------------------------
if st.session_state["init_point"]:

    st.subheader("Escaneá para pagar")
    st.markdown(f"### 💲 Monto a pagar: ${st.session_state['monto']:,}")

    qr_url = (
        "https://api.qrserver.com/v1/create-qr-code/"
        f"?size=300x300&data={st.session_state['init_point']}"
    )
    st.image(qr_url)

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

            # -------------------------
            # Pago aprobado
            # -------------------------
            if status == "approved":
                # Pantalla gigante verde
                st.markdown(
                    f"""
                    <div style="
                        background-color:#4CAF50;
                        color:white;
                        font-size:50px;
                        text-align:center;
                        padding:50px;
                        border-radius:20px;
                    ">
                        ✅ PAGO APROBADO<br>
                        💰 Monto: ${st.session_state['monto']:,}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Reproducir sonido solo una vez (PC)
                if not st.session_state["sonido_ok"]:
                    try:
                        with open("cash.wav", "rb") as audio_file:
                            st.audio(audio_file.read(), format="audio/wav")
                        st.session_state["sonido_ok"] = True
                    except:
                        pass  # si es móvil no pasa nada

                # Detener autorefresh / polling
                st.stop()

            # -------------------------
            # Pago rechazado
            # -------------------------
            elif status == "rejected":
                st.markdown(
                    f"""
                    <div style="
                        background-color:#f44336;
                        color:white;
                        font-size:50px;
                        text-align:center;
                        padding:50px;
                        border-radius:20px;
                    ">
                        ❌ PAGO RECHAZADO
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # -------------------------
            # Pago pendiente
            # -------------------------
            else:
                st.info("⏳ Esperando pago...")

        else:
            st.info("⏳ Esperando confirmación...")

    except Exception as e:
        st.warning(f"⏳ Aún no hay confirmación del pago: {e}")
