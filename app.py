# Erweiterte app.py mit Freigabe-Logik, Abmelden bei "Fertig", QR, Parkkarte, Historie
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

st.sidebar.title("🔧 Export & QR")
if st.sidebar.button("Export Historie als PDF"):
    export_historie_pdf()

if st.sidebar.checkbox("Fahrzeug-QR-Codes anzeigen"):
    if os.path.exists(DATEN_CSV):
        df_qr = pd.read_csv(DATEN_CSV)
        for _, row in df_qr.iterrows():
            st.markdown(f"**{row['Fahrzeugnummer']}**")
            img_bytes = generiere_qr(row['Fahrzeugnummer'])
            st.image(img_bytes, width=150)

# 📥 Excel-Import für neue Fahrzeuge
st.subheader("📥 Fahrzeugdaten importieren")
upload = st.file_uploader("Excel-Datei hochladen (Fahrzeugnummer, Prioritaet, Status, Fortschritt)", type="xlsx")
if upload:
    try:
        excel_df = pd.read_excel(upload)
        excel_df["Bearbeitung gestartet"] = False
        excel_df["Bearbeiter"] = ""
        if os.path.exists(PARKPLATZ_CSV):
            parkplaetze = pd.read_csv(PARKPLATZ_CSV)
        else:
            parkplaetze = pd.DataFrame({"Platz": [f"P{n}" for n in range(1, 51)], "Belegt": [False]*50})

        freie = parkplaetze[~parkplaetze.Belegt].reset_index()
        for i in range(min(len(excel_df), len(freie))):
            excel_df.loc[i, "Parkplatz"] = freie.loc[i, "Platz"]
            parkplaetze.loc[freie.loc[i, "index"], "Belegt"] = True

        if os.path.exists(DATEN_CSV):
            df_alt = pd.read_csv(DATEN_CSV)
            df = pd.concat([df_alt, excel_df], ignore_index=True)
        else:
            df = excel_df

        # ⏹️ Abmelden: Fahrzeuge mit Status "Fertig" austragen & Parkplatz freigeben
        if "Status" in df.columns and "Parkplatz" in df.columns:
            fertig = df[df["Status"] == "Fertig"].copy()
            if not fertig.empty:
                st.warning("Folgende Fahrzeuge wurden abgeschlossen und entfernt:")
                st.dataframe(fertig)
                df = df[df["Status"] != "Fertig"]
                for platz in fertig["Parkplatz"]:
                    parkplaetze.loc[parkplaetze.Platz == platz, "Belegt"] = False

        df.to_csv(DATEN_CSV, index=False)
        parkplaetze.to_csv(PARKPLATZ_CSV, index=False)
        st.success("Fahrzeuge erfolgreich importiert, zugewiesen und abgeschlossen verarbeitet.")

        # 📍 Visuelle Parkkarte
        st.subheader("📍 Parkplatzübersicht")
        grid = parkplaetze["Platz"].tolist()
        belegung = df.set_index("Parkplatz")["Fahrzeugnummer"].to_dict()
        for i in range(0, len(grid), 10):
            cols = st.columns(10)
            for j, platz in enumerate(grid[i:i+10]):
                with cols[j]:
                    label = belegung.get(platz, "🟩 frei")
                    if label != "🟩 frei":
                        st.markdown(f"**🟥 {platz}**\n{label}")
                    else:
                        st.markdown(f"{platz}")

    except Exception as e:
        st.error(f"Fehler beim Importieren: {e}")


