
import streamlit as st
import pandas as pd
from datetime import datetime
import os
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

st.title("Demontageplanung – Automobil Kreislaufwirtschaft")

stationen = ['Flüssigkeiten ablassen', 'Batterie entfernen', 'Räder demontieren',
             'Innenraumteile ausbauen', 'Karosserie zerlegen']
datafile = "fahrzeuge_daten.csv"

# Benutzerrolle
rolle = st.sidebar.selectbox("🔐 Rolle wählen", ["Schichtleiter", "Werkstattmitarbeiter"])

# Lade gespeicherte Daten
if 'fahrzeuge' not in st.session_state:
    if os.path.exists(datafile):
        st.session_state.fahrzeuge = pd.read_csv(datafile).to_dict(orient="records")
    else:
        st.session_state.fahrzeuge = []

def berechne_fortschritt(status):
    if status == "Noch nicht begonnen":
        return "Offen"
    elif status == "Karosserie zerlegt":
        return "Abgeschlossen"
    else:
        return "In Arbeit"

# Sidebar-Statistik
fortschrittsliste = [berechne_fortschritt(fzg["Status"]) for fzg in st.session_state.fahrzeuge]
gesamt = len(fortschrittsliste)
offen = fortschrittsliste.count("Offen")
in_arbeit = fortschrittsliste.count("In Arbeit")
abgeschlossen = fortschrittsliste.count("Abgeschlossen")

st.sidebar.markdown(f"**📊 Übersicht**")
st.sidebar.markdown(f"- Gesamt: **{gesamt}**")
st.sidebar.markdown(f"- 🕒 Offen: **{offen}**")
st.sidebar.markdown(f"- 🔧 In Arbeit: **{in_arbeit}**")
st.sidebar.markdown(f"- ✅ Abgeschlossen: **{abgeschlossen}**")

# Diagramm anzeigen
with st.expander("📈 Fortschrittsdiagramm"):
    fig, ax = plt.subplots()
    ax.bar(["Offen", "In Arbeit", "Abgeschlossen"], [offen, in_arbeit, abgeschlossen])
    ax.set_ylabel("Anzahl Fahrzeuge")
    ax.set_title("Demontage-Fortschritt")
    st.pyplot(fig)

# Excel-Upload
st.header("📥 Excel-Import für angelieferte Fahrzeuge")
uploaded_file = st.file_uploader("Excel-Datei hochladen (.xlsx)", type=["xlsx"])
if uploaded_file:
    df_upload = pd.read_excel(uploaded_file)
    st.dataframe(df_upload)
    if st.button("In Planung übernehmen"):
        for _, row in df_upload.iterrows():
            neues_fahrzeug = {
                "Fahrzeug": int(row["Fahrzeugnummer"]),
                "Ankunftszeit": row["Ankunftszeit"],
                "Schicht": row["Schicht"],
                "Status": "Noch nicht begonnen",
                "Begonnen": False,
                "Hinzugefügt am": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            st.session_state.fahrzeuge.append(neues_fahrzeug)
        pd.DataFrame(st.session_state.fahrzeuge).to_csv(datafile, index=False)
        st.success("Import abgeschlossen.")
        st.experimental_rerun()

# Fahrzeuganzeige mit Rollenlogik
st.header("🚗 Fahrzeugstatus bearbeiten")

anzeige_fahrzeuge = []
for i, fzg in enumerate(st.session_state.fahrzeuge):
    fortschritt = berechne_fortschritt(fzg["Status"])
    anzeigen = True
    if rolle == "Werkstattmitarbeiter" and fortschritt != "Offen":
        anzeigen = False
    if anzeigen:
        col1, col2, col3, col4 = st.columns([2, 3, 3, 2])
        with col1:
            st.markdown(f"**Fahrzeug {fzg['Fahrzeug']}**")
        with col2:
            st.markdown(f"Status: *{fzg['Status']}* ({fortschritt})")
        with col3:
            fzg["Begonnen"] = st.checkbox("Begonnen?", value=fzg.get("Begonnen", False), key=f"beginn_{i}")
        with col4:
            if fortschritt != "Abgeschlossen":
                if st.button("✅ Abschließen", key=f"abschliessen_{i}"):
                    status = fzg["Status"]
                    if status == "Noch nicht begonnen":
                        fzg["Status"] = stationen[0]
                    elif status in stationen:
                        idx = stationen.index(status)
                        if idx + 1 < len(stationen):
                            fzg["Status"] = stationen[idx + 1]
                        else:
                            fzg["Status"] = "Karosserie zerlegt"
                    pd.DataFrame(st.session_state.fahrzeuge).to_csv(datafile, index=False)
                    st.experimental_rerun()
        anzeige_fahrzeuge.append({**fzg, "Fortschritt": fortschritt})

if anzeige_fahrzeuge:
    st.dataframe(pd.DataFrame(anzeige_fahrzeuge))

# Export
if rolle == "Schichtleiter":
    if st.button("📤 Excel exportieren"):
        pd.DataFrame(st.session_state.fahrzeuge).to_excel("Demontage_Tagesplanung_WebApp.xlsx", index=False)
        st.success("Export abgeschlossen.")

# App neuladen
if st.button("🔄 App neu laden"):
    st.experimental_rerun()

