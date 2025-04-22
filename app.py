import streamlit as st
import pandas as pd
import os
import datetime
import calendar
import qrcode
from fpdf import FPDF

# Pfade
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

def lade_fahrzeuge():
    return pd.read_csv(DATEN_CSV) if os.path.exists(DATEN_CSV) else pd.DataFrame(columns=["Fahrzeugnummer", "Status", "Fortschritt", "Prioritaet", "Bearbeiter", "Parkplatz"])

def lade_parkplaetze():
    if os.path.exists(PARKPLATZ_CSV):
        return pd.read_csv(PARKPLATZ_CSV)
    return pd.DataFrame({"Platz": [f"P{n}" for n in range(1, 41)], "Belegt": [False]*40})

def lade_kalender():
    return pd.read_csv(KALENDER_CSV) if os.path.exists(KALENDER_CSV) else pd.DataFrame(columns=["Fahrzeugnummer", "Geplant für", "Schicht", "Prioritaet"])

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
    df = lade_kalender()
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, "Kalenderübersicht Fahrzeuge", ln=True, align="C")
    for _, row in df.iterrows():
        pdf.cell(0, 8, f"{row['Geplant für']} – {row['Fahrzeugnummer']} – {row['Schicht']} – {row['Prioritaet']}", ln=True)
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
        if benutzername in df_benutzer.nutzername.values:
            user_row = df_benutzer[df_benutzer.nutzername == benutzername].iloc[0]
            if user_row.passwort == passwort:
                st.session_state.login = True
                st.session_state.nutzer = user_row.to_dict()
                st.experimental_rerun()
            else:
                st.error("❌ Falsches Passwort")
        else:
            st.error("❌ Nutzer nicht gefunden")
    st.stop()

st.sidebar.title("🚗 Navigation")
seiten = ["Fahrzeugbearbeitung", "Subtasks", "Kalender", "Parkkarte", "Import", "QR-Codes", "Export"]
if st.session_state["nutzer"]["rolle"] == "admin":
    seiten.append("Benutzerverwaltung")
seite = st.sidebar.radio("Seite auswählen", seiten)

if st.sidebar.button("🔒 Logout"):
    st.session_state.login = False
    st.experimental_rerun()

benutzer_df = lade_benutzer()
df = lade_fahrzeuge()
parkplaetze = lade_parkplaetze()

# Seiteninhalt
if seite == "Fahrzeugbearbeitung":
    st.title("🚗 Fahrzeugbearbeitung")
    if not df.empty:
        index = st.selectbox("Fahrzeug wählen", df.index, format_func=lambda i: df.at[i, "Fahrzeugnummer"])
        df.at[index, "Status"] = st.selectbox("Status", ["Angekommen", "Check-In", "Demontage", "Sortierung", "Fertig"], index=0)
        df.at[index, "Prioritaet"] = st.selectbox("Priorität", ["hoch", "mittel", "niedrig"], index=1)
        df.at[index, "Fortschritt"] = st.slider("Fortschritt %", 0, 100, int(df.at[index, "Fortschritt"]))
        df.at[index, "Bearbeiter"] = st.selectbox("Bearbeiter", ["-"] + benutzer_df[benutzer_df.rolle == "mitarbeiter"]["name"].tolist(), index=0)
        freie = parkplaetze[~parkplaetze.Belegt]["Platz"].tolist()
        aktuell = df.at[index, "Parkplatz"] if pd.notna(df.at[index, "Parkplatz"]) else ""
        alle = sorted(set(freie + [aktuell])) if aktuell else freie
        df.at[index, "Parkplatz"] = st.selectbox("🅿️ Parkplatz", alle, index=alle.index(aktuell) if aktuell in alle else 0)
        if st.button("💾 Speichern"):
            df.to_csv(DATEN_CSV, index=False)
            st.success("Gespeichert")

elif seite == "Subtasks":
    st.title("🧩 Aufgaben je Fahrzeug")
    sub_df = lade_subtasks()
    selected = st.selectbox("Fahrzeug wählen", df["Fahrzeugnummer"].unique())
    fz_tasks = sub_df[sub_df.Fahrzeugnummer == selected]
    for i, row in fz_tasks.iterrows():
        c1, c2, c3 = st.columns([4, 2, 2])
        with c1:
            sub_df.at[i, "Aufgabe"] = st.text_input(f"Aufgabe {i}", row["Aufgabe"], key=f"a{i}")
        with c2:
            sub_df.at[i, "Status"] = st.selectbox("Status", ["offen", "in Arbeit", "erledigt"], index=["offen", "in Arbeit", "erledigt"].index(row["Status"]), key=f"s{i}")
        with c3:
            sub_df.at[i, "Prioritaet"] = st.selectbox("Priorität", ["hoch", "mittel", "niedrig"], index=["hoch", "mittel", "niedrig"].index(row["Prioritaet"]), key=f"p{i}")
    if st.button("📌 Speichern"):
        speichere_subtasks(sub_df)
        st.success("Aufgaben gespeichert")

elif seite == "Kalender":
    st.title("📅 Monatskalender")
    kalender = lade_kalender()
    kalender["Geplant für"] = pd.to_datetime(kalender["Geplant für"], errors="coerce")
    aktuell = datetime.date.today()
    monat_df = kalender[kalender["Geplant für"].dt.month == aktuell.month]
    tage = {i: [] for i in range(1, 32)}
    for _, row in monat_df.iterrows():
        tag = row["Geplant für"].day
        farbe = "red" if row["Prioritaet"] == "hoch" else "orange" if row["Prioritaet"] == "mittel" else "green"
        eintrag = f"<span style='color:{farbe}'>{row['Fahrzeugnummer']} ({row['Schicht']})</span>"
        tage[tag].append(eintrag)
    for woche in calendar.monthcalendar(aktuell.year, aktuell.month):
        cols = st.columns(7)
        for i, tag in enumerate(woche):
            with cols[i]:
                if tag > 0:
                    st.markdown(f"### {tag}")
                    for eintrag in tage[tag]:
                        st.markdown(eintrag, unsafe_allow_html=True)

elif seite == "Parkkarte":
    st.title("📍 Parkplätze")
    belegung = df.set_index("Parkplatz")["Fahrzeugnummer"].to_dict()
    for i in range(0, len(parkplaetze), 10):
        cols = st.columns(10)
        for j, platz in enumerate(parkplaetze["Platz"][i:i+10]):
            with cols[j]:
                label = belegung.get(platz, "🟩 frei")
                st.markdown(f"**🟥 {platz}**\n{label}" if label != "🟩 frei" else platz)

elif seite == "Import":
    st.title("📥 Excel Import")
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

elif seite == "QR-Codes":
    st.title("📸 QR-Codes für Fahrzeuge")
    for _, row in df.iterrows():
        st.markdown(f"**{row['Fahrzeugnummer']}**")
        st.image(qrcode.make(row['Fahrzeugnummer']).resize((150, 150)))

elif seite == "Export":
    st.title("📤 Export")
    kalender_export()
    export_historie_pdf()

elif seite == "Benutzerverwaltung" and st.session_state["nutzer"]["rolle"] == "admin":
    st.subheader("👥 Benutzerverwaltung")
    benutzer_df = lade_benutzer()
    with st.expander("➕ Benutzer hinzufügen"):
        name = st.text_input("Name")
        user = st.text_input("Benutzername")
        pw = st.text_input("Passwort")
        mail = st.text_input("E-Mail")
        rolle = st.selectbox("Rolle", ["admin", "schichtleiter", "mitarbeiter"])
        if st.button("Benutzer speichern"):
            if user in benutzer_df.nutzername.values:
                st.warning("Benutzername existiert bereits")
            else:
                neu = pd.DataFrame([[user, pw, rolle, name, mail]], columns=benutzer_df.columns)
                benutzer_df = pd.concat([benutzer_df, neu], ignore_index=True)
                benutzer_df.to_csv(USER_DB, index=False)
                st.success("Benutzer hinzugefügt")

    with st.expander("❌ Benutzer löschen"):
        auswahl = st.selectbox("Benutzer wählen", benutzer_df.nutzername.tolist())
        if st.button("🗑️ Löschen"):
            benutzer_df = benutzer_df[benutzer_df.nutzername != auswahl]
            benutzer_df.to_csv(USER_DB, index=False)
            st.success("Benutzer gelöscht")

