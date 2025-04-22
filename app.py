# 🚗 Komplette App: Login, QR, Fortschritt, Historie, Kalender, Subtasks, Parkplatzverwaltung
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
SUBTASK_CSV = "subtasks.csv"

@st.cache_data
def lade_benutzer():
    return pd.read_csv(USER_DB) if os.path.exists(USER_DB) else pd.DataFrame(columns=["nutzername", "passwort", "rolle", "name", "email"])

@st.cache_data
def lade_subtasks():
    return pd.read_csv(SUBTASK_CSV) if os.path.exists(SUBTASK_CSV) else pd.DataFrame(columns=["Fahrzeugnummer", "Aufgabe", "Status", "Prioritaet"])

def speichere_subtasks(df):
    df.to_csv(SUBTASK_CSV, index=False)

def lade_kalender():
    if os.path.exists(KALENDER_CSV):
        return pd.read_csv(KALENDER_CSV)
    return pd.DataFrame(columns=["Fahrzeugnummer", "Geplant für", "Schicht", "Prioritaet"])

def sende_mail(empfaenger_liste, text):
    msg = EmailMessage()
    msg.set_content(text)
    msg["Subject"] = "Fahrzeugstatus aktualisiert"
    msg["From"] = "noreply@demontage.local"
    msg["To"] = ", ".join(empfaenger_liste)
    try:
        with smtplib.SMTP("localhost") as server:
            server.send_message(msg)
    except:
        pass

def kalender_export():
    df = lade_kalender()
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
            user = df[df.nutzername == name].iloc[0]
            if user.passwort == pw:
                st.session_state["login"] = True
                st.session_state["nutzer"] = user.to_dict()
            else:
                st.error("❌ Falsches Passwort")
        else:
            st.error("❌ Nutzer nicht gefunden")

if "login" not in st.session_state:
    st.session_state.login = False
if not st.session_state.login:
    login()
    st.stop()

benutzer_df = lade_benutzer()
if os.path.exists(DATEN_CSV):
    df = pd.read_csv(DATEN_CSV)
else:
    df = pd.DataFrame(columns=["Fahrzeugnummer", "Status", "Fortschritt", "Prioritaet", "Bearbeiter", "Parkplatz"])

if os.path.exists(PARKPLATZ_CSV):
    parkplaetze = pd.read_csv(PARKPLATZ_CSV)
else:
    parkplaetze = pd.DataFrame({"Platz": [f"P{n}" for n in range(1, 51)], "Belegt": [False]*50})

# Sidebar: Tools
st.sidebar.title("🔧 Tools")
if st.sidebar.button("📜 Historie als PDF exportieren"):
    if os.path.exists(HISTORIE_CSV):
        dfh = pd.read_csv(HISTORIE_CSV)
        pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", size=11)
        pdf.cell(200, 10, "Änderungshistorie", ln=True, align="C"); pdf.ln(5)
        for _, row in dfh.iterrows():
            text = f"{row['Datum']} – {row['Fahrzeugnummer']} – {row['Änderung']} durch {row['Bearbeiter']}"
            pdf.multi_cell(0, 8, txt=text)
        path = "historie_export.pdf"; pdf.output(path)
        with open(path, "rb") as f:
            st.sidebar.download_button("⬇️ Historie-PDF", f, file_name=path)
if st.sidebar.checkbox("📸 QR-Codes anzeigen"):
    for _, row in df.iterrows():
        st.markdown(f"**{row['Fahrzeugnummer']}**")
        st.image(qrcode.make(row['Fahrzeugnummer']).resize((150,150)))

# Hauptbereich – Fahrzeugbearbeitung
st.title("🚘 Fahrzeugverwaltung inkl. Subtasks & Kalender")
if not df.empty:
    index = st.selectbox("Fahrzeug bearbeiten", df.index, format_func=lambda i: df.at[i, "Fahrzeugnummer"])
    prior = st.selectbox("Priorität", ["hoch", "mittel", "niedrig"], index=["hoch", "mittel", "niedrig"].index(df.at[index, "Prioritaet"] if pd.notna(df.at[index, "Prioritaet"]) else "mittel"))
    status = st.selectbox("Status", ["Angekommen", "Check-In", "Demontage", "Sortierung", "Fertig"])
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
        st.success("✅ Änderungen gespeichert")
        hist = pd.read_csv(HISTORIE_CSV) if os.path.exists(HISTORIE_CSV) else pd.DataFrame(columns=["Datum", "Fahrzeugnummer", "Änderung", "Bearbeiter"])
        hist = pd.concat([hist, pd.DataFrame([{ "Datum": datetime.datetime.now(), "Fahrzeugnummer": df.at[index, "Fahrzeugnummer"], "Änderung": f"Status: {status}, Fortschritt: {fortschritt}%, Prio: {prior}", "Bearbeiter": st.session_state['nutzer']['name']}])])
        hist.to_csv(HISTORIE_CSV, index=False)

# Fortschritt
st.subheader("📊 Fortschrittsanzeige")
for i, row in df.iterrows():
    st.markdown(f"**{row['Fahrzeugnummer']}** – {row['Status']} – {row['Bearbeiter']} – Prio: {row['Prioritaet']}")
    st.progress(int(row["Fortschritt"]))

# Kalenderanzeige
st.subheader("📆 Kalender Monatsansicht")
kalender_df = lade_kalender()
kalender_df["Geplant für"] = pd.to_datetime(kalender_df["Geplant für"])
aktuell = datetime.date.today()
monat_df = kalender_df[kalender_df["Geplant für"].dt.month == aktuell.month]
kalendertage = {day: [] for day in range(1, 32)}
for _, row in monat_df.iterrows():
    tag = row["Geplant für"].day
    farbe = "red" if row["Prioritaet"] == "hoch" else "orange" if row["Prioritaet"] == "mittel" else "green"
    eintrag = f"<span style='color:{farbe}'>{row['Fahrzeugnummer']} ({row['Schicht']})</span>"
    kalendertage[tag].append(eintrag)
for woche in calendar.monthcalendar(aktuell.year, aktuell.month):
    cols = st.columns(7)
    for i, tag in enumerate(woche):
        with cols[i]:
            if tag > 0:
                st.markdown(f"### {tag}")
                for eintrag in kalendertage[tag]:
                    st.markdown(eintrag, unsafe_allow_html=True)

# Parkkarte
st.subheader("📍 Parkübersicht")
platzliste = parkplaetze["Platz"].tolist()
belegung = df.set_index("Parkplatz")["Fahrzeugnummer"].to_dict()
for i in range(0, len(platzliste), 10):
    cols = st.columns(10)
    for j, platz in enumerate(platzliste[i:i+10]):
        with cols[j]:
            label = belegung.get(platz, "🟩 frei")
            st.markdown(f"**🟥 {platz}**\n{label}" if label != "🟩 frei" else platz)

# 📌 Subtasks-Verwaltung
st.subheader("🧩 Aufgabenverwaltung je Fahrzeug")
sub_df = lade_subtasks()
selected_fz = st.selectbox("Fahrzeug auswählen für Aufgaben", df["Fahrzeugnummer"].unique())
fz_tasks = sub_df[sub_df.Fahrzeugnummer == selected_fz]
if not fz_tasks.empty:
    for i, row in fz_tasks.iterrows():
        cols = st.columns([4, 2, 2])
        with cols[0]:
            new_task = st.text_input(f"Aufgabe {i}", row["Aufgabe"], key=f"task_{i}")
        with cols[1]:
            new_status = st.selectbox("Status", ["offen", "in Arbeit", "erledigt"], index=["offen", "in Arbeit", "erledigt"].index(row["Status"]), key=f"st_{i}")
        with cols[2]:
            new_prio = st.selectbox("Prio", ["hoch", "mittel", "niedrig"], index=["hoch", "mittel", "niedrig"].index(row["Prioritaet"]), key=f"pr_{i}")
        sub_df.at[i, "Aufgabe"] = new_task
        sub_df.at[i, "Status"] = new_status
        sub_df.at[i, "Prioritaet"] = new_prio
if st.button("📌 Aufgaben speichern"):
    speichere_subtasks(sub_df)
    st.success("Subtasks aktualisiert")
with st.expander("➕ Neue Aufgabe hinzufügen"):
    aufgabe = st.text_input("Neue Aufgabe")
    prio = st.selectbox("Prio", ["hoch", "mittel", "niedrig"])
    if st.button("✅ Aufgabe hinzufügen"):
        new = pd.DataFrame([[selected_fz, aufgabe, "offen", prio]], columns=["Fahrzeugnummer", "Aufgabe", "Status", "Prioritaet"])
        sub_df = pd.concat([sub_df, new], ignore_index=True)
        speichere_subtasks(sub_df)
        st.success("Aufgabe gespeichert")

# 📤 Kalenderexport
kalender_export()



