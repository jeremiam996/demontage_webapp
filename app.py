
import streamlit as st
import pandas as pd
import cv2
import numpy as np
from datetime import datetime
import os
import plotly.express as px
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration
import av

st.set_page_config(layout="wide")

# Benutzerverwaltung
user_db = {
    "schichtleiter": "pass123",
    "werkstatt": "1234"
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = ""

if not st.session_state.logged_in:
    st.title("🔐 Login")
    username = st.text_input("Benutzername")
    password = st.text_input("Passwort", type="password")
    if st.button("Einloggen"):
        if username in user_db and user_db[username] == password:
            st.session_state.logged_in = True
            st.session_state.user = username
            st.rerun()
        else:
            st.error("Benutzername oder Passwort falsch.")
    st.stop()

rolle = "Schichtleiter" if st.session_state.user == "schichtleiter" else "Werkstattmitarbeiter"
st.title("Demontageplanung – Automobil Kreislaufwirtschaft")

datafile = "fahrzeuge_daten.csv"
stationen = ['Flüssigkeiten ablassen', 'Batterie entfernen', 'Räder demontieren', 'Innenraumteile ausbauen', 'Karosserie zerlegen']

if 'fahrzeuge' not in st.session_state:
    if os.path.exists(datafile):
        st.session_state.fahrzeuge = pd.read_csv(datafile).to_dict(orient="records")
    else:
        st.session_state.fahrzeuge = []

def berechne_fortschritt(status):
    if status == "Noch nicht begonnen":
        return "Offen"
    elif status == "Karosserie zerlegt":
        return "Abgeschlossen"
    else:
        return "In Arbeit"

fortschrittsliste = [berechne_fortschritt(fzg["Status"]) for fzg in st.session_state.fahrzeuge]
gesamt = len(fortschrittsliste)
offen = fortschrittsliste.count("Offen")
in_arbeit = fortschrittsliste.count("In Arbeit")
abgeschlossen = fortschrittsliste.count("Abgeschlossen")

# Fortschrittsdiagramm
st.subheader("📊 Demontage-Fortschritt")
fig = px.bar(x=["Offen", "In Arbeit", "Abgeschlossen"],
             y=[offen, in_arbeit, abgeschlossen],
             labels={"x": "Status", "y": "Anzahl Fahrzeuge"},
             color=["Offen", "In Arbeit", "Abgeschlossen"],
             text=[offen, in_arbeit, abgeschlossen])
fig.update_layout(showlegend=False)
st.plotly_chart(fig, use_container_width=True)

# QR-Scan Webcam (OpenCV)
st.subheader("📷 Fahrzeug per QR-Code scannen")
if "qr_result" not in st.session_state:
    st.session_state.qr_result = ""

class QRProcessor(VideoProcessorBase):
    def __init__(self):
        self.detector = cv2.QRCodeDetector()

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        qr_data, bbox, _ = self.detector.detectAndDecode(img)
        if bbox is not None and qr_data:
            st.session_state.qr_result = qr_data
            for i in range(len(bbox)):
                pt1 = tuple(bbox[i][0])
                pt2 = tuple(bbox[(i + 1) % len(bbox)][0])
                cv2.line(img, (int(pt1[0]), int(pt1[1])), (int(pt2[0]), int(pt2[1])), (0, 255, 0), 2)
        return av.VideoFrame.from_ndarray(img, format="bgr24")

webrtc_streamer(
    key="qrscan",
    video_processor_factory=QRProcessor,
    rtc_configuration=RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}),
    media_stream_constraints={"video": True, "audio": False},
)

if st.session_state.qr_result:
    st.success(f"Erkannter QR-Code: {st.session_state.qr_result}")

# Fahrzeug hinzufügen
st.subheader("🚗 Fahrzeug hinzufügen")
fahrzeugnummer = st.text_input("Fahrzeugnummer", value=st.session_state.qr_result)
ankunft = st.time_input("Ankunftszeit", value=datetime.strptime("08:00", "%H:%M").time())
schicht = st.selectbox("Schicht", ["Morgenschicht", "Spätschicht"])

if st.button("➕ Fahrzeug speichern"):
    neues_fzg = {
        "Fahrzeug": int(fahrzeugnummer),
        "Ankunftszeit": ankunft.strftime("%H:%M"),
        "Schicht": schicht,
        "Status": "Noch nicht begonnen",
        "Begonnen": False,
        "Hinzugefügt am": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    st.session_state.fahrzeuge.append(neues_fzg)
    pd.DataFrame(st.session_state.fahrzeuge).to_csv(datafile, index=False)
    st.success(f"Fahrzeug {fahrzeugnummer} gespeichert.")
    st.session_state.qr_result = ""
    st.rerun()

# Statusübersicht
st.subheader("🔧 Fahrzeuge & Status")
anzeige_fahrzeuge = []
for i, fzg in enumerate(st.session_state.fahrzeuge):
    fortschritt = berechne_fortschritt(fzg["Status"])
    anzeigen = True
    if rolle == "Werkstattmitarbeiter" and fortschritt != "Offen":
        anzeigen = False
    if anzeigen:
        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
        with col1:
            st.markdown(f"**Fahrzeug {fzg['Fahrzeug']}**")
        with col2:
            st.markdown(f"Status: *{fzg['Status']}* ({fortschritt})")
        with col3:
            fzg["Begonnen"] = st.checkbox("Begonnen?", value=fzg.get("Begonnen", False), key=f"beginn_{i}")
        with col4:
            if fortschritt != "Abgeschlossen":
                if st.button("✅ Abschließen", key=f"abschliessen_{i}"):
                    status = fzg["Status"]
                    if status == "Noch nicht begonnen":
                        fzg["Status"] = stationen[0]
                    elif status in stationen:
                        idx = stationen.index(status)
                        if idx + 1 < len(stationen):
                            fzg["Status"] = stationen[idx + 1]
                        else:
                            fzg["Status"] = "Karosserie zerlegt"
                    pd.DataFrame(st.session_state.fahrzeuge).to_csv(datafile, index=False)
                    st.rerun()
        anzeige_fahrzeuge.append({**fzg, "Fortschritt": fortschritt})

if anzeige_fahrzeuge:
    st.dataframe(pd.DataFrame(anzeige_fahrzeuge))

if rolle == "Schichtleiter":
    if st.button("📤 Excel exportieren"):
        pd.DataFrame(st.session_state.fahrzeuge).to_excel("Demontage_Tagesplanung_WebApp.xlsx", index=False)
        st.success("Export abgeschlossen.")

