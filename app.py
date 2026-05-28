import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client, Client
from datetime import date, timedelta
import matplotlib.pyplot as plt
import io
import base64
import random

# Sayfa Ayarları
st.set_page_config(page_title="Okul Takip Sistemi", layout="wide")

# --- OTURUM YÖNETİMİ ---
if "giris_yapildi" not in st.session_state: st.session_state.giris_yapildi = False

if not st.session_state.giris_yapildi:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.title("🔐 Sisteme Giriş")
        with st.form("giris_formu"):
            k_adi = st.text_input("Kullanıcı Adı")
            sifre = st.text_input("Sifre", type="password")
            if st.form_submit_button("Giriş Yap", use_container_width=True):
                if k_adi == "admin" and sifre == "123456":
                    st.session_state.giris_yapildi = True
                    st.rerun()
                else: st.error("Hatalı bilgiler.")
    st.stop()

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- ANA MENÜ ---
menu = st.sidebar.radio("Modüller", ["Öğrenci Yönetimi", "Öğrenci Profil Paneli", "Not Takip", "Ödev Takip", "LGS Takip", "🛠️ Test Verisi Üret"])
branslar = ["Matematik", "Türkçe", "Fen Bilimleri", "Sosyal Bilgiler", "İngilizce", "Din Kültürü", "İnkılap Tarihi"]
secilen_brans = st.sidebar.selectbox("Branş Seçimi", branslar)

# (Diğer modüller öncekiyle aynı, LGS Takip Modülünü aşağıda güncelledim)

elif menu == "LGS Takip":
    st.header("LGS Hazırlık ve Takip Modülü")
    sinif_8_listesi = ["8-A"] # Basitleştirildi
    secilen_sinif_lgs = st.selectbox("Sınıf Seçin", sinif_8_listesi)
    
    ogrenciler_res = supabase.table("ogrenciler").select("id, ad_soyad").eq("sinif", secilen_sinif_lgs).execute()
    
    if not ogrenciler_res.data:
        st.warning("Öğrenci bulunamadı.")
    else:
        ogrenciler = ogrenciler_res.data
        ogr_secenekleri = {ogr["ad_soyad"]: ogr["id"] for ogr in ogrenciler}
        ogr_idler = [ogr["id"] for ogr in ogrenciler]
        
        tab_lgs1, tab_lgs2, tab_lgs3 = st.tabs(["📝 Deneme Girişi", "📊 Sınıf Sıralama & PDF", "🎯 Öğrenci Analizi"])
        
        with tab_lgs1:
            deneme_adi = st.text_input("Deneme Adı")
            # ... (Daha önceki toplu giriş kodu buraya aynı şekilde gelecek) ...
            # ÖNEMLİ: Veritabanına kaydederken sütun adının 'lgs_puani' olduğundan emin oluyoruz.

        with tab_lgs2:
            mevcut_denemeler = supabase.table("lgs_denemeleri").select("deneme_adi").in_("ogrenci_id", ogr_idler).execute()
            if mevcut_denemeler.data:
                secili_deneme = st.selectbox("Sınav Seçin", list(set([d["deneme_adi"] for d in mevcut_denemeler.data])))
                s_veri = supabase.table("lgs_denemeleri").select("*").eq("deneme_adi", secili_deneme).in_("ogrenci_id", ogr_idler).execute()
                
                if s_veri.data:
                    df_s = pd.DataFrame(s_veri.data)
                    # HATA BURADA ÇÖZÜLDÜ: 'lgs_puani' ismini garanti ediyoruz
                    df_s = df_s.rename(columns={'lgs_puani': 'LGS Puanı'})
                    df_s["Toplam Net"] = df_s[["turkce_d", "mat_d", "fen_d", "ink_d", "din_d", "ing_d"]].sum(axis=1) - (df_s[["turkce_y", "mat_y", "fen_y", "ink_y", "din_y", "ing_y"]].sum(axis=1) / 3)
                    
                    df_s = df_s.sort_values(by="LGS Puanı", ascending=False)
                    st.dataframe(df_s, use_container_width=True)
                    
                    # PDF İndirme Butonu
                    csv = df_s.to_csv(index=False).encode('utf-8')
                    st.download_button("📄 Sınıf Raporunu İndir (CSV)", csv, f"{secili_deneme}_Rapor.csv", "text/csv")
