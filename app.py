import streamlit as st
import pandas as pd
import os
import smtplib
from email.message import EmailMessage
import datetime
import calendar
import qrcode
from fpdf import FPDF
from io import BytesIO

USER_DB = "benutzer.csv"
DATEN_CSV = "fahrzeuge.csv"
HISTORIE_CSV = "historie.csv"
PARKPLATZ_CSV = "parkplaetze.csv"
KALENDER_CSV = "kalender.csv"
SUBTASK_CSV = "subtasks.csv"

@st.cache_data
def lade_benutzer():
    if os.path.exists(USER_DB):
        return pd.read_csv(USER_DB)
    return pd.DataFrame(columns=["nutzername", "passwort", "rolle", "name", "email"])

@st.cache_data
def lade_subtasks():
    return pd.read_csv(SUBTASK_CSV) if os.path.exists(SUBTASK_CSV) else pd.DataFrame(columns=["Fahrzeugnummer", "Aufgabe", "Status", "Prioritaet"])

def speichere_subtasks(df):
    df.to_csv(SUBTASK_CSV, index=False)

def export_historie_pdf():
    df = pd.read_csv(HISTORIE_CSV) if os.path.exists(HISTORIE_CSV) else pd.DataFrame()
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", size=11)
    pdf.cell(200, 10, "Änderungshistorie", ln=True, align="C"); pdf.ln(5)
    for _, row in df.iterrows():
        text = f"{row['Datum']} — {row['Fahrzeugnummer']} — {row['Änderung']} durch {row['Bearbeiter']}"
        pdf.multi_cell(0, 8, txt=text)
    path = "historie_export.pdf"; pdf.output(path)
    with open(path, "rb") as f:
        st.sidebar.download_button("⬇️ Historie als PDF", f, file_name=path)

def kalender_export():
    df = pd.read_csv(KALENDER_CSV) if os.path.exists(KALENDER_CSV) else pd.DataFrame()
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, "Kalenderübersicht Fahrzeuge", ln=True, align="C")
    pdf.ln(5)
    for _, row in df.iterrows():
        pdf.cell(0, 8, txt=f"{row['Geplant für']} – {row['Fahrzeugnummer']} – {row['Schicht']} – Prio: {row['Prioritaet']}", ln=True)
    pdf.output("kalender_export.pdf")
    with open("kalender_export.pdf", "rb") as f:
        st.sidebar.download_button("⬇️ Kalender-PDF", f, file_name="kalender.pdf")

def login():
    st.sidebar.title("🔐 Login")
    name = st.sidebar.text_input("Benutzername")
    pw = st.sidebar.text_input("Passwort", type="password")
    if st.sidebar.button("Login"):
        df = lade_benutzer()
        if name in df.nutzername.values:
            row = df[df.nutzername == name].iloc[0]
            if row.passwort == pw:
                st.session_state["login"] = True
                st.session_state["nutzer"] = row.to_dict()
            else:
                st.error("❌ Falsches Passwort")
        else:
            st.error("❌ Nutzer nicht gefunden")

if "login" not in st.session_state:
    st.session_state.login = False
if not st.session_state.login:
    login()
    st.stop()

# Admin: Benutzerverwaltung
if st.session_state["nutzer"]["rolle"] == "admin":
    st.sidebar.markdown("---")
    st.sidebar.subheader("👥 Benutzerverwaltung")
    benutzer_df = lade_benutzer()

    with st.sidebar.expander("➕ Benutzer hinzufügen"):
        new_name = st.text_input("Name")
        new_user = st.text_input("Benutzername")
        new_pw = st.text_input("Passwort")
        new_mail = st.text_input("Email")
        new_role = st.selectbox("Rolle", ["admin", "mitarbeiter"])
        if st.button("✅ Benutzer speichern"):
            if new_user in benutzer_df.nutzername.values:
                st.warning("Benutzername existiert bereits")
            else:
                new_entry = pd.DataFrame([[new_user, new_pw, new_role, new_name, new_mail]], columns=benutzer_df.columns)
                benutzer_df = pd.concat([benutzer_df, new_entry], ignore_index=True)
                benutzer_df.to_csv(USER_DB, index=False)
                st.success("Benutzer hinzugefügt")

    with st.sidebar.expander("❌ Benutzer löschen"):
        benutzer_auswahl = st.selectbox("Benutzer wählen", benutzer_df.nutzername.tolist())
        if st.button("🗑️ Löschen"):
            benutzer_df = benutzer_df[benutzer_df.nutzername != benutzer_auswahl]
            benutzer_df.to_csv(USER_DB, index=False)
            st.success("Benutzer gelöscht")



