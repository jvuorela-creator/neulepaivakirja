import streamlit as st
import pandas as pd
import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.service_account import Credentials
from datetime import date

# --- ASETUKSET ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_google_client():
    # MUUTOS: Luetaan tunnukset Streamlitin Secrets-muistista
    # Eikä paikallisesta tiedostosta.
    # st.secrets["gcp_service_account"] vastaa JSON-tiedoston sisältöä
    creds_dict = st.secrets["gcp_service_account"]
    
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client

# ... loppuosa koodista pysyy samana (load_data, add_row ja käyttöliittymä) ...
# Funktio datan hakemiseen
def load_data(sheet_name):
    client = get_google_client()
    try:
        sh = client.open("Neulepäiväkirja") # Taulukon nimi Google Drivessa
        worksheet = sh.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Virhe yhdistettäessä taulukkoon: {e}")
        return pd.DataFrame()

# Funktio datan lisäämiseen
def add_row(sheet_name, row_data):
    client = get_google_client()
    sh = client.open("Neulepäiväkirja")
    worksheet = sh.worksheet(sheet_name)
    worksheet.append_row(row_data)

# --- KÄYTTÖLIITTYMÄ ---

st.set_page_config(page_title="Neulepäiväkirja", layout="wide")
st.title("🧶 Neulepäiväkirja")

# Luodaan välilehdet
tab1, tab2, tab3 = st.tabs(["Lankavarasto (Ostot)", "Valmiit työt", "Raportit"])

# --- TAB 1: LANKAVARASTO ---
with tab1:
    st.header("Kirjaa uusi lankaostos")
    
    with st.form("lanka_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            osto_pvm = st.date_input("Ostopäivä", value=date.today())
            merkki = st.text_input("Langan merkki/nimi")
            vari = st.text_input("Väri/Värikoodi")
        with col2:
            materiaali = st.text_input("Materiaali (esim. 75% villa)")
            paino = st.number_input("Paino (g)", min_value=0, step=50)
            hinta = st.number_input("Hinta (€)", min_value=0.0, step=0.5)
        
        submitted_lanka = st.form_submit_button("Tallenna lanka")
        
        if submitted_lanka:
            # Tallenna Google Sheetiin (Välilehti: 'Langat')
            row = [str(osto_pvm), merkki, vari, materiaali, paino, hinta]
            add_row("Langat", row)
            st.success(f"Lisätty: {merkki} ({vari})")

    st.divider()
    st.subheader("Lankavaraston tilanne")
    df_langat = load_data("Langat")
    if not df_langat.empty:
        st.dataframe(df_langat)

# --- TAB 2: VALMIIT TYÖT ---
with tab2:
    st.header("Kirjaa valmistunut työ")
    
    types = ["Sukat", "Lapaset", "Pipo", "Paita", "Kaulaliina", "Muu"]
    
    with st.form("tyo_form", clear_on_submit=True):
        tyo_pvm = st.date_input("Valmistumispäivä", key="tyo_date")
        tyyppi = st.selectbox("Työn tyyppi", types)
        lanka_kaytetty = st.text_input("Käytetty lanka (Merkki/Väri)")
        menekki = st.number_input("Langan menekki (g)", min_value=0)
        lisatietoja = st.text_area("Muistiinpanot (puikkokoko, ohje...)")
        
        # Kuvan lataus
        uploaded_file = st.file_uploader("Lataa kuva työstä", type=['png', 'jpg', 'jpeg'])
        
        submitted_tyo = st.form_submit_button("Tallenna työ")
        
        if submitted_tyo:
            image_link = "Ei kuvaa"
            # Tässä olisi koodi kuvan tallennukseen Google Driveen API:n kautta
            # Yksinkertaistuksen vuoksi tässä esimerkissä emme aja varsinaista uploadia
            if uploaded_file is not None:
                image_link = f"Tallennettu: {uploaded_file.name}" 
                # Oikeassa toteutuksessa tässä kutsuttaisiin Drive API upload-funktiota
            
            row = [str(tyo_pvm), tyyppi, lanka_kaytetty, menekki, lisatietoja, image_link]
            add_row("Työt", row)
            st.success("Työ tallennettu onnistuneesti!")

# --- TAB 3: RAPORTIT ---
with tab3:
    st.header("Raportointi")
    
    st.info("Valitse ajanjakso tarkastellaksesi ostoja ja valmistuneita töitä.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        start_date = st.date_input("Alkupäivämäärä", value=date(2025, 1, 1))
    with col_b:
        end_date = st.date_input("Loppupäivämäärä", value=date.today())

    # Muutetaan pvm vertailukelpoiseksi
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    st.divider()
    
    # 1. LANKARAPORTTI
    st.subheader("📦 Ostetut langat valitulla ajanjaksolla")
    df_langat = load_data("Langat")
    
    if not df_langat.empty:
        # Varmistetaan että pvm-sarake on datetime-muodossa
        df_langat['Ostopäivä'] = pd.to_datetime(df_langat['Ostopäivä'])
        
        mask = (df_langat['Ostopäivä'] >= start_date) & (df_langat['Ostopäivä'] <= end_date)
        df_filtered_langat = df_langat.loc[mask]
        
        st.dataframe(df_filtered_langat)
        st.metric("Lankaa ostettu yhteensä (g)", f"{df_filtered_langat['Paino (g)'].sum()} g")
        st.metric("Rahaa käytetty (€)", f"{df_filtered_langat['Hinta (€)'].sum()} €")
    else:
        st.write("Ei dataa.")

    st.divider()

    # 2. TYÖRAPORTTI
    st.subheader("🧶 Valmistuneet työt valitulla ajanjaksolla")
    df_tyot = load_data("Työt")
    
    if not df_tyot.empty:
        df_tyot['Valmistumispäivä'] = pd.to_datetime(df_tyot['Valmistumispäivä'])
        
        mask_tyot = (df_tyot['Valmistumispäivä'] >= start_date) & (df_tyot['Valmistumispäivä'] <= end_date)
        df_filtered_tyot = df_tyot.loc[mask_tyot]
        
        st.dataframe(df_filtered_tyot)
        
        # Yhteenveto tyypeittäin
        st.write("**Yhteenveto tyypeittäin:**")
        st.bar_chart(df_filtered_tyot['Työn tyyppi'].value_counts())
    else:

        st.write("Ei valmistuneita töitä tällä ajanjaksolla.")
