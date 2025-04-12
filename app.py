
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

st.title("Demontageplanung – Automobil Kreislaufwirtschaft")

# Stationen
stationen = ['Flüssigkeiten ablassen', 'Batterie entfernen', 'Räder demontieren',
             'Innenraumteile ausbauen', 'Karosserie zerlegen']
datafile = "fahrzeuge_daten.csv"

# Session State laden
if 'fahrzeuge' not in st.session_state:
    if os.path.exists(datafile):
        st.session_state.fahrzeuge = pd.read_csv(datafile).to_dict(orient="records")
    else:
        st.session_state.fahrzeuge = []

# Fortschrittsstatus berechnen
def berechne_status(status):
    if status == 'Noch nicht begonnen':
        return 'Offen'
    elif status == 'Karosserie zerlegt':
        return 'Abgeschlossen'
    else:
        return 'In Arbeit'

# Statistik
fortschrittsliste = [berechne_status(fzg['Status']) for fzg in st.session_state.fahrzeuge]
gesamt = len(fortschrittsliste)
offen = fortschrittsliste.count('Offen')
in_arbeit = fortschrittsliste.count('In Arbeit')
abgeschlossen = fortschrittsliste.count('Abgeschlossen')

st.subheader("📊 Übersicht")
st.markdown(f"- Gesamt: **{gesamt}** Fahrzeuge")
st.markdown(f"- 🕒 Offen: **{offen}**, 🔧 In Arbeit: **{in_arbeit}**, ✅ Abgeschlossen: **{abgeschlossen}**")

# Filteroption
filter_option = st.selectbox("🔍 Filter", ["Alle", "Nur offene", "Nur in Arbeit", "Nur abgeschlossene"])

# Fahrzeugtabelle mit Fortschritt und Bearbeitungsoption
st.header("Fahrzeuge & Statusbearbeitung")

anzeige_daten = []
for i, fahrzeug in enumerate(st.session_state.fahrzeuge):
    fortschritt = berechne_status(fahrzeug['Status'])
    if (
        filter_option == "Alle"
        or (filter_option == "Nur offene" and fortschritt == "Offen")
        or (filter_option == "Nur in Arbeit" and fortschritt == "In Arbeit")
        or (filter_option == "Nur abgeschlossene" and fortschritt == "Abgeschlossen")
    ):
        col1, col2, col3 = st.columns([3, 4, 2])
        with col1:
            st.markdown(f"**Fahrzeug {fahrzeug['Fahrzeug']}**")
        with col2:
            st.markdown(f"Status: *{fahrzeug['Status']}* ({fortschritt})")
        with col3:
            if fortschritt != "Abgeschlossen":
                if st.button(f"✅ Schritt abschließen", key=f"abschliessen_{i}"):
                    aktueller_status = fahrzeug["Status"]
                    if aktueller_status == "Noch nicht begonnen":
                        st.session_state.fahrzeuge[i]["Status"] = stationen[0]
                    elif aktueller_status in stationen:
                        idx = stationen.index(aktueller_status)
                        if idx + 1 < len(stationen):
                            st.session_state.fahrzeuge[i]["Status"] = stationen[idx + 1]
                        else:
                            st.session_state.fahrzeuge[i]["Status"] = "Karosserie zerlegt"
                    pd.DataFrame(st.session_state.fahrzeuge).to_csv(datafile, index=False)
                    st.experimental_rerun()
        anzeige_daten.append({
            **fahrzeug,
            "Fortschritt": fortschritt
        })

if anzeige_daten:
    st.dataframe(pd.DataFrame(anzeige_daten))

# Neuladen
if st.button("🔄 App neu laden"):
    st.experimental_rerun()


# Neuladen-Button
if st.button("🔄 App neu laden"):
    st.experimental_rerun()
