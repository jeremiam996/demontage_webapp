import streamlit as st
import pandas as pd
import os
import datetime
import calendar
import qrcode
from fpdf import FPDF

USER_DB = "benutzer.csv"
DATEN_CSV = "fahrzeuge.csv"
HISTORIE_CSV = "historie.csv"
PARKPLATZ_CSV = "parkplaetze.csv"
KALENDER_CSV = "kalender.csv"
SUBTASK_CSV = "subtasks.csv"

@st.cache_data
def lade_benutzer():
    return pd.read_csv(USER_DB) if os.path.exists(USER_DB) else pd.DataFrame(columns=["nutzername", "passwort", "rolle", "name", "email"])
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
        txt = f"{row['Datum']} — {row['Fahrzeugnummer']} — {row['Änderung']} durch {row['Bearbeiter']}"
        pdf.multi_cell(0, 8, txt=txt)
    with open("historie_export.pdf", "wb") as f: pdf.output(f)
    with open("historie_export.pdf", "rb") as f:
        st.sidebar.download_button("📜 Historie PDF", f, file_name="historie_export.pdf")
def kalender_export():
    df = pd.read_csv(KALENDER_CSV) if os.path.exists(KALENDER_CSV) else pd.DataFrame()
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, "Kalenderübersicht Fahrzeuge", ln=True, align="C")
    for _, row in df.iterrows():
        pdf.cell(0, 8, f"{row['Geplant für']} – {row['Fahrzeugnummer']} – {row['Schicht']} – {row['Prioritaet']}", ln=True)
    pdf.output("kalender_export.pdf")
    with open("kalender_export.pdf", "rb") as f:
        st.sidebar.download_button("📅 Kalender PDF", f, file_name="kalender_export.pdf")

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
            else: st.error("❌ Falsches Passwort")
        else: st.error("❌ Nutzer nicht gefunden")
if "login" not in st.session_state:
    st.session_state.login = False
if not st.session_state.login:
    login()
    st.stop()

benutzer_df = lade_benutzer()
df = pd.read_csv(DATEN_CSV) if os.path.exists(DATEN_CSV) else pd.DataFrame(columns=["Fahrzeugnummer", "Status", "Fortschritt", "Prioritaet", "Bearbeiter", "Parkplatz"])
parkplaetze = pd.read_csv(PARKPLATZ_CSV) if os.path.exists(PARKPLATZ_CSV) else pd.DataFrame({"Platz": [f"P{n}" for n in range(1, 41)], "Belegt": [False]*40})

# 🚘 Fahrzeugverwaltung
st.title("🚗 Fahrzeugbearbeitung")
if not df.empty:
    index = st.selectbox("Fahrzeug wählen", df.index, format_func=lambda i: df.at[i, "Fahrzeugnummer"])
    status = st.selectbox("Status", ["Angekommen", "Check-In", "Demontage", "Sortierung", "Fertig"], index=0)
    prior = st.selectbox("Priorität", ["hoch", "mittel", "niedrig"], index=1)
    fortschritt = st.slider("Fortschritt %", 0, 100, int(df.at[index, "Fortschritt"] if pd.notna(df.at[index, "Fortschritt"]) else 0))
    bearbeiter = st.selectbox("Bearbeiter", ["-"] + benutzer_df[benutzer_df.rolle == "mitarbeiter"]["name"].tolist(), index=0)
    freie = parkplaetze[~parkplaetze.Belegt]["Platz"].tolist()
    aktuell = df.at[index, "Parkplatz"] if pd.notna(df.at[index, "Parkplatz"]) else ""
    alle = sorted(set(freie + [aktuell])) if aktuell else freie
    platzwahl = st.selectbox("🅿️ Parkplatz", alle, index=alle.index(aktuell) if aktuell in alle else 0)

    if st.button("💾 Speichern"):
        df.at[index, "Status"] = status
        df.at[index, "Prioritaet"] = prior
        df.at[index, "Fortschritt"] = fortschritt
        df.at[index, "Bearbeiter"] = bearbeiter if bearbeiter != "-" else ""
        df.at[index, "Parkplatz"] = platzwahl
        parkplaetze.loc[parkplaetze.Platz == platzwahl, "Belegt"] = True
        if aktuell and aktuell != platzwahl:
            parkplaetze.loc[parkplaetze.Platz == aktuell, "Belegt"] = False
        if status == "Fertig":
            parkplaetze.loc[parkplaetze.Platz == platzwahl, "Belegt"] = False
        df.to_csv(DATEN_CSV, index=False)
        parkplaetze.to_csv(PARKPLATZ_CSV, index=False)
        st.success("Fahrzeugdaten aktualisiert")

# 🧩 Subtasks je Fahrzeug
st.subheader("🧩 Aufgaben pro Fahrzeug")
sub_df = lade_subtasks()
fz = df.at[index, "Fahrzeugnummer"]
fz_tasks = sub_df[sub_df.Fahrzeugnummer == fz]
if not fz_tasks.empty:
    for i, row in fz_tasks.iterrows():
        cols = st.columns([3, 2, 2])
        with cols[0]:
            sub_df.at[i, "Aufgabe"] = st.text_input(f"Aufgabe {i}", row["Aufgabe"], key=f"a_{i}")
        with cols[1]:
            sub_df.at[i, "Status"] = st.selectbox("Status", ["offen", "in Arbeit", "erledigt"], index=["offen", "in Arbeit", "erledigt"].index(row["Status"]), key=f"s_{i}")
        with cols[2]:
            sub_df.at[i, "Prioritaet"] = st.selectbox("Prio", ["hoch", "mittel", "niedrig"], index=["hoch", "mittel", "niedrig"].index(row["Prioritaet"]), key=f"p_{i}")
if st.button("📌 Aufgaben speichern"):
    speichere_subtasks(sub_df)
    st.success("Aufgaben gespeichert")
with st.expander("➕ Neue Aufgabe"):
    neu = st.text_input("Neue Aufgabe")
    nprio = st.selectbox("Priorität", ["hoch", "mittel", "niedrig"])
    if st.button("✅ Hinzufügen"):
        new_entry = pd.DataFrame([[fz, neu, "offen", nprio]], columns=sub_df.columns)
        sub_df = pd.concat([sub_df, new_entry], ignore_index=True)
        speichere_subtasks(sub_df)
        st.success("Hinzugefügt")

# 📍 Parkübersicht
st.subheader("📍 Parkplatz Übersicht")
belegt = df.set_index("Parkplatz")["Fahrzeugnummer"].to_dict()
for i in range(0, len(parkplaetze), 10):
    cols = st.columns(10)
    for j, platz in enumerate(parkplaetze["Platz"][i:i+10]):
        with cols[j]:
            label = belegt.get(platz, "🟩 frei")
            st.markdown(f"**🟥 {platz}**\n{label}" if label != "🟩 frei" else platz)

# 📅 Kalender Monatsansicht
st.subheader("📅 Monatskalender")
kaldat = pd.read_csv(KALENDER_CSV) if os.path.exists(KALENDER_CSV) else pd.DataFrame(columns=["Fahrzeugnummer", "Geplant für", "Schicht", "Prioritaet"])
kaldat["Geplant für"] = pd.to_datetime(kaldat["Geplant für"], errors='coerce')
aktuell = datetime.date.today()
monat = kaldat[kaldat["Geplant für"].dt.month == aktuell.month]
kart = {day: [] for day in range(1, 32)}
for _, row in monat.iterrows():
    tag = row["Geplant für"].day
    farbe = "red" if row["Prioritaet"] == "hoch" else "orange" if row["Prioritaet"] == "mittel" else "green"
    kart[tag].append(f"<span style='color:{farbe}'>{row['Fahrzeugnummer']} ({row['Schicht']})</span>")
for woche in calendar.monthcalendar(aktuell.year, aktuell.month):
    cols = st.columns(7)
    for i, tag in enumerate(woche):
        with cols[i]:
            if tag > 0:
                st.markdown(f"### {tag}")
                for eintrag in kart[tag]:
                    st.markdown(eintrag, unsafe_allow_html=True)

# 📥 Excel-Import
st.subheader("📥 Fahrzeugdaten importieren")
up = st.file_uploader("Excel hochladen", type="xlsx")
if up:
    try:
        daten = pd.read_excel(up)
        daten["Bearbeiter"] = ""
        daten["Parkplatz"] = None
        freie = parkplaetze[~parkplaetze.Belegt].reset_index()
        for i in range(min(len(daten), len(freie))):
            daten.loc[i, "Parkplatz"] = freie.loc[i, "Platz"]
            parkplaetze.loc[freie.loc[i, "index"], "Belegt"] = True
        df = pd.concat([df, daten], ignore_index=True)
        df.to_csv(DATEN_CSV, index=False)
        parkplaetze.to_csv(PARKPLATZ_CSV, index=False)
        st.success("Import erfolgreich")
    except Exception as e:
        st.error(f"Fehler: {e}")




