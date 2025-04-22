import streamlit as st
import pandas as pd
import os
import datetime
from io import BytesIO
from werkzeug.security import generate_password_hash, check_password_hash

# -----------------------------
# Benutzerverwaltung
# -----------------------------
USER_DB = "benutzer.csv"

def lade_benutzer():
    if os.path.exists(USER_DB):
        return pd.read_csv(USER_DB)
    else:
        return pd.DataFrame(columns=["nutzername", "passwort_hash", "rolle", "name", "email"])

def speichere_benutzer(df):
    df.to_csv(USER_DB, index=False)

def login():
    st.sidebar.title("🔐 Login")
    nutzername = st.sidebar.text_input("Benutzername")
    passwort = st.sidebar.text_input("Passwort", type="password")
    if st.sidebar.button("Login"):
        df = lade_benutzer()
        if nutzername in df["nutzername"].values:
            row = df[df["nutzername"] == nutzername].iloc[0]
            if check_password_hash(row["passwort_hash"], passwort):
                st.session_state["login"] = True
                st.session_state["nutzer"] = row.to_dict()
            else:
                st.error("❌ Falsches Passwort")
        else:
            st.error("❌ Benutzername nicht gefunden")

if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    login()
    st.stop()

if st.sidebar.button("🚪 Logout"):
    st.session_state.clear()
    st.experimental_rerun()

rolle = st.session_state["nutzer"]["rolle"]

# -----------------------------
# Daten laden
# -----------------------------
DATEN_CSV = "fahrzeuge.csv"
PARKPLATZ_CSV = "parkplaetze.csv"
KALENDER_CSV = "kalender.csv"

def lade_csv(pfad, spalten):
    if os.path.exists(pfad):
        return pd.read_csv(pfad)
    else:
        return pd.DataFrame(columns=spalten)

df = lade_csv(DATEN_CSV, ["Fahrzeugnummer", "Status", "Bearbeitung gestartet", "Schicht", "Ankunft", "Parkplatz"])
parkplaetze = lade_csv(PARKPLATZ_CSV, ["Platz", "Belegt"])
kalender_df = lade_csv(KALENDER_CSV, ["Fahrzeug", "Datum", "Schicht"])

# -----------------------------
# App Navigation
# -----------------------------
st.sidebar.title(f"Willkommen {st.session_state['nutzer']['name']}")
seite = st.sidebar.radio("Navigation", ["Planung", "Status", "Parkkarte", "Kalender", "Export", "Admin"] if rolle == "admin" else ["Planung", "Status", "Kalender", "Export"])

# -----------------------------
# Seite: Planung
# -----------------------------
if seite == "Planung":
    st.header("📅 Fahrzeugplanung")

    uploaded_file = st.file_uploader("Excel-Datei mit Fahrzeugen hochladen", type=["xlsx"])
    if uploaded_file:
        neue_df = pd.read_excel(uploaded_file)
        neue_df["Status"] = "offen"
        neue_df["Bearbeitung gestartet"] = False
        freie = parkplaetze[parkplaetze.Belegt == False]
        for i, row in neue_df.iterrows():
            if i < len(freie):
                neue_df.at[i, "Parkplatz"] = freie.iloc[i]["Platz"]
                parkplaetze.loc[parkplaetze.Platz == freie.iloc[i]["Platz"], "Belegt"] = True
        df = pd.concat([df, neue_df], ignore_index=True)
        df.to_csv(DATEN_CSV, index=False)
        parkplaetze.to_csv(PARKPLATZ_CSV, index=False)
        st.success("Import erfolgreich und Fahrzeuge eingeplant ✅")

    st.dataframe(df)

# Weitere Seiten und Funktionen bleiben unverändert