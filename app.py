import streamlit as st
import pandas as pd
import os
import datetime
from io import BytesIO

# -----------------------------
# Benutzerverwaltung
# -----------------------------
USER_DB = "benutzer.csv"

def lade_benutzer():
    if os.path.exists(USER_DB):
        return pd.read_csv(USER_DB)
    else:
        return pd.DataFrame(columns=["nutzername", "passwort", "rolle", "name", "email"])

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
            if row["passwort"] == passwort:
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

if os.path.exists(DATEN_CSV):
    df = pd.read_csv(DATEN_CSV)
else:
    df = pd.DataFrame(columns=["Fahrzeugnummer", "Status", "Bearbeitung gestartet", "Schicht", "Ankunft", "Parkplatz"])

if os.path.exists(PARKPLATZ_CSV):
    parkplaetze = pd.read_csv(PARKPLATZ_CSV)
else:
    parkplaetze = pd.DataFrame({"Platz": [f"{chr(r)}{n}" for r in range(65, 69) for n in range(1, 5)], "Belegt": [False]*16})

if os.path.exists(KALENDER_CSV):
    kalender_df = pd.read_csv(KALENDER_CSV)
else:
    kalender_df = pd.DataFrame(columns=["Fahrzeug", "Datum", "Schicht"])

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

# -----------------------------
# Seite: Status
# -----------------------------
elif seite == "Status":
    st.header("🛠️ Fahrzeugstatus")

    if rolle != "admin":
        df = df[df["Status"] != "abgeschlossen"]

    for i, row in df.iterrows():
        cols = st.columns([3, 2, 2, 2, 2])
        cols[0].markdown(f"**{row['Fahrzeugnummer']}**")
        cols[1].markdown(f"Status: {row['Status']}")
        gestartet = cols[2].checkbox("Gestartet", value=row["Bearbeitung gestartet"], key=f"start_{i}")
        if cols[3].button("Abschließen", key=f"done_{i}"):
            df.at[i, "Status"] = "abgeschlossen"
        df.at[i, "Bearbeitung gestartet"] = gestartet

        if gestartet:
            cols[4].markdown("✅ Schritte: Eingang ✅ - Prüfung ⬜ - Ausbau ⬜ - Abschluss ⬜")

    df.to_csv(DATEN_CSV, index=False)

# -----------------------------
# Seite: Parkkarte
# -----------------------------
elif seite == "Parkkarte":
    st.header("🅿️ Parkplatzübersicht")
    for i in range(4):
        cols = st.columns(4)
        for j in range(4):
            platz = f"{chr(65+i)}{j+1}"
            belegt = False
            if not parkplaetze[parkplaetze.Platz == platz].empty:
                belegt = parkplaetze[parkplaetze.Platz == platz]["Belegt"].iloc[0]
            farbe = "red" if belegt else "green"
            cols[j].markdown(f"<div style='background-color:{farbe};color:white;padding:10px;text-align:center;border-radius:10px'>{platz}</div>", unsafe_allow_html=True)

# -----------------------------
# Seite: Kalender
# -----------------------------
elif seite == "Kalender":
    st.header("📆 Geplante Fahrzeuge")
    st.dataframe(kalender_df)

    tag = st.date_input("Tag auswählen zur Anzeige")
    if not kalender_df.empty:
        geplante = kalender_df[kalender_df["Datum"] == tag.isoformat()]
        st.subheader("Fahrzeuge an diesem Tag")
        st.dataframe(geplante)

    with st.form("kalender_form"):
        fzg = st.text_input("Fahrzeug")
        datum = st.date_input("Geplant für")
        schicht = st.selectbox("Schicht", ["Morgenschicht", "Spätschicht"])
        speichern = st.form_submit_button("Eintragen")
        if speichern:
            kalender_df = pd.concat([kalender_df, pd.DataFrame([[fzg, datum.isoformat(), schicht]], columns=kalender_df.columns)])
            kalender_df.to_csv(KALENDER_CSV, index=False)
            st.success("Eingetragen ✅")

    if rolle in ["admin", "schichtleiter"] and not kalender_df.empty:
        st.subheader("🚚 Eintrag verschieben")
        auszuwahl = kalender_df["Fahrzeug"].unique().tolist()
        zu_verschieben = st.selectbox("Fahrzeug auswählen", auszuwahl)
        neues_datum = st.date_input("Neues Datum")
        neue_schicht = st.selectbox("Neue Schicht", ["Morgenschicht", "Spätschicht"])
        if st.button("Verschieben"):
            kalender_df.loc[kalender_df["Fahrzeug"] == zu_verschieben, ["Datum", "Schicht"]] = [neues_datum.isoformat(), neue_schicht]
            kalender_df.to_csv(KALENDER_CSV, index=False)
            st.success("Eintrag aktualisiert ✅")


# -----------------------------
# Seite: Export
# -----------------------------
elif seite == "Export":
    st.header("📤 Export")
    nur_heute = st.checkbox("Nur heutige Fahrzeuge exportieren")
    export_df = df.copy()
    if nur_heute:
        export_df = export_df[export_df["Ankunft"] == datetime.date.today().isoformat()]

    if not export_df.empty:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            export_df.to_excel(writer, index=False, sheet_name="Fahrzeuge")
        st.download_button("⬇️ Excel-Datei herunterladen", data=output.getvalue(), file_name="fahrzeuge_export.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("Keine Daten zum Export verfügbar.")

# -----------------------------
# Seite: Admin
# -----------------------------
if seite == "Admin" and rolle == "admin":
    st.header("👥 Benutzerverwaltung")
    benutzer_df = lade_benutzer()
    with st.form("Neuen Benutzer anlegen"):
        name = st.text_input("Name")
        mail = st.text_input("E-Mail")
        nutzername = st.text_input("Nutzername")
        passwort = st.text_input("Standardpasswort")
        rolle = st.selectbox("Rolle", ["admin", "werkstatt"])
        senden = st.form_submit_button("Benutzer speichern")
        if senden:
            benutzer_df = pd.concat([benutzer_df, pd.DataFrame([[nutzername, passwort, rolle, name, mail]], columns=benutzer_df.columns)])
            speichere_benutzer(benutzer_df)
            st.success("Benutzer gespeichert ✅")




# ----------------------------------------
# Erweiterung: Visuelle Erinnerung & Filter
# ----------------------------------------

if seite == "Planung":
    ...

    # Filteroptionen
    schicht_filter = st.selectbox("Nach Schicht filtern", ["Alle"] + df["Schicht"].dropna().unique().tolist())
    bearbeiter_filter = st.selectbox("Nach Bearbeiter filtern", ["Alle"] + df["Bearbeiter"].dropna().unique().tolist())

    if schicht_filter != "Alle":
        df = df[df["Schicht"] == schicht_filter]
    if bearbeiter_filter != "Alle":
        df = df[df["Bearbeiter"] == bearbeiter_filter]

    st.markdown("### 🔔 Visuelle Erinnerung: Offene Fahrzeuge ohne Bearbeitung")
    offene = df[(df["Status"] == "offen") & (df["Bearbeitung gestartet"] == False)]
    if not offene.empty:
        st.warning(f"⚠️ {len(offene)} Fahrzeuge sind noch nicht in Bearbeitung gestartet.")
    else:
        st.success("✅ Alle Fahrzeuge wurden bereits begonnen oder abgeschlossen.")







# -----------------------------
# Erweiterung: Fortschrittsanzeige
# -----------------------------
def berechne_fortschritt(zeile):
    schritte = ["Öl ablassen", "Batterie entfernen", "Flüssigkeiten trennen", "Ausbau", "Abschluss"]
    erledigt = sum([1 for s in schritte if zeile.get(s)])
    return int((erledigt / len(schritte)) * 100)

# -----------------------------
# Erweiterung: Protokollierung
# -----------------------------
import csv
from datetime import datetime

def protokolliere_aenderung(fahrzeugnummer, feld, alt, neu, bearbeiter):
    with open("historie.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().isoformat(), fahrzeugnummer, feld, alt, neu, bearbeiter])

# Diese Funktionen kannst du dann z.B. in der Status-Seite verwenden:
# if alt != neu:
#     protokolliere_aenderung(row["Fahrzeugnummer"], "Status", alt, neu, nutzername)



