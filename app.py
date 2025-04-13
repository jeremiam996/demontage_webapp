
import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import plotly.express as px

menu = st.sidebar.selectbox("📂 Bereich wählen", ["📋 Planung", "📊 Status", "🅿️ Parkplatz"])

FZ_FILE = "fahrzeuge_daten.csv"
USER_FILE = "user_db.csv"
KALENDER_FILE = "kalender_daten.csv"
PARKPLATZ_FILE = "parkplaetze.csv"

for file in [FZ_FILE, USER_FILE, KALENDER_FILE, PARKPLATZ_FILE]:
    if not os.path.exists(file):
        pd.DataFrame().to_csv(file, index=False)

fahrzeuge = pd.read_csv(FZ_FILE)
kalender = pd.read_csv(KALENDER_FILE)
parkplaetze = pd.read_csv(PARKPLATZ_FILE)

if menu == "📋 Planung":
    st.title("📋 Fahrzeugplanung & Kalender")
    with st.form("planung_formular"):
        fzg_nr = st.text_input("Fahrzeugnummer")
        schicht = st.selectbox("Geplante Schicht", ["Morgenschicht", "Spätschicht"])
        geplant_fuer = st.date_input("Geplantes Ankunftsdatum", value=datetime.today())
        platz = st.text_input("Geplanter Parkplatz (z. B. A1)")
        submitted = st.form_submit_button("Eintragen")
        if submitted and fzg_nr:
            fahrzeuge = fahrzeuge.append({
                "Fahrzeug": fzg_nr,
                "Ankunftszeit": "geplant",
                "Schicht": schicht,
                "Status": "Noch nicht begonnen",
                "Begonnen": False,
                "Hinzugefügt am": datetime.now(),
                "Parkplatz": platz,
                "Geplant für": geplant_fuer
            }, ignore_index=True)
            fahrzeuge.to_csv(FZ_FILE, index=False)
            st.success(f"Fahrzeug {fzg_nr} geplant für {geplant_fuer} auf Platz {platz}")
    st.subheader("🗓 Geplante Fahrzeuge (nächste 14 Tage)")
    upcoming = fahrzeuge[fahrzeuge["Geplant für"].notna()]
    upcoming["Geplant für"] = pd.to_datetime(upcoming["Geplant für"], errors="coerce")
    upcoming = upcoming[upcoming["Geplant für"] >= datetime.today()]
    st.dataframe(upcoming.sort_values("Geplant für"))

elif menu == "📊 Status":
    st.title("📊 Fortschritt & Übersicht")
    if not fahrzeuge.empty:
        fahrzeuge["Fortschritt"] = fahrzeuge["Status"].apply(
            lambda s: "Offen" if s == "Noch nicht begonnen" else
                      "Abgeschlossen" if s == "Karosserie zerlegt" else
                      "In Arbeit"
        )
        status_count = fahrzeuge["Fortschritt"].value_counts()
        fig = px.bar(status_count, x=status_count.index, y=status_count.values,
                     labels={"x": "Status", "y": "Anzahl"}, color=status_count.index)
        st.plotly_chart(fig)
        st.subheader("Alle Fahrzeuge")
        st.dataframe(fahrzeuge)

elif menu == "🅿️ Parkplatz":
    st.title("🅿️ Parkplatzübersicht")
    belegte_plaetze = fahrzeuge["Parkplatz"].dropna().unique()
    raster = [f"{reihe}{nr}" for reihe in ["A", "B", "C", "D"] for nr in range(1, 5)]
    cols = st.columns(4)
    for i, platz in enumerate(raster):
        belegt = platz in belegte_plaetze
        farbe = "🔴" if belegt else "🟢"
        with cols[i % 4]:
            st.markdown(f"{farbe} **{platz}**")
