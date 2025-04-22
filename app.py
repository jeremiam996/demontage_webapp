# Komplette app.py mit vollem Funktionsumfang: Import, Bearbeitung, QR, Historie, Parkplatz, Status
import streamlit as st
import pandas as pd
import os
import smtplib
from email.message import EmailMessage
import datetime
import calendar
from fpdf import FPDF
import qrcode
from io import BytesIO

USER_DB = "benutzer.csv"
DATEN_CSV = "fahrzeuge.csv"
HISTORIE_CSV = "historie.csv"
KALENDER_CSV = "kalender.csv"
PARKPLATZ_CSV = "parkplaetze.csv"

@st.cache_data
def lade_benutzer():
    if os.path.exists(USER_DB):
        return pd.read_csv(USER_DB)
    return pd.DataFrame(columns=["nutzername", "passwort", "rolle", "name", "email"])

def sende_mail(empfaenger_liste, text):
    if not empfaenger_liste:
        return
    msg = EmailMessage()
    msg.set_content(text)
    msg["Subject"] = "Fahrzeugstatus aktualisiert"
    msg["From"] = "noreply@demontage.local"
    msg["To"] = ", ".join(empfaenger_liste)
    try:
        with smtplib.SMTP("localhost") as server:
            server.send_message(msg)
    except Exception as e:
        st.warning(f"Fehler beim Senden der E-Mail: {e}")

def generiere_qr(text):
    img = qrcode.make(text)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def export_historie_pdf():
    df = pd.read_csv(HISTORIE_CSV)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    pdf.cell(200, 10, "Änderungshistorie", ln=True, align="C")
    pdf.ln(5)
    for _, row in df.iterrows():
        text = f"{row['Datum']} — {row['Fahrzeugnummer']} — {row['Änderung']} durch {row['Bearbeiter']}"
        pdf.multi_cell(0, 8, txt=text)
    path = "historie_export.pdf"
    pdf.output(path)
    with open(path, "rb") as f:
        st.download_button("⬇️ Historie als PDF", f, file_name=path)

# Sidebar Tools
st.sidebar.title("🔧 Tools")
if st.sidebar.button("📜 Historie als PDF exportieren"):
    export_historie_pdf()
if st.sidebar.checkbox("📸 QR-Codes anzeigen"):
    if os.path.exists(DATEN_CSV):
        df_qr = pd.read_csv(DATEN_CSV)
        for _, row in df_qr.iterrows():
            st.markdown(f"**{row['Fahrzeugnummer']}**")
            st.image(generiere_qr(row['Fahrzeugnummer']), width=150)

# Daten laden
if os.path.exists(DATEN_CSV):
    df = pd.read_csv(DATEN_CSV)
else:
    df = pd.DataFrame(columns=["Fahrzeugnummer", "Status", "Fortschritt", "Prioritaet", "Bearbeiter", "Parkplatz"])

if os.path.exists(PARKPLATZ_CSV):
    parkplaetze = pd.read_csv(PARKPLATZ_CSV)
else:
    parkplaetze = pd.DataFrame({"Platz": [f"P{n}" for n in range(1, 51)], "Belegt": [False]*50})

benutzer_df = lade_benutzer()

st.title("🚗 Fahrzeugübersicht & Bearbeitung")
if not df.empty:
    index = st.selectbox("Fahrzeug auswählen", df.index, format_func=lambda i: df.at[i, "Fahrzeugnummer"])
    prior = st.selectbox("Priorität", ["hoch", "mittel", "niedrig"], index=["hoch", "mittel", "niedrig"].index(df.at[index, "Prioritaet"] if pd.notna(df.at[index, "Prioritaet"]) else "mittel"))
    status = st.selectbox("Status", ["Angekommen", "Check-In", "Demontage", "Sortierung", "Fertig"], index=0)
    fortschritt = st.slider("Fortschritt", 0, 100, int(df.at[index, "Fortschritt"]))
    bearbeiter = st.selectbox("Bearbeiter", ["-"] + benutzer_df[benutzer_df.rolle == "mitarbeiter"]["name"].tolist(), index=0)
    freie_pp = parkplaetze[~parkplaetze.Belegt]["Platz"].tolist()
    aktuelle_pp = df.at[index, "Parkplatz"] if pd.notna(df.at[index, "Parkplatz"]) else ""
    alle_pp = sorted(set([aktuelle_pp] + freie_pp)) if aktuelle_pp else freie_pp
    platzwahl = st.selectbox("🅿️ Parkplatz", alle_pp, index=alle_pp.index(aktuelle_pp) if aktuelle_pp in alle_pp else 0)

    if st.button("💾 Speichern"):
        df.at[index, "Prioritaet"] = prior
        df.at[index, "Status"] = status
        df.at[index, "Fortschritt"] = fortschritt
        df.at[index, "Bearbeiter"] = bearbeiter if bearbeiter != "-" else ""
        df.at[index, "Parkplatz"] = platzwahl
        parkplaetze.loc[parkplaetze.Platz == platzwahl, "Belegt"] = True
        if aktuelle_pp and aktuelle_pp != platzwahl:
            parkplaetze.loc[parkplaetze.Platz == aktuelle_pp, "Belegt"] = False
        if status == "Fertig":
            parkplaetze.loc[parkplaetze.Platz == platzwahl, "Belegt"] = False
        df.to_csv(DATEN_CSV, index=False)
        parkplaetze.to_csv(PARKPLATZ_CSV, index=False)
        st.success("Gespeichert!")

# Visuelle Parkkarte
st.subheader("📍 Parkübersicht")
platzliste = parkplaetze["Platz"].tolist()
belegung = df.set_index("Parkplatz")["Fahrzeugnummer"].to_dict()
for i in range(0, len(platzliste), 10):
    cols = st.columns(10)
    for j, platz in enumerate(platzliste[i:i+10]):
        mit = belegung.get(platz, "🟩 frei")
        with cols[j]:
            st.markdown(f"**🟥 {platz}**\n{mit}" if mit != "🟩 frei" else platz)

# Fahrzeugimport aus Excel
st.subheader("📥 Import Fahrzeugliste (Excel)")
upload = st.file_uploader("Excel mit Spalten: Fahrzeugnummer, Status, Prioritaet, Fortschritt", type="xlsx")
if upload:
    try:
        excel_df = pd.read_excel(upload)
        excel_df["Bearbeiter"] = ""
        freie = parkplaetze[~parkplaetze.Belegt].reset_index()
        for i in range(min(len(excel_df), len(freie))):
            excel_df.loc[i, "Parkplatz"] = freie.loc[i, "Platz"]
            parkplaetze.loc[freie.loc[i, "index"], "Belegt"] = True
        df = pd.concat([df, excel_df], ignore_index=True)
        df.to_csv(DATEN_CSV, index=False)
        parkplaetze.to_csv(PARKPLATZ_CSV, index=False)
        st.success("Import abgeschlossen.")
    except Exception as e:
        st.error(f"Fehler: {e}")


    except Exception as e:
        st.error(f"Fehler beim Importieren: {e}")


