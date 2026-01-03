import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import date

# --- ASETUKSET ---

# 1. Määritä Googlen oikeudet (Scopes)
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# 2. KORVAA TÄHÄN OMA GOOGLE DRIVE -KANSION ID
# Löydät sen kansion osoiteriviltä selaimessa (litania lopussa)
DRIVE_FOLDER_ID = "1GeeN1EBiOEzIFlidWe-zGjOM8OX78Svp" 


# --- APUFUNKTIOT ---

def get_google_creds():
    """Hakee tunnukset Streamlitin Secrets-piilosta."""
    # Varmista, että Secretsissä on otsikko [gcp_service_account]
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return creds

def get_sheet_client():
    """Yhdistää Google Sheetsiin."""
    creds = get_google_creds()
    client = gspread.authorize(creds)
    return client

def load_data(sheet_name):
    """Lataa datan tietystä välilehdestä Pandas-taulukkoon."""
    client = get_sheet_client()
    try:
        sh = client.open("Neulepäiväkirja") # Taulukon nimi
        worksheet = sh.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Virhe yhdistettäessä taulukkoon: {e}")
        return pd.DataFrame()

def add_row(sheet_name, row_data):
    """Lisää uuden rivin taulukkoon."""
    client = get_sheet_client()
    sh = client.open("Neulepäiväkirja")
    worksheet = sh.worksheet(sheet_name)
    worksheet.append_row(row_data)

def upload_image_to_drive(file_obj):
    """Lataa kuvan Google Driveen ja palauttaa linkin."""
    try:
        creds = get_google_creds()
        service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {
            'name': file_obj.name,
            'parents': [DRIVE_FOLDER_ID]
        }
        
        media = MediaIoBaseUpload(file_obj, mimetype=file_obj.type)
        
        file = service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id, webViewLink'
        ).execute()
        
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"Virhe kuvan latauksessa: {e}")
        return "Virhe latauksessa"

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
    # Ladataan data vain jos välilehti on auki (optimointi)
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
            
            # Jos kuva on ladattu, lähetetään se Driveen
            if uploaded_file is not None:
                with st.spinner('Tallennetaan kuvaa pilveen...'):
                    image_link = upload_image_to_drive(uploaded_file)
            
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
        end_date = st

