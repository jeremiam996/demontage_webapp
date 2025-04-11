
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

st.title("Demontageplanung – Automobil Kreislaufwirtschaft")

# Initiale Daten
stationen = ['Flüssigkeiten ablassen', 'Batterie entfernen', 'Räder demontieren',
             'Innenraumteile ausbauen', 'Karosserie zerlegen']
zeit_pro_schritt = timedelta(minutes=45)
datafile = "fahrzeuge_daten.csv"

# Lade bestehende Daten (falls vorhanden)
if 'fahrzeuge' not in st.session_state:
    if os.path.exists(datafile):
        st.session_state.fahrzeuge = pd.read_csv(datafile).to_dict(orient="records")
    else:
        st.session_state.fahrzeuge = []

# Fahrzeugformular
st.header("Fahrzeug manuell eingeben")
fahrzeugnummer = st.number_input("Fahrzeugnummer", min_value=1, step=1)
ankunft = st.time_input("Ankunftszeit", value=datetime.strptime("08:00", "%H:%M").time())
schicht = st.selectbox("Schicht", ["Morgenschicht", "Spätschicht"])

if st.button("Fahrzeug hinzufügen"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    neues_fahrzeug = {
        "Fahrzeug": fahrzeugnummer,
        "Ankunftszeit": ankunft.strftime("%H:%M"),
        "Schicht": schicht,
        "Status": "Noch nicht begonnen",
        "Hinzugefügt am": timestamp
    }
    st.session_state.fahrzeuge.append(neues_fahrzeug)
    pd.DataFrame(st.session_state.fahrzeuge).to_csv(datafile, index=False)
    st.success(f"Fahrzeug {fahrzeugnummer} gespeichert um {timestamp}.")

# Fahrzeuge anzeigen und Status bearbeiten
st.header("Fahrzeuge & Status")
df_status = pd.DataFrame(st.session_state.fahrzeuge)

if not df_status.empty:
    for i, row in df_status.iterrows():
        status = st.selectbox(f"Status Fahrzeug {row['Fahrzeug']}",
                              ['Noch nicht begonnen'] + stationen + ['Karosserie zerlegt'],
                              index=(['Noch nicht begonnen'] + stationen + ['Karosserie zerlegt']).index(row['Status']) if 'Status' in row else 0,
                              key=f"status_{i}")
        st.session_state.fahrzeuge[i]["Status"] = status

    st.dataframe(pd.DataFrame(st.session_state.fahrzeuge))

    if st.button("Exportieren als Excel"):
        df_export = pd.DataFrame(st.session_state.fahrzeuge)
        df_export.to_excel("Demontage_Tagesplanung_WebApp.xlsx", index=False)
        st.success("Datei exportiert: Demontage_Tagesplanung_WebApp.xlsx")

    if st.button("Daten zurücksetzen"):
        st.session_state.fahrzeuge = []
        if os.path.exists(datafile):
            os.remove(datafile)
        st.success("Alle Daten wurden zurückgesetzt.")
else:
    st.info("Noch keine Fahrzeuge eingetragen.")
