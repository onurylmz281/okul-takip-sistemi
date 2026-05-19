import streamlit as st
from supabase import create_client, Client

# Sayfa Ayarları
st.set_page_config(page_title="Okul Takip Sistemi", layout="wide")

# Supabase Bağlantısı
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# Yan Menü (Sidebar) Oluşturma
st.sidebar.title("Menü")
menu = st.sidebar.radio("Sayfa Seçimi", ["Öğrenci Yönetimi", "LGS Takip"])

if menu == "Öğrenci Yönetimi":
    st.header("Sınıf ve Öğrenci Yönetimi")
    
    # Sınıf Seçimi
    siniflar = ["5-A", "6-A", "7-A", "8-A"] 
    secilen_sinif = st.selectbox("Sınıf Seçin", siniflar)
    
    st.subheader(f"{secilen_sinif} Sınıfına Öğrenci Ekle")
    
    # Öğrenci Ekleme Formu
    with st.form("ogrenci_ekle_form", clear_on_submit=True):
        yeni_ogrenci_ad = st.text_input("Öğrenci Adı Soyadı")
        submit = st.form_submit_button("Ekle")
        
        if submit and yeni_ogrenci_ad:
            supabase.table("ogrenciler").insert({"ad_soyad": yeni_ogrenci_ad, "sinif": secilen_sinif}).execute()
            st.success("Öğrenci sisteme kaydedildi.")
            
    st.divider()
    
    # Sınıf Listesi ve Profil Yönlendirmesi
    st.subheader(f"{secilen_sinif} Sınıfı Öğrenci Listesi")
    response = supabase.table("ogrenciler").select("*").eq("sinif", secilen_sinif).execute()
    ogrenciler = response.data
    
    if ogrenciler:
        ogrenci_isimleri = [ogr["ad_soyad"] for ogr in ogrenciler]
        secilen_ogrenci = st.selectbox("Profiline gitmek için bir öğrenci seçin", ["Seçiniz..."] + ogrenci_isimleri)
        
        if secilen_ogrenci != "Seçiniz...":
            st.info(f"Şu an {secilen_ogrenci} adlı öğrencinin profilindesiniz.")
            st.write("Bu alana öğrenciye ait kişisel bilgiler, mülakat kayıtları ve gelişim verileri eklenecektir.")
    else:
        st.warning("Bu sınıfta henüz kayıtlı öğrenci bulunmuyor.")

elif menu == "LGS Takip":
    st.header("LGS Deneme Takip Sistemi")
    st.write("Veri tabanı tabloları hazır. Bu ekranın arayüzü ve grafik kodları 3. adımda oluşturulacaktır.")
