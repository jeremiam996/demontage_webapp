def login():
    st.sidebar.title("🔐 Login")
    nutzername = st.sidebar.text_input("Benutzername")
    passwort = st.sidebar.text_input("Passwort", type="password")
    
    if st.sidebar.button("Login"):
        df = lade_benutzer()
        
        # Sicherstellen, dass die Datei korrekt geladen wurde
        if "nutzername" not in df.columns or "passwort_hash" not in df.columns:
            st.error("❌ Die Datei `benutzer.csv` ist fehlerhaft. Erforderliche Spalten fehlen.")
            return

        # Überprüfen, ob der Benutzername existiert
        if nutzername not in df["nutzername"].values:
            st.error("❌ Benutzername nicht gefunden. Bitte überprüfe die Eingabe.")
            return

        # Laden der Benutzerinformationen
        row = df[df["nutzername"] == nutzername].iloc[0]
        
        # Passwort prüfen
        if check_password_hash(row["passwort_hash"], passwort):
            st.session_state["login"] = True
            st.session_state["nutzer"] = row.to_dict()
            st.success(f"✅ Willkommen, {row['name']}!")
        else:
            st.error("❌ Falsches Passwort.")