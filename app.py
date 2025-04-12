
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

# Uploadbereich für Excel-Dateien
st.header("🚗 Excel-Upload für angelieferte Fahrzeuge")
uploaded_file = st.file_uploader("Excel-Datei hochladen (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        df_upload = pd.read_excel(uploaded_file)
        st.subheader("Vorschau hochgeladener Daten")
        st.dataframe(df_upload)

        if st.button("In Tagesplanung übernehmen"):
            for _, row in df_upload.iterrows():
                try:
                    neues_fahrzeug = {
                        "Fahrzeug": int(row["Fahrzeugnummer"]),
                        "Ankunftszeit": row["Ankunftszeit"],
                        "Schicht": row["Schicht"],
                        "Status": "Noch nicht begonnen",
                        "Hinzugefügt am": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    st.session_state.fahrzeuge.append(neues_fahrzeug)
                except Exception as e:
                    st.warning(f"Fehler bei Zeile: {row} – {e}")
            pd.DataFrame(st.session_state.fahrzeuge).to_csv(datafile, index=False)
            st.success("Fahrzeuge aus Excel erfolgreich übernommen.")
    except Exception as e:
        st.error(f"Fehler beim Einlesen der Datei: {e}")

# Fahrzeugformular (manuell)
st.header("Fahrzeug manuell eingeben")
fahrzeugnummer = st.number_input("Fahrzeugnummer", min_value=1, step=1)
ankunft = st.time_input("Ankunftszeit", value=datetime.strptime("08:00", "%H:%M").time())
schicht = st.selectbox("Schicht", ["Morgenschicht", "Spätschicht"])

if st.button("Fahrzeug hinzufügen"):
    neues_fahrzeug = {
        "Fahrzeug": fahrzeugnummer,
        "Ankunftszeit": ankunft.strftime("%H:%M"),
        "Schicht": schicht,
        "Status": "Noch nicht begonnen",
        "Hinzugefügt am": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    st.session_state.fahrzeuge.append(neues_fahrzeug)
    pd.DataFrame(st.session_state.fahrzeuge).to_csv(datafile, index=False)
    st.success(f"Fahrzeug {fahrzeugnummer} gespeichert.")

# Fahrzeugstatus anzeigen und bearbeiten
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

# Neuladen-Button
if st.button("🔄 App neu laden"):
    st.experimental_rerun()
