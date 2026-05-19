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
menu = st.sidebar.radio("Modüller", ["Öğrenci Yönetimi", "Not Takip", "Ödev Takip", "LGS Takip"])

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

elif menu == "Not Takip":
    st.header(f"Not Takip Paneli - {secilen_brans}")
    secilen_sinif = st.selectbox("Sınıf Seçin", sinif_listesi, key="not_sinif")
    
    # 1. Öğrencileri Çek
    ogrenciler_res = supabase.table("ogrenciler").select("id, ad_soyad").eq("sinif", secilen_sinif).execute()
    
    if not ogrenciler_res.data:
        st.warning("Bu sınıfa ait öğrenci kaydı bulunmuyor. Lütfen 'Öğrenci Yönetimi' sekmesinden kayıt ekleyin.")
    else:
        ogrenciler = ogrenciler_res.data
        ogrenci_idler = [ogr["id"] for ogr in ogrenciler]
        
        # 2. Seçilen branşa ait mevcut notları çek
        notlar_res = supabase.table("notlar").select("*").eq("brans", secilen_brans).in_("ogrenci_id", ogrenci_idler).execute()
        mevcut_notlar = {not_kaydi["ogrenci_id"]: not_kaydi for not_kaydi in notlar_res.data}
        
        # 3. Tablo için veri hazırlama
        tablo_verisi = []
        for ogr in ogrenciler:
            ogr_id = ogr["id"]
            not_datasi = mevcut_notlar.get(ogr_id, {})
            
            tablo_verisi.append({
                "Kayıt ID": not_datasi.get("id", None),
                "Öğrenci ID": ogr_id,
                "Ad Soyad": ogr["ad_soyad"],
                "1. Yazılı": not_datasi.get("sinav_1", None),
                "2. Yazılı": not_datasi.get("sinav_2", None),
                "1. Performans": not_datasi.get("perf_1", None),
                "2. Performans": not_datasi.get("perf_2", None),
                "Proje": not_datasi.get("proje", None)
            })
            
        df = pd.DataFrame(tablo_verisi)
        
        # 4. Ortalama Hesaplama Fonksiyonu
        def ortalama_hesapla(row):
            notlar = [row["1. Yazılı"], row["2. Yazılı"], row["1. Performans"], row["2. Performans"], row["Proje"]]
            gecerli_notlar = [float(n) for n in notlar if pd.notnull(n) and str(n).strip() != ""]
            if gecerli_notlar:
                return round(sum(gecerli_notlar) / len(gecerli_notlar), 2)
            return None

        df["Ortalama"] = df.apply(ortalama_hesapla, axis=1)
        
        # 5. Düzenlenebilir Veri Tablosu
        st.write("Aşağıdaki tablo üzerinden not girişlerini yapabilirsiniz. Sayfadan ayrılmadan önce kaydetmeyi unutmayın.")
        
        duzenlenmis_df = st.data_editor(
            df,
            column_config={
                "Kayıt ID": None, 
                "Öğrenci ID": None, 
                "Ad Soyad": st.column_config.TextColumn(disabled=True),
                "Ortalama": st.column_config.NumberColumn(disabled=True)
            },
            hide_index=True,
            use_container_width=True
        )
        
        if st.button("Notları Veri Tabanına Kaydet", type="primary"):
            kayit_listesi = []
            for index, row in duzenlenmis_df.iterrows():
                kayit_verisi = {
                    "ogrenci_id": row["Öğrenci ID"],
                    "brans": secilen_brans,
                    "sinav_1": float(row["1. Yazılı"]) if pd.notnull(row["1. Yazılı"]) and str(row["1. Yazılı"]).strip() != "" else None,
                    "sinav_2": float(row["2. Yazılı"]) if pd.notnull(row["2. Yazılı"]) and str(row["2. Yazılı"]).strip() != "" else None,
                    "perf_1": float(row["1. Performans"]) if pd.notnull(row["1. Performans"]) and str(row["1. Performans"]).strip() != "" else None,
                    "perf_2": float(row["2. Performans"]) if pd.notnull(row["2. Performans"]) and str(row["2. Performans"]).strip() != "" else None,
                    "proje": float(row["Proje"]) if pd.notnull(row["Proje"]) and str(row["Proje"]).strip() != "" else None
                }
                
                if pd.notnull(row["Kayıt ID"]):
                    kayit_verisi["id"] = int(row["Kayıt ID"])
                    
                kayit_listesi.append(kayit_verisi)
            
            # Upsert işlemi çakışma durumunda (aynı öğrenci ve branş) güncellemeyi zorunlu kılar
            supabase.table("notlar").upsert(kayit_listesi, on_conflict="ogrenci_id,brans").execute()
            st.success("Notlar başarıyla kaydedildi.")
            st.rerun()

elif menu == "Ödev Takip":
    st.header("Ödev Takip Modülü")
    st.write("Bu modülün arayüzü 3. adımda entegre edilecektir.")

elif menu == "LGS Takip":
    st.header("LGS Takip Modülü")
    st.write("Bu modülün arayüzü 4. adımda entegre edilecektir.")
