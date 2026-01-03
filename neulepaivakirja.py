import streamlit as st
import pandas as pd
import gspread
import requests
from google.oauth2.service_account import Credentials
from datetime import date

# --- ASETUKSET ---

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# --- APUFUNKTIOT ---

def get_sheet_client():
    """Yhdistää Google Sheetsiin."""
    if "gcp_service_account" in st.secrets:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    else:
        st.error("Google-tunnukset puuttuvat Secrets-asetuksista.")
        return None

def load_data(sheet_name):
    """Lataa datan."""
    client = get_sheet_client()
    if client:
        try:
            sh = client.open("Neulepäiväkirja")
            worksheet = sh.worksheet(sheet_name)
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except Exception as e:
            st.error(f"Virhe taulukon avaamisessa: {e}")
    return pd.DataFrame()

def add_row(sheet_name, row_data):
    """Lisää rivin."""
    client = get_sheet_client()
    if client:
        sh = client.open("Neulepäiväkirja")
        worksheet = sh.worksheet(sheet_name)
        worksheet.append_row(row_data)

def upload_image_to_imgbb(file_obj):
    """Lataa kuvan ImgBB-palveluun ja palauttaa linkin."""
    try:
        # Haetaan avain
        if "imgbb_api_key" not in st.secrets:
            st.error("ImgBB API-avain puuttuu asetuksista!")
            return "Virhe: Avain puuttuu"

        api_key = st.secrets["imgbb_api_key"]
        url = "https://api.imgbb.com/1/upload"
        
        # Valmistellaan lähetys
        payload = {
            "key": api_key,
        }
        files = {
            "image": file_obj.getvalue()
        }
        
        # Lähetetään
        response = requests.post(url, data=payload, files=files)
        
        if response.status_code == 200:
            json_data = response.json()
            # Haetaan 'url' data-objektin sisältä
            return json_data['data']['url']
        else:
            st.error(f"Virhe ImgBB-latauksessa: {response.status_code}")
            return "Latausvirhe"
            
    except Exception as e:
        st.error(f"Virhe: {e}")
        return "Virhe"

# --- KÄYTTÖLIITTYMÄ ---

st.set_page_config(page_title="Neulepäiväkirja", layout="wide")
st.title("🧶 Neulepäiväkirja")

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
            materiaali = st.text_input("Materiaali")
            paino = st.number_input("Paino (g)", min_value=0, step=50)
            hinta = st.number_input("Hinta (€)", min_value=0.0, step=0.5)
# Määritellään vaihtoehdot listana
        vahvuus_vaihtoehdot = [
            "Cobbweb (n. 1000m/100g)",
            "Lace (n. 800m/100g)",
            "Fingering (n. 400m/100g)",
            "Sport (n. 300m/100g)",
            "DK (n. 200-250m/100g)",
            "Worsted (n. 200m/100g)",
            "Aran (n. 150-180m/100g)",
            "Bulky/Chunky (n. 100-120m/100g)",
            "Super Bulky (n. 50-80m/100g)",
            
        ]
        
        # Luodaan alasvetovalikko
        vahvuus = st.selectbox("Vahvuus", vahvuus_vaihtoehdot)
        
        if st.form_submit_button("Tallenna lanka"):
            row = [str(osto_pvm), merkki, vari, materiaali, paino, hinta]
            add_row("Langat", row)
            st.success(f"Lisätty: {merkki}")

    st.divider()
    st.subheader("Varasto")
    df_langat = load_data("Langat")
    if not df_langat.empty:
        st.dataframe(df_langat)

# --- TAB 2: VALMIIT TYÖT ---
with tab2:
    st.header("Kirjaa valmistunut työ")
    types = ["Sukat", "Lapaset", "Pipo", "Paita", "Kaulaliina", "Muu"]
    
    with st.form("tyo_form", clear_on_submit=True):
        tyo_pvm = st.date_input("Valmistumispäivä")
        tyyppi = st.selectbox("Työn tyyppi", types)
        lanka_kaytetty = st.text_input("Käytetty lanka")
        menekki = st.number_input("Menekki (g)", min_value=0)
        lisatietoja = st.text_area("Muistiinpanot")
        
        uploaded_file = st.file_uploader("Kuva työstä", type=['png', 'jpg', 'jpeg'])
        
        if st.form_submit_button("Tallenna työ"):
            image_link = "Ei kuvaa"
            
            if uploaded_file is not None:
                with st.spinner('Ladataan kuvaa pilveen...'):
                    image_link = upload_image_to_imgbb(uploaded_file)
            
            row = [str(tyo_pvm), tyyppi, lanka_kaytetty, menekki, lisatietoja, image_link]
            add_row("Työt", row)
            
            if image_link.startswith("http"):
                st.success("Työ tallennettu!")
                st.image(image_link, width=200)
            else:
                st.warning("Työ tallennettu ilman kuvaa.")

# --- TAB 3: RAPORTIT ---
with tab3:
    st.header("Raportointi")
    
    col_a, col_b = st.columns(2)
    with col_a:
        start_date = pd.to_datetime(st.date_input("Alku", value=date(2025, 1, 1)))
    with col_b:
        end_date = pd.to_datetime(st.date_input("Loppu", value=date.today()))

    st.divider()
    
    st.subheader("🧶 Valmistuneet työt")
    df_tyot = load_data("Työt")
    
    if not df_tyot.empty:
        df_tyot['Valmistumispäivä'] = pd.to_datetime(df_tyot['Valmistumispäivä'])
        mask = (df_tyot['Valmistumispäivä'] >= start_date) & (df_tyot['Valmistumispäivä'] <= end_date)
        df_filtered = df_tyot.loc[mask]
        
        # Näytetään taulukko (piilotetaan raaka linkki jos halutaan siistimpi)
        st.dataframe(df_filtered)
        
        st.write("### Kuvagalleria")
        
        # Loopataan rivit ja näytetään kuvat
        # Käytetään sarakkeita (cols) jotta kuvat tulevat vierekkäin
        cols = st.columns(3)
        for index, row in df_filtered.iterrows():
            linkki = str(row['Kuvalinkki'])
            if linkki.startswith("http"):
                # Valitaan sarake (0, 1 tai 2) jakojäännöksellä
                with cols[index % 3]:
                    st.image(linkki, caption=f"{row['Työn tyyppi']} ({row['Valmistumispäivä'].date()})")
    else:
        st.write("Ei töitä valitulla ajanjaksolla.")






