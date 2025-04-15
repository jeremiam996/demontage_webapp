
import streamlit as st
import pandas as pd
import qrcode
from PIL import Image
import io
import base64
import os
from datetime import datetime

st.set_page_config(page_title="Demontage App", layout="wide")

# CSV-Dateien
fahrzeug_file = "fahrzeuge_daten.csv"
user_file = "user_db.csv"
parkplatz_file = "parkplaetze.csv"
kalender_file = "kalender_daten.csv"

# Daten einlesen
def lade_daten():
    if os.path.exists(fahrzeug_file):
        df = pd.read_csv(fahrzeug_file)
    else:
        df = pd.DataFrame(columns=["Fahrzeug", "Ankunftszeit", "Schicht", "Status", "Begonnen", "Hinzugefügt am", "Parkplatz", "Geplant für", "Bearbeiter"])
    return df

def speichere_daten(df):
    df.to_csv(fahrzeug_file, index=False)

# Login
def login():
    users = pd.read_csv(user_file)
    username = st.sidebar.text_input("Benutzername")
    password = st.sidebar.text_input("Passwort", type="password")
    if st.sidebar.button("Login"):
        user = users[(users["Benutzer"] == username) & (users["Passwort"] == password)]
        if not user.empty:
            return user.iloc[0]["Rolle"]
        else:
            st.sidebar.error("Login fehlgeschlagen.")
            return None
    return None

rolle = login()
if rolle:
    st.sidebar.success(f"Eingeloggt als {rolle}")
    df = lade_daten()

    # QR aus Bild
    st.subheader("📷 Fahrzeug per QR-Bild hinzufügen")
    uploaded_qr = st.file_uploader("QR-Code Bild hochladen", type=["png", "jpg", "jpeg"])
    if uploaded_qr:
        try:
            import cv2
            import numpy as np
            from pyzbar.pyzbar import decode
            image = Image.open(uploaded_qr)
            img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            result = decode(img)
            if result:
                fahrzeug = result[0].data.decode("utf-8")
                neue_zeile = {"Fahrzeug": fahrzeug, "Ankunftszeit": datetime.now().strftime("%H:%M"),
                              "Schicht": "offen", "Status": "offen", "Begonnen": False, "Hinzugefügt am": datetime.now().date(),
                              "Parkplatz": "", "Geplant für": "", "Bearbeiter": ""}
                df = df.append(neue_zeile, ignore_index=True)
                speichere_daten(df)
                st.success(f"Fahrzeug {fahrzeug} hinzugefügt!")
            else:
                st.warning("Kein QR-Code erkannt.")
        except Exception as e:
            st.error("Fehler beim Verarbeiten des QR-Codes.")

    # Manuelle Eingabe
    st.subheader("🚗 Fahrzeug manuell hinzufügen")
    fzg = st.text_input("Fahrzeugnummer")
    if st.button("Hinzufügen"):
        neue_zeile = {"Fahrzeug": fzg, "Ankunftszeit": datetime.now().strftime("%H:%M"),
                      "Schicht": "offen", "Status": "offen", "Begonnen": False, "Hinzugefügt am": datetime.now().date(),
                      "Parkplatz": "", "Geplant für": "", "Bearbeiter": ""}
        df = df.append(neue_zeile, ignore_index=True)
        speichere_daten(df)
        st.success(f"Fahrzeug {fzg} hinzugefügt!")

    # Übersicht
    st.subheader("📋 Übersicht")
    st.dataframe(df)

else:
    st.warning("Bitte einloggen.")

