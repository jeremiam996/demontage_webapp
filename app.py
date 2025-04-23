import streamlit as st
import pandas as pd
import os
import datetime
import calendar
import qrcode
from fpdf import FPDF
import smtplib
from email.mime.text import MIMEText

# Pfade
USER_DB = "benutzer.csv"
DATEN_CSV = "fahrzeuge.csv"
HISTORIE_CSV = "historie.csv"
PARKPLATZ_CSV = "parkplaetze.csv"
KALENDER_CSV = "kalender.csv"
SUBTASK_CSV = "subtasks.csv"

SMTP_SERVER = "smtp.example.com"
SMTP_PORT = 587
SMTP_USER = "your@email.com"
SMTP_PASS = "password"

@st.cache_data
def lade_benutzer():
    return pd.read_csv(USER_DB) if os.path.exists(USER_DB) else pd.DataFrame(columns=["nutzername", "passwort", "rolle", "name", "email"])

@st.cache_data
def lade_subtasks():
    return pd.read_csv(SUBTASK_CSV) if os.path.exists(SUBTASK_CSV) else pd.DataFrame(columns=["Fahrzeugnummer", "Aufgabe", "Status", "Prioritaet"])

def sende_mail(empfaenger, betreff, nachricht):
    try:
        msg = MIMEText(nachricht)
        msg["Subject"] = betreff
        msg["From"] = SMTP_USER
        msg["To"] = empfaenger
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print("E-Mail Fehler:", e)
        return False

def pruefe_erinnerung():
    df = lade_subtasks()
    benutzer = lade_benutzer()
    df = df[df["Status"] != "erledigt"]
    df = df[df["Prioritaet"] == "hoch"]
    if not df.empty:
        for empfaenger in benutzer["email"].dropna().tolist():
            sende_mail(empfaenger, "Offene Hoch-Prioritätsaufgaben", "Bitte überprüfen Sie die Aufgabenliste")

@st.cache_data
def lade_fahrzeuge():
    if os.path.exists(DATEN_CSV):
        df = pd.read_csv(DATEN_CSV)
        for col in ["Fahrzeugnummer", "Status", "Fortschritt", "Prioritaet", "Bearbeiter", "Parkplatz"]:
            if col not in df.columns:
                df[col] = ""
        return df
    return pd.DataFrame(columns=["Fahrzeugnummer", "Status", "Fortschritt", "Prioritaet", "Bearbeiter", "Parkplatz"])

def lade_parkplaetze():
    if os.path.exists(PARKPLATZ_CSV):
        return pd.read_csv(PARKPLATZ_CSV)
    zeilen = ['A', 'B', 'C', 'D']
    spalten = range(1, 5)
    plaetze = [f"{z}{s}" for z in zeilen for s in spalten]
    return pd.DataFrame({"Platz": plaetze, "Belegt": [False] * len(plaetze)})

def visuelle_parkkarte(df):
    belegung = df.set_index("Parkplatz")["Fahrzeugnummer"].to_dict()
    for zeile in ['A', 'B', 'C', 'D']:
        cols = st.columns(4)
        for i, spalte in enumerate(range(1, 5)):
            platz = f"{zeile}{spalte}"
            with cols[i]:
                if platz in belegung:
                    st.markdown(f"### {platz} \n**{belegung[platz]}**", unsafe_allow_html=True)
                else:
                    st.markdown(f"### {platz} \n🟩 frei", unsafe_allow_html=True)

def lade_kalender():
    if os.path.exists(KALENDER_CSV):
        df = pd.read_csv(KALENDER_CSV)
        if "Geplant für" in df.columns:
            df["Geplant für"] = pd.to_datetime(df["Geplant für"], errors="coerce")
        return df
    return pd.DataFrame(columns=["Fahrzeugnummer", "Geplant für", "Schicht", "Prioritaet"])

def export_historie_pdf():
    if not os.path.exists(HISTORIE_CSV):
        return
    df = pd.read_csv(HISTORIE_CSV)
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", size=11)
    pdf.cell(200, 10, "Änderungshistorie", ln=True, align="C"); pdf.ln(5)
    for _, row in df.iterrows():
        txt = f"{row.get('Datum', '-')} — {row.get('Fahrzeugnummer', '-')} — {row.get('Änderung', '-')} durch {row.get('Bearbeiter', '-')}"
        pdf.multi_cell(0, 8, txt=txt)
    with open("historie_export.pdf", "wb") as f: pdf.output(f)
    with open("historie_export.pdf", "rb") as f:
        st.sidebar.download_button("📜 Historie PDF", f, file_name="historie_export.pdf")

def kalender_export():
    df = lade_kalender()
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, "Kalenderübersicht Fahrzeuge", ln=True, align="C")
    for _, row in df.iterrows():
        geplant = row.get("Geplant für", "-")
        fz = row.get("Fahrzeugnummer", "-")
        schicht = row.get("Schicht", "-")
        prio = row.get("Prioritaet", "-")
        pdf.cell(0, 8, f"{geplant} – {fz} – {schicht} – {prio}", ln=True)
    pdf.output("kalender_export.pdf")
    with open("kalender_export.pdf", "rb") as f:
        st.sidebar.download_button("📅 Kalender PDF", f, file_name="kalender_export.pdf")

if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.sidebar.title("🔐 Login")
    benutzername = st.sidebar.text_input("Benutzername")
    passwort = st.sidebar.text_input("Passwort", type="password")
    if st.sidebar.button("Login"):
        df_benutzer = lade_benutzer()
        if benutzername in df_benutzer["nutzername"].values:
            user_row = df_benutzer[df_benutzer["nutzername"] == benutzername]
            if not user_row.empty and user_row.iloc[0]["passwort"] == passwort:
                st.session_state.login = True
                st.session_state.nutzer = user_row.iloc[0].to_dict()
                st.experimental_rerun()
            else:
                st.error("❌ Falsches Passwort")
        else:
            st.error("❌ Nutzer nicht gefunden")
    st.stop()

# Nur Schichtleiter erhalten Erinnerung automatisch
if st.session_state["nutzer"]["rolle"] == "schichtleiter":
    pruefe_erinnerung()





