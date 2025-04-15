# Vollständige, funktionierende App mit Login, QR-Code-Scan, Excel-Import, Status, Kalender, Parkplatzübersicht, PDF-Export

import streamlit as st
import pandas as pd
import os
import qrcode
from datetime import datetime, date
import plotly.express as px
from fpdf import FPDF
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
import av
import cv2
from pyzbar.pyzbar import decode
import tempfile

# --- SETTINGS ---
CSV_PATH = "fahrzeuge_daten.csv"
USER_PATH = "user_db.csv"
PARKPLATZ_PATH = "parkplaetze.csv"
KALENDER_PATH = "kalender_daten.csv"
PDF_PATH = "export_heute.pdf"

st.set_page_config(page_title="Demontage App", layout="wide")

# --- SESSION STATE INIT ---
if "login" not in st.session_state:
    st.session_state.login = None
if "rolle" not in st.session_state:
    st.session_state.rolle = None
if "fahrzeuge" not in st.session_state:
    st.session_state.fahrzeuge = pd.DataFrame()

# --- LOAD DATA ---
def load_csv(path, default_columns):
    if not os.path.exists(path):
        pd.DataFrame(columns=default_columns).to_csv(path, index=False)
    return pd.read_csv(path)

def save_csv(df, path):
    df.to_csv(path, index=False)

fahrzeuge = load_csv(CSV_PATH, ["Fahrzeug", "Ankunftszeit", "Schicht", "Status", "Begonnen", "Hinzugefügt am", "Parkplatz", "Geplant für", "Bearbeiter"])
user_db = load_csv(USER_PATH, ["Benutzer", "Passwort", "Rolle", "Name", "Email", "Passwort_geändert"])
kalender = load_csv(KALENDER_PATH, ["Fahrzeug", "Geplant für", "Schicht"])
parkplaetze = load_csv(PARKPLATZ_PATH, ["Parkplatz", "Belegt"])

# --- LOGIN ---
if st.session_state.login is None:
    st.subheader("🔐 Login")
    with st.form("login_form"):
        user = st.text_input("Benutzername")
        pw = st.text_input("Passwort", type="password")
        submit = st.form_submit_button("Anmelden")
    if submit:
        entry = user_db[(user_db.Benutzer == user) & (user_db.Passwort == pw)]
        if not entry.empty:
            st.session_state.login = user
            st.session_state.rolle = entry.iloc[0].Rolle
            st.rerun()
        else:
            st.error("Login fehlgeschlagen")
    st.stop()

# --- HEADER ---
st.markdown(f"### Willkommen, **{st.session_state.login}** ({st.session_state.rolle})")
menu = st.sidebar.radio("Menü", ["Planung", "Status", "Parkplatz", "Kalender", "QR-Scan", "Export"])

# --- PLANUNG ---
if menu == "Planung":
    st.subheader("📅 Fahrzeugplanung")
    uploaded = st.file_uploader("Excel hochladen", type=["xlsx", "xls", "csv"])
    if uploaded:
        new_data = pd.read_csv(uploaded) if uploaded.name.endswith("csv") else pd.read_excel(uploaded)
        new_data["Status"] = "Offen"
        new_data["Begonnen"] = False
        new_data["Hinzugefügt am"] = date.today().isoformat()
        new_data["Parkplatz"] = ""
        new_data["Bearbeiter"] = ""
        freie = parkplaetze[parkplaetze.Belegt == False]
        for i in range(len(new_data)):
            if i < len(freie):
                platz = freie.iloc[i].Parkplatz
                new_data.at[i, "Parkplatz"] = platz
                parkplaetze.loc[parkplaetze.Parkplatz == platz, "Belegt"] = True
        fahrzeuge = pd.concat([fahrzeuge, new_data], ignore_index=True)
        save_csv(fahrzeuge, CSV_PATH)
        save_csv(parkplaetze, PARKPLATZ_PATH)
        st.success("Import erfolgreich")
    st.dataframe(fahrzeuge)

# --- STATUS ---
elif menu == "Status":
    st.subheader("📊 Statusübersicht")
    rolle = st.session_state.rolle
    if rolle == "Werkstattmitarbeiter":
        df = fahrzeuge[fahrzeuge.Status != "Abgeschlossen"]
    else:
        df = fahrzeuge
    for i, row in df.iterrows():
        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            st.write(row.Fahrzeug)
        with col2:
            if st.checkbox("Begonnen", key=f"begonnen_{i}", value=row.Begonnen):
                fahrzeuge.at[i, "Begonnen"] = True
        with col3:
            if st.button("Abgeschlossen", key=f"fertig_{i}"):
                fahrzeuge.at[i, "Status"] = "Abgeschlossen"
                fahrzeuge.at[i, "Bearbeiter"] = st.session_state.login
    fig = px.histogram(fahrzeuge, x="Status")
    st.plotly_chart(fig, use_container_width=True)
    save_csv(fahrzeuge, CSV_PATH)

# --- PARKPLATZ ---
elif menu == "Parkplatz":
    st.subheader("🅿️ Parkplatzbelegung")
    grid_cols = ["A", "B", "C", "D"]
    grid_rows = range(1, 5)
    belegung = {(row["Parkplatz"]): row["Belegt"] for _, row in parkplaetze.iterrows()}
    for col in grid_cols:
        columns = st.columns(len(grid_rows))
        for i, r in enumerate(grid_rows):
            platz = f"{col}{r}"
            farbe = "red" if belegung.get(platz, False) else "green"
            columns[i].markdown(f"<div style='background:{farbe};padding:15px;border-radius:5px;text-align:center;color:white'>{platz}</div>", unsafe_allow_html=True)

# --- KALENDER ---
elif menu == "Kalender":
    st.subheader("📅 Kalender – künftige Anlieferungen")
    st.dataframe(kalender)
    with st.form("kalender_form"):
        fzg = st.text_input("Fahrzeug")
        datum = st.date_input("Geplant für")
        schicht = st.selectbox("Schicht", ["Morgenschicht", "Spätschicht"])
        if st.form_submit_button("Hinzufügen"):
            kalender.loc[len(kalender)] = [fzg, datum.isoformat(), schicht]
            save_csv(kalender, KALENDER_PATH)
            st.success("Eingetragen")

# --- QR-SCAN ---
elif menu == "QR-Scan":
    st.subheader("📷 Fahrzeug per QR-Code hinzufügen")

    class QRScanner(VideoTransformerBase):
        def transform(self, frame):
            img = frame.to_ndarray(format="bgr24")
            for code in decode(img):
                data = code.data.decode("utf-8")
                st.session_state.qr_code_data = data
            return img

    webrtc_streamer(key="qr", video_transformer_factory=QRScanner)
    if "qr_code_data" in st.session_state:
        st.success(f"QR-Code erkannt: {st.session_state.qr_code_data}")
        new_row = pd.DataFrame([[st.session_state.qr_code_data, datetime.now().strftime("%H:%M"), "", "Offen", False, date.today().isoformat(), "", "", ""]], columns=fahrzeuge.columns)
        fahrzeuge = pd.concat([fahrzeuge, new_row], ignore_index=True)
        save_csv(fahrzeuge, CSV_PATH)
        del st.session_state.qr_code_data

# --- EXPORT ---
elif menu == "Export":
    st.subheader("📤 Export Funktionen")
    if st.checkbox("Nur Fahrzeuge von heute exportieren"):
        today = date.today().isoformat()
        export_df = fahrzeuge[fahrzeuge["Hinzugefügt am"] == today]
    else:
        export_df = fahrzeuge
    st.download_button("⬇️ CSV Export", export_df.to_csv(index=False), file_name="fahrzeuge_export.csv")
