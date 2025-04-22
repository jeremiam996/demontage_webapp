# Erweiterte app.py mit QR-Codes, Historie-Export, Mitarbeiterzuweisung, Status, Fortschritt, Kalender, PDF
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

@st.cache_data
def lade_benutzer():
    if os.path.exists(USER_DB):
        return pd.read_csv(USER_DB)
    return pd.DataFrame(columns=["nutzername", "passwort", "rolle", "name", "email"])

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

if os.path.exists(DATEN_CSV):
    df = pd.read_csv(DATEN_CSV)
else:
    df = pd.DataFrame(columns=["Fahrzeugnummer", "Status", "Bearbeitung gestartet", "Prioritaet", "Fortschritt"])

if not os.path.exists(HISTORIE_CSV):
    pd.DataFrame(columns=["Datum", "Fahrzeugnummer", "Änderung", "Bearbeiter"]).to_csv(HISTORIE_CSV, index=False)

if not os.path.exists(KALENDER_CSV):
    pd.DataFrame(columns=["Fahrzeugnummer", "Geplant für", "Schicht", "Prioritaet"]).to_csv(KALENDER_CSV, index=False)

st.title("🚗 Fahrzeugübersicht mit Priorisierung, Fortschritt & Kalender")

if "Prioritaet" not in df.columns:
    df["Prioritaet"] = "mittel"
if "Fortschritt" not in df.columns:
    df["Fortschritt"] = 0

prio_filter = st.selectbox("Nach Priorität filtern:", ["alle", "hoch", "mittel", "niedrig"])
zeige_df = df.copy()
if prio_filter != "alle":
    zeige_df = zeige_df[zeige_df["Prioritaet"] == prio_filter]
st.dataframe(zeige_df)

index = st.selectbox("Fahrzeug auswählen zur Bearbeitung:", df.index)
prior = st.selectbox("Priorität setzen:", ["hoch", "mittel", "niedrig"], index=["hoch", "mittel", "niedrig"].index(df.at[index, "Prioritaet"]))
fortschritt = st.slider("Fortschritt (%)", 0, 100, int(df.at[index, "Fortschritt"]))
geplant_datum = st.date_input("📅 Geplant für:", datetime.date.today())
schicht = st.selectbox("Schicht", ["Früh", "Spät", "Nacht"])

if st.button("✅ Änderungen speichern"):
    df.at[index, "Prioritaet"] = prior
    df.at[index, "Fortschritt"] = fortschritt
    df.to_csv(DATEN_CSV, index=False)

    kalender_df = pd.read_csv(KALENDER_CSV)
    kalender_df = kalender_df[kalender_df.Fahrzeugnummer != df.at[index, "Fahrzeugnummer"]]
    neuer_eintrag = pd.DataFrame([{
        "Fahrzeugnummer": df.at[index, "Fahrzeugnummer"],
        "Geplant für": geplant_datum,
        "Schicht": schicht,
        "Prioritaet": prior
    }])
    kalender_df = pd.concat([kalender_df, neuer_eintrag])
    kalender_df.to_csv(KALENDER_CSV, index=False)

    empfaenger = lade_benutzer().query("rolle == 'supervisor'")["email"].tolist()
    msg = f"Fahrzeug {df.at[index, 'Fahrzeugnummer']} aktualisiert:\nPriorität: {prior}\nFortschritt: {fortschritt}%\nGeplant für: {geplant_datum} ({schicht})"
    sende_mail(empfaenger, msg)
    st.success("Änderungen gespeichert und Benachrichtigung gesendet")

    historie_df = pd.read_csv(HISTORIE_CSV)
    historie_df = pd.concat([historie_df, pd.DataFrame([{"Datum": datetime.datetime.now(), "Fahrzeugnummer": df.at[index, "Fahrzeugnummer"], "Änderung": f"Priorität: {prior}, Fortschritt: {fortschritt}%", "Bearbeiter": st.session_state['nutzer']['name']}])])
    historie_df.to_csv(HISTORIE_CSV, index=False)

st.subheader("📊 Fortschrittsanzeige")
for i, row in zeige_df.iterrows():
    st.markdown(f"**{row['Fahrzeugnummer']}** — Priorität: {row['Prioritaet']}")
    st.progress(int(row["Fortschritt"]))

st.subheader("📆 Kalender Monatsansicht (farbig)")
kalender_df = pd.read_csv(KALENDER_CSV)
kalender_df["Geplant für"] = pd.to_datetime(kalender_df["Geplant für"])
aktuell = datetime.date.today()
monat_df = kalender_df[kalender_df["Geplant für"].dt.month == aktuell.month]

kalendertage = {day: [] for day in range(1, 32)}
for _, row in monat_df.iterrows():
    tag = row["Geplant für"].day
    style = ""
    if row["Prioritaet"] == "hoch":
        style = "color:red"
    elif row["Prioritaet"] == "mittel":
        style = "color:orange"
    elif row["Prioritaet"] == "niedrig":
        style = "color:green"
    eintrag = f"<span style='{style}'>{row['Fahrzeugnummer']} ({row['Schicht']})</span>"
    kalendertage[tag].append(eintrag)

for woche in calendar.monthcalendar(aktuell.year, aktuell.month):
    cols = st.columns(7)
    for i, tag in enumerate(woche):
        if tag > 0:
            with cols[i]:
                tag_datum = datetime.date(aktuell.year, aktuell.month, tag)
                if tag_datum < aktuell:
                    st.markdown(f"### ~~{tag}~~")
                else:
                    st.markdown(f"### {tag}")
                for eintrag in kalendertage.get(tag, []):
                    st.markdown(eintrag, unsafe_allow_html=True)

st.subheader("📜 Änderungshistorie")
historie_df = pd.read_csv(HISTORIE_CSV)
st.dataframe(historie_df.sort_values("Datum", ascending=False))

st.subheader("📄 PDF-Export Fahrzeugstatus")
if st.button("📥 Export als PDF"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Fahrzeugstatusbericht", ln=True, align="C")
    pdf.ln(10)
    for _, row in df.iterrows():
        text = f"{row['Fahrzeugnummer']} — Status: {row.get('Status','')}, Priorität: {row['Prioritaet']}, Fortschritt: {row['Fortschritt']}%"
        pdf.multi_cell(0, 10, txt=text)
    pdf_file = "fahrzeug_status.pdf"
    pdf.output(pdf_file)
    with open(pdf_file, "rb") as f:
        st.download_button("⬇️ PDF Herunterladen", f, file_name=pdf_file)

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

