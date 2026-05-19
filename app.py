import streamlit as st
import pandas as pd
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

# Yan Menü (Sidebar)
st.sidebar.title("Sistem Ayarları")
branslar = ["Matematik", "Türkçe", "Fen Bilimleri", "Sosyal Bilgiler", "İngilizce", "Din Kültürü", "İnkılap Tarihi"]
secilen_brans = st.sidebar.selectbox("Branş Seçimi", branslar)

st.sidebar.divider()
# Menü yapısı güncellendi
menu = st.sidebar.radio("Modüller", ["Öğrenci Yönetimi", "Öğrenci Profili", "Not Takip", "Ödev Takip", "LGS Takip"])

sinif_listesi = ["5-A", "5-B", "6-A", "6-B", "7-A", "7-B", "8-A", "8-B"]

if menu == "Öğrenci Yönetimi":
    st.header("Öğrenci Yönetimi")
    secilen_sinif = st.selectbox("Sınıf Seçin", sinif_listesi)
    
    with st.form("ogrenci_ekle_form", clear_on_submit=True):
        yeni_ogrenci = st.text_input("Öğrenci Adı Soyadı")
        kaydet_btn = st.form_submit_button("Öğrenciyi Sisteme Ekle")
        
        if kaydet_btn and yeni_ogrenci:
            supabase.table("ogrenciler").insert({"ad_soyad": yeni_ogrenci, "sinif": secilen_sinif}).execute()
            st.success("Kayıt başarılı.")
            st.rerun()
            
    st.subheader(f"{secilen_sinif} Sınıf Listesi")
    ogrenciler_res = supabase.table("ogrenciler").select("*").eq("sinif", secilen_sinif).execute()
    if ogrenciler_res.data:
        df_ogrenciler = pd.DataFrame(ogrenciler_res.data)
        st.dataframe(df_ogrenciler[["ad_soyad"]], use_container_width=True, hide_index=True)
    else:
        st.info("Kayıtlı öğrenci bulunmamaktadır.")

elif menu == "Öğrenci Profili":
    st.header("Öğrenci Profili")
    secilen_sinif = st.selectbox("Sınıf Seçin", sinif_listesi, key="profil_sinif")
    is_8th_grade = secilen_sinif.startswith("8")
    
    ogrenciler_res = supabase.table("ogrenciler").select("*").eq("sinif", secilen_sinif).execute()
    
    if ogrenciler_res.data:
        ogrenci_isimleri = [ogr["ad_soyad"] for ogr in ogrenciler_res.data]
        secilen_ogrenci = st.selectbox("Profilini Görüntülemek İstediğiniz Öğrenciyi Seçin", ["Seçiniz..."] + ogrenci_isimleri)
        
        if secilen_ogrenci != "Seçiniz...":
            ogr_data = next(ogr for ogr in ogrenciler_res.data if ogr["ad_soyad"] == secilen_ogrenci)
            ogr_id = ogr_data["id"]
            
            st.markdown(f"### 👤 {secilen_ogrenci} - Akademik Profil")
            
            # --- 1. METRİK KARTLARI HESAPLAMA ---
            notlar_res = supabase.table("notlar").select("*").eq("ogrenci_id", ogr_id).execute()
            genel_ortalama = 0
            if notlar_res.data:
                toplam_not = 0
                not_sayisi = 0
                for kayit in notlar_res.data:
                    n = [kayit.get("sinav_1"), kayit.get("sinav_2"), kayit.get("perf_1"), kayit.get("perf_2"), kayit.get("proje")]
                    gecerli = [float(x) for x in n if x is not None]
                    if gecerli:
                        toplam_not += (sum(gecerli) / len(gecerli))
                        not_sayisi += 1
                if not_sayisi > 0:
                    genel_ortalama = round(toplam_not / not_sayisi, 2)

            odevler_res = supabase.table("odev_teslimleri").select("*").eq("ogrenci_id", ogr_id).execute()
            odev_orani = 0
            if odevler_res.data:
                toplam_odev = len(odevler_res.data)
                yapti_sayisi = sum(1 for o in odevler_res.data if o["durum"] == "Yaptı")
                odev_orani = round((yapti_sayisi / toplam_odev) * 100, 1)

            son_deneme_neti = 0
            lgs_res = None
            if is_8th_grade:
                lgs_res = supabase.table("lgs_denemeleri").select("*").eq("ogrenci_id", ogr_id).execute()
                if lgs_res.data:
                    son_deneme = lgs_res.data[-1] 
                    t_net = son_deneme["turkce_d"] - (son_deneme["turkce_y"] / 3)
                    m_net = son_deneme["mat_d"] - (son_deneme["mat_y"] / 3)
                    f_net = son_deneme["fen_d"] - (son_deneme["fen_y"] / 3)
                    i_net = son_deneme["ink_d"] - (son_deneme["ink_y"] / 3)
                    d_net = son_deneme["din_d"] - (son_deneme["din_y"] / 3)
                    in_net = son_deneme["ing_d"] - (son_deneme["ing_y"] / 3)
                    son_deneme_neti = round(t_net + m_net + f_net + i_net + d_net + in_net, 2)

            col1, col2, col3 = st.columns(3)
            col1.metric("Genel Not Ortalaması", f"{genel_ortalama} / 100")
            col2.metric("Ödev Tamamlama Oranı", f"% {odev_orani}")
            if is_8th_grade:
                col3.metric("Son Deneme Neti", f"{son_deneme_neti} Net")
            
            st.divider()

            # --- 2. NOT VE BAŞARI DURUMU TABLOSU ---
            st.subheader("📊 Branş Bazlı Not Durumu")
            if notlar_res.data:
                df_profil_notlar = pd.DataFrame(notlar_res.data)
                df_gosterim = df_profil_notlar.rename(columns={
                    "brans": "Branş", "sinav_1": "1. Yazılı", "sinav_2": "2. Yazılı", 
                    "perf_1": "1. Performans", "perf_2": "2. Performans", "proje": "Proje"
                })
                
                def satir_ort(row):
                    n = [row["1. Yazılı"], row["2. Yazılı"], row["1. Performans"], row["2. Performans"],
