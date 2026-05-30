import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client, Client
from datetime import date, timedelta
import matplotlib.subplots as subplots
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
import io
import base64
import random
import os

# --- 1. SAYFA VE LOGO AYARLARI ---
st.set_page_config(
    page_title="Sadiye ve Abdullah Tan Ortaokulu Takip Paneli", 
    page_icon="🎓", 
    layout="wide"
)

# --- 2. SUPABASE BAĞLANTISI ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- 3. SABİTLER VE YARDIMCI FONKSİYONLAR ---
branslar = ["Matematik", "Türkçe", "Fen Bilimleri", "Sosyal/İnkılap", "İngilizce", "Din Kültürü"]
sinif_listesi = ["5-A", "6-A", "7-A", "8-A"]

# Rol ve Kullanıcı Veritabanı
KULLANICILAR = {
    "admin": {"sifre": "123456", "rol": "admin", "brans": "Tümü"},
    "matematik": {"sifre": "123456", "rol": "ogretmen", "brans": "Matematik"},
    "turkce": {"sifre": "123456", "rol": "ogretmen", "brans": "Türkçe"},
    "fen": {"sifre": "123456", "rol": "ogretmen", "brans": "Fen Bilimleri"},
    "sosyal_inkilap": {"sifre": "123456", "rol": "ogretmen", "brans": "Sosyal/İnkılap"},
    "ingilizce": {"sifre": "123456", "rol": "ogretmen", "brans": "İngilizce"},
    "din": {"sifre": "123456", "rol": "ogretmen", "brans": "Din Kültürü"}
}

def get_base64_logo():
    if os.path.exists("logo.png"):
        with open("logo.png", "rb") as f:
            data = f.read()
            return base64.b64encode(data).decode('utf-8')
    return ""

pdf_logo_b64 = get_base64_logo()
logo_html = f'<img src="data:image/png;base64,{pdf_logo_b64}" style="width: 70px; float: left; margin-right: 15px;">' if pdf_logo_b64 else ''

# --- 4. OTURUM YÖNETİMİ ---
if "giris_yapildi" not in st.session_state:
    st.session_state.giris_yapildi = False
    st.session_state.rol = None
    st.session_state.brans = None

# --- 5. GİRİŞ EKRANI ---
if not st.session_state.giris_yapildi:
    with st.container():
        col_logo, col_baslik = st.columns([1, 6])
        with col_logo:
            if os.path.exists("logo.png"):
                st.image("logo.png", width=120)
            else:
                st.write("🏢") 
        
        with col_baslik:
            st.title("🎓 Sadiye ve Abdullah Tan Ortaokulu")
            st.subheader("Okul Takip Paneline Hoşgeldiniz")
            st.markdown("""
            Bu panel, okul yönetim sürecini dijitalleştirerek öğretmen ve velilerimiz için veri odaklı 
            bir takip mekanizması sunar. Panel üzerinden aşağıdaki işlemleri gerçekleştirebilirsiniz:
            
            * **Öğrenci Yönetimi:** Öğrenci kayıtlarını sınıf bazlı oluşturabilir ve toplu yönetebilirsiniz (Sadece Yönetici).
            * **Akademik Takip:** Not girişlerini yapabilir, branş bazlı ortalamaları izleyebilir ve PDF profil raporları alabilirsiniz.
            * **Ödev Süreçleri:** Ödev tanımlayabilir, teslim durumlarını puanlayabilir ve detaylı istatistikler tutabilirsiniz.
            * **LGS Hazırlık (8. Sınıflar):** Deneme sınavı sonuçlarını girebilir, sınıf sıralamalarını görebilir ve sınavları analiz edebilirsiniz.
            """)
    
    st.divider()
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.write("#### 🔐 Yetkili Girişi")
        st.write("Devam etmek için lütfen kullanıcı bilgilerinizi girin.")
        
        with st.form("giris_formu"):
            k_adi = st.text_input("Kullanıcı Adı")
            sifre = st.text_input("Şifre", type="password")
            giris_butonu = st.form_submit_button("Sisteme Giriş Yap", use_container_width=True)
            
            if giris_butonu:
                try:
                    res = supabase.table("kullanicilar").select("*").eq("kullanici_adi", k_adi).execute()
                    if res.data and len(res.data) > 0:
                        if res.data[0]["sifre"] == sifre:
                            st.session_state.giris_yapildi = True
                            st.session_state.rol = res.data[0]["rol"]
                            st.session_state.brans = res.data[0]["brans"]
                            st.rerun()
                        else:
                            st.error("❌ Hatalı şifre girdiniz.")
                    else:
                        st.error("❌ Sistemde böyle bir kullanıcı bulunamadı.")
                except Exception as e:
                    st.error(f"Sistem Hatası: Veritabanı bağlantısı kurulamadı. Hata Detayı: {str(e)}")
    st.stop() 

# --- 6. ANA UYGULAMA PANELİ ---
top_col1, top_col2 = st.columns([8, 1])
with top_col1:
    st.title("🚀 Okul Takip Sistemi")
with top_col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=80)

# Sidebar
if st.sidebar.button("🚪 Güvenli Çıkış", use_container_width=True):
    st.session_state.giris_yapildi = False
    st.session_state.rol = None
    st.session_state.brans = None
    st.rerun()

st.sidebar.divider()

if st.session_state.rol == "admin":
    secilen_brans = st.sidebar.selectbox("İşlem Yapılacak Branş", branslar)
    moduller = ["Öğrenci Yönetimi", "Öğrenci Profil Paneli", "Not Takip", "Ödev Takip", "LGS Takip", "🔑 Şifre İşlemleri", "🛠️ Test Verisi Modülü"]
else:
    st.sidebar.success(f"Aktif Branş: {st.session_state.brans}")
    secilen_brans = st.session_state.brans
    moduller = ["Öğrenci Profil Paneli", "Not Takip", "Ödev Takip", "LGS Takip"]

menu = st.sidebar.radio("Modüller", moduller)


# --- MODÜL 1: ÖĞRENCİ YÖNETİMİ (SADECE ADMİN) ---
if menu == "Öğrenci Yönetimi":
    st.header("👥 Öğrenci Yönetimi")
    
    tab_ekle, tab_sil = st.tabs(["➕ Öğrenci Ekle / Listele", "🗑️ Öğrenci Sil"])
    
    with tab_ekle:
        secilen_sinif = st.selectbox("Sınıf Seçin", sinif_listesi, key="ogr_ekle_sinif")
        with st.form("ogrenci_ekle_form", clear_on_submit=True):
            yeni_ogrenci = st.text_input("Öğrenci Adı Soyadı")
            kaydet_btn = st.form_submit_button("Öğrenciyi Sisteme Ekle")
            
            if kaydet_btn and yeni_ogrenci:
                try:
                    supabase.table("ogrenciler").insert({"ad_soyad": yeni_ogrenci, "sinif": secilen_sinif}).execute()
                    st.success(f"✅ {yeni_ogrenci} sisteme başarıyla eklendi.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Kayıt işlemi başarısız: {str(e)}")
                
        st.subheader(f"{secilen_sinif} Sınıf Listesi")
        try:
            ogrenciler_res = supabase.table("ogrenciler").select("*").eq("sinif", secilen_sinif).execute()
            if ogrenciler_res.data:
                df_ogrenciler = pd.DataFrame(ogrenciler_res.data)
                st.dataframe(df_ogrenciler[["ad_soyad"]], use_container_width=True, hide_index=True)
            else:
                st.info("Kayıtlı öğrenci bulunmamaktadır.")
        except Exception as e:
            st.error(f"Öğrenci listesi yüklenemedi: {str(e)}")

    with tab_sil:
        st.warning("⚠️ Dikkat: Seçilen öğrencileri sildiğinizde, bu öğrencilere ait tüm not, ödev ve LGS deneme kayıtları kalıcı olarak silinir.")
        secilen_sinif_sil = st.selectbox("Sınıf Seçin", sinif_listesi, key="ogr_sil_sinif")
        try:
            ogrenciler_sil_res = supabase.table("ogrenciler").select("id, ad_soyad").eq("sinif", secilen_sinif_sil).execute()
            
            if not ogrenciler_sil_res.data:
                st.info("Bu sınıfta silinecek kayıtlı öğrenci bulunmuyor.")
            else:
                ogr_secenekleri_sil = {ogr["ad_soyad"]: ogr["id"] for ogr in ogrenciler_sil_res.data}
                silinecek_ogrenciler_ad = st.multiselect("Silinecek Öğrencileri Seçin", list(ogr_secenekleri_sil.keys()))
                
                if silinecek_ogrenciler_ad:
                    silinecek_ogr_id_list = [ogr_secenekleri_sil[ad] for ad in silinecek_ogrenciler_ad]
                    if st.button(f"🗑️ Seçili {len(silinecek_ogrenciler_ad)} Öğrenciyi ve Tüm Verilerini Sil", type="primary"):
                        try:
                            supabase.table("notlar").delete().in_("ogrenci_id", silinecek_ogr_id_list).execute()
                            supabase.table("odev_teslimleri").delete().in_("ogrenci_id", silinecek_ogr_id_list).execute()
                            supabase.table("lgs_denemeleri").delete().in_("ogrenci_id", silinecek_ogr_id_list).execute()
                            supabase.table("ogrenciler").delete().in_("id", silinecek_ogr_id_list).execute()
                            st.success(f"✅ Seçilen {len(silinecek_ogrenciler_ad)} öğrenci ve verileri tamamen silindi.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Silme işlemi başarısız. Hata: {str(e)}")
                else:
                    st.info("Silmek için lütfen listeden en az bir öğrenci seçin.")
        except Exception as e:
            st.error(f"Veriler yüklenirken hata oluştu: {str(e)}")


# --- MODÜL 2: ÖĞRENCİ PROFİL PANELİ ---
elif menu == "Öğrenci Profil Paneli":
    st.header("👤 Öğrenci Profil Paneli")
    secilen_sinif = st.selectbox("Sınıf Seçin", sinif_listesi, key="profil_sinif_secim")
    
    try:
        ogrenciler_res = supabase.table("ogrenciler").select("*").eq("sinif", secilen_sinif).execute()
        ogrenci_isimleri = ["Seçiniz..."]
        if ogrenciler_res.data:
            ogrenci_isimleri += [ogr["ad_soyad"] for ogr in ogrenciler_res.data]
            
        secilen_ogrenci = st.selectbox("Profilini Görüntülemek İstediğiniz Öğrenciyi Seçin", ogrenci_isimleri, key="profil_ogrenci_secim")
            
        if secilen_ogrenci != "Seçiniz...":
            ogr_data = next(ogr for ogr in ogrenciler_res.data if ogr["ad_soyad"] == secilen_ogrenci)
            ogr_id = ogr_data["id"]
            
            st.markdown(f"### 👤 {secilen_ogrenci} - Akademik Gelişim Özet Raporu")
            
            notlar_res = supabase.table("notlar").select("*").eq("ogrenci_id", ogr_id).execute()
            genel_ortalama = 0
            df_html_notlar = "<p>Not verisi bulunamadı.</p>"
            if notlar_res.data:
                df_profil_notlar = pd.DataFrame(notlar_res.data)
                df_gosterim = df_profil_notlar.rename(columns={
                    "brans": "Branş", "sinav_1": "1. Yazılı", "sinav_2": "2. Yazılı", 
                    "perf_1": "1. Performans", "perf_2": "2. Performans", "proje": "Proje"
                })
                
                def satir_ort(row):
                    n = [row["1. Yazılı"], row["2. Yazılı"], row["1. Performans"], row["2. Performans"], row["Proje"]]
                    g = [float(x) for x in n if pd.notnull(x)]
                    return round(sum(g) / len(g), 2) if g else None
                    
                df_gosterim["Ortalama"] = df_gosterim.apply(satir_ort, axis=1)
                df_gosterim = df_gosterim[["Branş", "1. Yazılı", "2. Yazılı", "1. Performans", "2. Performans", "Proje", "Ortalama"]]
                
                gecerli_ortalamalar = df_gosterim["Ortalama"].dropna().tolist()
                if gecerli_ortalamalar:
                    genel_ortalama = round(sum(gecerli_ortalamalar) / len(gecerli_ortalamalar), 2)
                
                st.subheader("📊 Branş Bazlı Not Durumu")
                st.dataframe(df_gosterim, hide_index=True, use_container_width=True)
                df_html_notlar = df_gosterim.to_html(border=1, index=False, justify='center')
            else:
                st.info("Bu öğrenciye ait herhangi bir not verisi bulunmamaktadır.")
            
            odevler_res = supabase.table("odev_teslimleri").select("*").eq("ogrenci_id", ogr_id).execute()
            odev_orani = 0
            genel_graph_base64 = ""
            pdf_brans_grafikleri_html = ""
            df_html_odevler = "<p>Ödev verisi bulunamadı.</p>"
            
            if odevler_res.data:
                df_odevler_all = pd.DataFrame(odevler_res.data)
                toplam_odev = len(df_odevler_all)
                yapti_sayisi = sum(1 for o in odevler_res.data if o["durum"] == "Yaptı")
                odev_orani = round((yapti_sayisi / toplam_odev) * 100, 1)
                
                st.divider()
                st.subheader("📚 Ödev İstatistikleri ve Ders Bazlı Dağılım Paneli")
                
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    filtre_brans = st.selectbox("Ders Seçimi", ["Tüm Dersler"] + branslar, key="prof_hw_brans")
                with col_f2:
                    filtre_durum = st.selectbox("Ödev Durumu", ["Tüm Durumlar", "Yaptı", "Yarım", "Yapmadı", "Gelmedi"], key="prof_hw_durum")
                
                odev_detay_res = supabase.table("odev_teslimleri").select("durum, ogretmen_notu, odevler(odev_adi, brans)").eq("ogrenci_id", ogr_id).execute()
                detay_liste = []
                for d in odev_detay_res.data:
                    odev_bilgisi = d.get("odevler") or {}
                    detay_liste.append({
                        "Branş": odev_bilgisi.get("brans", ""),
                        "Ödev Adı": odev_bilgisi.get("odev_adi", ""),
                        "Durum": d.get("durum", ""),
                        "Açıklama/Not": d.get("ogretmen_notu", "")
                    })
                df_full_odev = pd.DataFrame(detay_liste)
                
                df_filtered_odev = df_full_odev.copy()
                if filtre_brans != "Tüm Dersler":
                    df_filtered_odev = df_filtered_odev[df_filtered_odev["Branş"] == filtre_brans]
                if filtre_durum != "Tüm Durumlar":
                    df_filtered_odev = df_filtered_odev[df_filtered_odev["Durum"] == filtre_durum]
                
                col_grafik, col_tablo = st.columns([5, 5])
                
                with col_grafik:
                    if not df_filtered_odev.empty:
                        color_map = {"Yaptı": "#4CAF50", "Yarım": "#FFC107", "Yapmadı": "#F44336", "Gelmedi": "#9E9E9E"}
                        status_counts_genel = df_filtered_odev["Durum"].value_counts()
                        current_colors_genel = [color_map.get(idx_name, "#2196F3") for idx_name in status_counts_genel.index]
                        
                        fig_genel, ax_genel = plt.subplots(figsize=(3.5, 3.5))
                        wedges, texts, autotexts = ax_genel.pie(
                            status_counts_genel, labels=status_counts_genel.index, autopct='%1.1f%%', 
                            startangle=90, colors=current_colors_genel, wedgeprops=dict(width=0.4, edgecolor='w')
                        )
                        plt.setp(autotexts, size=8, weight="bold")
                        plt.setp(texts, size=9)
                        st.write("**Genel Ödev Dağılımı**")
                        st.pyplot(fig_genel)
                        
                        buf_genel = io.BytesIO()
                        plt.savefig(buf_genel, format='png', bbox_inches='tight', dpi=130)
                        buf_genel.seek(0)
                        genel_graph_base64 = base64.b64encode(buf_genel.read()).decode('utf-8')
                        plt.close(fig_genel)
                        
                        st.divider()
                        st.write("**Ders Bazlı Ödev Dağılımları**")
                        cizilecek_branslar = branslar if filtre_brans == "Tüm Dersler" else [filtre_brans]
                        aktif_branslar = [b for b in cizilecek_branslar if not df_filtered_odev[df_filtered_odev["Branş"] == b].empty]
                        
                        if aktif_branslar:
                            cols_ui = st.columns(2)
                            idx = 0
                            for b in aktif_branslar:
                                df_b = df_filtered_odev[df_filtered_odev["Branş"] == b]
                                status_counts = df_b["Durum"].value_counts()
                                current_colors = [color_map.get(idx_name, "#2196F3") for idx_name in status_counts.index]
                                
                                fig, ax = plt.subplots(figsize=(2.8, 2.8))
                                wedges, texts, autotexts = ax.pie(
                                    status_counts, labels=status_counts.index, autopct='%1.1f%%', 
                                    startangle=90, colors=current_colors, wedgeprops=dict(width=0.4, edgecolor='w')
                                )
                                plt.setp(autotexts, size=7, weight="bold")
                                plt.setp(texts, size=8)
                                ax.set_title(f"{b}", fontsize=9, weight="bold", pad=5)
                                
                                with cols_ui[idx % 2]:
                                    st.pyplot(fig)
                                
                                buf = io.BytesIO()
                                plt.savefig(buf, format='png', bbox_inches='tight', dpi=130)
                                buf.seek(0)
                                img_b64 = base64.b64encode(buf.read()).decode('utf-8')
                                plt.close(fig)
                                pdf_brans_grafikleri_html += f'<div style="display: inline-block; width: 45%; margin: 2%; text-align: center; vertical-align: top;"><img src="data:image/png;base64,{img_b64}" style="width: 100%; max-width: 240px;"></div>'
                                idx += 1
                        else:
                            st.warning("Ders bazlı analiz için veri bulunamadı.")
                else:
                    st.warning("Seçilen kriterlere uygun ödev kaydı bulunamadığından grafik oluşturulamadı.")
            
            with col_tablo:
                st.write("**Filtrelenmiş Ödev Sorumluluk Listesi**")
                st.dataframe(df_filtered_odev, hide_index=True, use_container_width=True)
                df_html_odevler = df_filtered_odev.to_html(border=1, index=False, justify='center')
        else:
            st.info("Bu öğrenciye ait ödev değerlendirmesi bulunmamaktadır.")

        st.sidebar.markdown("---")
        st.sidebar.subheader("Öğrenci Genel Durumu")
        st.sidebar.metric("Genel Not Ortalaması", f"{genel_ortalama} / 100")
        st.sidebar.metric("Ödev Tamamlama Oranı", f"% {odev_orani}")
        
        html_odev_grafikleri = ""
        if genel_graph_base64:
            html_odev_grafikleri = f"""
            <div style="text-align: center; margin-top: 15px;">
                <div style="display: inline-block; width: 45%; vertical-align: top;">
                    <b>Genel Ödev Dağılımı</b><br>
                    <img src="data:image/png;base64,{genel_graph_base64}" style="max-width: 250px;">
                </div>
                <div style="display: inline-block; width: 50%; vertical-align: top;">
                    <b>Ders Bazlı Ödev Dağılımları</b><br>
                    {pdf_brans_grafikleri_html}
                </div>
            </div>
            """

        profil_pdf_html = f"""
        <html>
        <head>
        <meta charset="utf-8">
        <title>Öğrenci Profil Raporu</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 35px; color: #333; }}
            .title-container {{ margin-bottom: 30px; overflow: hidden; }}
            .title {{ text-align: center; font-size: 22px; font-weight: bold; margin-bottom: 5px; margin-top: 10px; }}
            .subtitle {{ text-align: center; font-size: 14px; color: #555; }}
            .kv-table {{ width: 100%; border: none; margin-bottom: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 12px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
            th {{ background-color: #f5f5f5; font-weight: bold; }}
            .section-title {{ font-size: 15px; font-weight: bold; color: #fff; background-color: #2196F3; padding: 6px 10px; margin-top: 25px; border-radius: 3px; }}
            .summary-box {{ background-color: #f9fbfd; border-left: 4px solid #4CAF50; padding: 12px; margin-top: 15px; font-size: 13px; text-align: center; }}
        </style>
        </head>
        <body onload="window.print()">
            <div class="title-container">
                {logo_html}
                <div class="title">ÖĞRENCİ AKADEMİK PROFİL RAPORU</div>
                <div class="subtitle">Sadiye ve Abdullah Tan Ortaokulu - Not ve Ödev Gelişim Dökümü</div>
            </div>
            <table class="kv-table">
                <tr>
                    <td style="text-align:left; border:none; font-size:14px;"><b>Öğrenci Adı Soyadı:</b> {secilen_ogrenci}</td>
                    <td style="text-align:right; border:none; font-size:14px;"><b>Sınıfı:</b> {secilen_sinif} | <b>Rapor Tarihi:</b> {date.today().strftime('%d.%m.%Y')}</td>
                </tr>
            </table>
            <div class="summary-box">
                <b>Genel Not Ortalaması:</b> {genel_ortalama} / 100 &nbsp;&nbsp;&nbsp; | &nbsp;&nbsp;&nbsp; <b>Ödev Tamamlama Oranı:</b> % {odev_orani}
            </div>
            <div class="section-title">📊 Branş Bazlı Not Durumu</div>
            {df_html_notlar}
            <div class="section-title">📚 Ödev Dağılım İstatistikleri</div>
            {html_odev_grafikleri}
            <div class="section-title">📝 Ödev Sorumluluk Listesi</div>
            {df_html_odevler}
        </body>
        </html>
        """
        st.divider()
        st.write("#### 💾 Öğrenci Profil Raporunu Dışa Aktar")
        st.download_button(
            label="📄 Profil Raporunu PDF İndir",
            data=profil_pdf_html,
            file_name=f"{secilen_ogrenci}_Profil_Raporu.html",
            mime="text/html"
        )
    except Exception as e:
        st.error(f"Profil verileri yüklenirken hata oluştu: {str(e)}")


# --- MODÜL 3: NOT TAKİP ---
elif menu == "Not Takip":
    st.header(f"📝 Not Takip Paneli - {secilen_brans}")
    secilen_sinif = st.selectbox("Sınıf Seçin", sinif_listesi, key="not_sinif")
    
    try:
        ogrenciler_res = supabase.table("ogrenciler").select("id, ad_soyad").eq("sinif", secilen_sinif).execute()
        if not ogrenciler_res.data:
            st.warning("Bu sınıfa ait öğrenci kaydı bulunmuyor. Lütfen 'Öğrenci Yönetimi' sekmesinden kayıt ekleyin.")
        else:
            ogrenciler = ogrenciler_res.data
            ogrenci_idler = [ogr["id"] for ogr in ogrenciler]
            
            notlar_res = supabase.table("notlar").select("*").eq("brans", secilen_brans).in_("ogrenci_id", ogrenci_idler).execute()
            mevcut_notlar = {not_kaydi["ogrenci_id"]: not_kaydi for not_kaydi in notlar_res.data}
            
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
            
            def ortalama_hesapla(row):
                notlar = [row["1. Yazılı"], row["2. Yazılı"], row["1. Performans"], row["2. Performans"], row["Proje"]]
                gecerli_notlar = [float(n) for n in notlar if pd.notnull(n) and str(n).strip() != ""]
                if gecerli_notlar:
                    return round(sum(gecerli_notlar) / len(gecerli_notlar), 2)
                return None

            df["Ortalama"] = df.apply(ortalama_hesapla, axis=1)
            st.write("Aşağıdaki tablo üzerinden notları ekleyebilir, güncelleyebilir veya hücreyi boşaltıp kaydederek silebilirsiniz.")
            
            duzenlenmis_df = st.data_editor(
                df,
                column_config={
                    "Kayıt ID": None, 
                    "Öğrenci ID": None, 
                    "Ad Soyad": st.column_config.TextColumn(disabled=True),
                    "Ortalama": st.column_config.NumberColumn(disabled=True)
                }, hide_index=True, use_container_width=True
            )
            
            if st.button("Notları Veri Tabanına Kaydet", type="primary"):
                try:
                    for index, row in duzenlenmis_df.iterrows():
                        kayit_verisi = {
                            "ogrenci_id": int(row["Öğrenci ID"]),
                            "brans": secilen_brans,
                            "sinav_1": float(row["1. Yazılı"]) if pd.notnull(row["1. Yazılı"]) and str(row["1. Yazılı"]).strip() != "" else None,
                            "sinav_2": float(row["2. Yazılı"]) if pd.notnull(row["2. Yazılı"]) and str(row["2. Yazılı"]).strip() != "" else None,
                            "perf_1": float(row["1. Performans"]) if pd.notnull(row["1. Performans"]) and str(row["1. Performans"]).strip() != "" else None,
                            "perf_2": float(row["2. Performans"]) if pd.notnull(row["2. Performans"]) and str(row["2. Performans"]).strip() != "" else None,
                            "proje": float(row["Proje"]) if pd.notnull(row["Proje"]) and str(row["Proje"]).strip() != "" else None
                        }
                        
                        not_var_mi = any(v is not None for k, v in kayit_verisi.items() if k not in ["ogrenci_id", "brans"])
                        
                        if pd.notnull(row["Kayıt ID"]):
                            if not_var_mi:
                                supabase.table("notlar").update(kayit_verisi).eq("id", int(row["Kayıt ID"])).execute()
                            else:
                                supabase.table("notlar").delete().eq("id", int(row["Kayıt ID"])).execute()
                        elif not_var_mi:
                            supabase.table("notlar").insert(kayit_verisi).execute()
                            
                    st.success("✅ Notlar başarıyla kaydedildi.")
                except Exception as e:
                    st.error(f"Notlar kaydedilirken hata oluştu: {str(e)}")
    except Exception as e:
        st.error(f"Öğrenci listesi yüklenemedi: {str(e)}")

# --- MODÜL 4: ÖDEV TAKİP ---
elif menu == "Ödev Takip":
    st.header(f"📦 Ödev Takip Modülü - {secilen_brans}")
    tab1, tab2, tab3 = st.tabs(["📝 Yeni Ödev Tanımla", "✅ Ödev Düzenle / Değerlendir", "📊 Ödev Raporları"])
    
    with tab1:
        secilen_sinif_odev = st.selectbox("Sınıf Seçin", sinif_listesi, key="odev_sinif_tanimla")
        with st.form("odev_tanimla_form", clear_on_submit=True):
            odev_adi = st.text_input("Ödev Adı / Konusu (Örn: Çarpanlar ve Katlar Test 1)")
            odev_aciklama = st.text_area("Ödev Açıklaması (İsteğe Bağlı)")
            teslim_tarihi = st.date_input("Teslim Tarihi")
            
            submit_odev = st.form_submit_button("Ödevi Sisteme Kaydet")
            
            if submit_odev and odev_adi:
                try:
                    supabase.table("odevler").insert({
                        "brans": secilen_brans,
                        "sinif": secilen_sinif_odev,
                        "odev_adi": odev_adi,
                        "aciklama": odev_aciklama,
                        "teslim_tarihi": str(teslim_tarihi)
                    }).execute()
                    st.success("✅ Ödev başarıyla tanımlandı.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ödev tanımlanırken hata oluştu: {str(e)}")

    with tab2:
        secilen_sinif_kontrol = st.selectbox("Sınıf Seçin", sinif_listesi, key="odev_sinif_kontrol")
        try:
            odevler_res = supabase.table("odevler").select("*").eq("sinif", secilen_sinif_kontrol).eq("brans", secilen_brans).execute()
            if not odevler_res.data:
                st.info("Bu sınıfa ve branşa ait tanımlanmış bir ödev bulunmamaktadır.")
            else:
                odev_secenekleri = {f"{o['odev_adi']} (Teslim: {o['teslim_tarihi']})": o['id'] for o in odevler_res.data}
                secilen_odev_etiketi = st.selectbox("Kontrol Edilecek / Düzenlenecek Ödevi Seçin", list(odev_secenekleri.keys()))
                secilen_odev_id = odev_secenekleri[secilen_odev_etiketi]
                
                col_d1, col_d2 = st.columns([4, 1])
                with col_d2:
                    if st.button("🗑️ Bu Ödevi Tamamen Sil"):
                        try:
                            supabase.table("odev_teslimleri").delete().eq("odev_id", secilen_odev_id).execute()
                            supabase.table("odevler").delete().eq("id", secilen_odev_id).execute()
                            st.success("✅ Ödev başarıyla silindi.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Silme işlemi başarısız: {str(e)}")
                
                ogrenciler_res = supabase.table("ogrenciler").select("id, ad_soyad").eq("sinif", secilen_sinif_kontrol).execute()
                
                if not ogrenciler_res.data:
                    st.warning("Sınıfta kayıtlı öğrenci bulunmuyor.")
                else:
                    ogrenciler = ogrenciler_res.data
                    ogr_idler = [ogr["id"] for ogr in ogrenciler]
                    
                    teslimler_res = supabase.table("odev_teslimleri").select("*").eq("odev_id", secilen_odev_id).in_("ogrenci_id", ogr_idler).execute()
                    mevcut_teslimler = {t["ogrenci_id"]: t for t in teslimler_res.data}
                    
                    tablo_verisi = []
                    for ogr in ogrenciler:
                        ogr_id = ogr["id"]
                        teslim_datasi = mevcut_teslimler.get(ogr_id, {})
                        tablo_verisi.append({
                            "Kayıt ID": teslim_datasi.get("id", None),
                            "Öğrenci ID": ogr_id,
                            "Ad Soyad": ogr["ad_soyad"],
                            "Durum": teslim_datasi.get("durum", "Değerlendirilmedi"),
                            "Öğretmen Notu": teslim_datasi.get("ogretmen_notu", "")
                        })
                        
                    df_odev = pd.DataFrame(tablo_verisi)
                    
                    duzenlenmis_df = st.data_editor(
                        df_odev,
                        column_config={
                            "Kayıt ID": None,
                            "Öğrenci ID": None,
                            "Ad Soyad": st.column_config.TextColumn(disabled=True),
                            "Durum": st.column_config.SelectboxColumn(
                                "Ödev Durumu",
                                options=["Değerlendirilmedi", "Yaptı", "Yarım", "Yapmadı", "Gelmedi"],
                                required=True
                            ),
                            "Öğretmen Notu": st.column_config.TextColumn("Öğretmen Notu (Opsiyonel)")
                        }, hide_index=True, use_container_width=True
                    )
                    
                    if st.button("Değişiklikleri Veri Tabanına Kaydet", type="primary"):
                        try:
                            for index, row in duzenlenmis_df.iterrows():
                                durum = row["Durum"]
                                not_metni = str(row["Öğretmen Notu"]).strip() if pd.notnull(row["Öğretmen Notu"]) else ""
                                
                                if durum != "Değerlendirilmedi":
                                    kayit_verisi = {
                                        "odev_id": secilen_odev_id,
                                        "ogrenci_id": int(row["Öğrenci ID"]),
                                        "durum": durum,
                                        "ogretmen_notu": not_metni
                                    }
                                    if pd.notnull(row["Kayıt ID"]):
                                        supabase.table("odev_teslimleri").update({"durum": durum, "ogretmen_notu": not_metni}).eq("id", int(row["Kayıt ID"])).execute()
                                    else:
                                        supabase.table("odev_teslimleri").insert(kayit_verisi).execute()
                                elif pd.notnull(row["Kayıt ID"]) and durum == "Değerlendirilmedi":
                                    supabase.table("odev_teslimleri").delete().eq("id", int(row["Kayıt ID"])).execute()
                            st.success("✅ Ödev durumları güncellendi.")
                        except Exception as e:
                            st.error(f"Değerlendirme kaydedilemedi: {str(e)}")
        except Exception as e:
            st.error(f"Ödev kayıtları yüklenemedi: {str(e)}")

    with tab3:
        st.write("### Rapor Filtreleme")
        col1, col2, col3 = st.columns(3)
        with col1:
            secilen_sinif_rapor = st.selectbox("Sınıf Seçin", sinif_listesi, key="odev_sinif_rapor")
        with col2:
            bugun = date.today()
            otuz_gun_once = bugun - timedelta(days=30)
            secilen_tarih = st.date_input("Teslim Tarihi Aralığı", value=(otuz_gun_once, bugun), key="odev_tarih_filtre")
        with col3:
            secilen_rapor_branslar = st.multiselect("Görüntülenecek Branşlar", branslar, default=[secilen_brans] if st.session_state.rol=="ogretmen" else branslar, key="odev_brans_filtre")

        if len(secilen_tarih) != 2:
            st.warning("Lütfen bir başlangıç ve bitiş tarihi aralığı seçin.")
        elif not secilen_rapor_branslar:
            st.warning("Lütfen en az bir branş seçin.")
        else:
            try:
                baslangic_tarihi, bitis_tarihi = secilen_tarih
                ogr_res = supabase.table("ogrenciler").select("id, ad_soyad").eq("sinif", secilen_sinif_rapor).execute()
                odv_res = supabase.table("odevler").select("id, odev_adi, brans").eq("sinif", secilen_sinif_rapor).in_("brans", secilen_rapor_branslar).gte("teslim_tarihi", str(baslangic_tarihi)).lte("teslim_tarihi", str(bitis_tarihi)).execute()
                
                if not ogr_res.data:
                    st.warning("Bu sınıfta kayıtlı öğrenci bulunmuyor.")
                elif not odv_res.data:
                    st.info("Belirtilen kriterlerde ödev verisi bulunamadı.")
                else:
                    ogrenciler = ogr_res.data
                    odevler = odv_res.data
                    odev_ids = [o["id"] for o in odevler]
                    ogr_ids = [o["id"] for o in ogrenciler]
                    
                    tsl_res = supabase.table("odev_teslimleri").select("ogrenci_id, odev_id, durum").in_("odev_id", odev_ids).in_("ogrenci_id", ogr_ids).execute()
                    odev_map = {o["id"]: f"{o['odev_adi']} ({o['brans']})" for o in odevler}
                    
                    matris_veri = []
                    for ogr in ogrenciler:
                        satir = {"Öğrenci Adı": ogr["ad_soyad"]}
                        for o in odevler:
                            satir[f"{o['odev_adi']} ({o['brans']})"] = "-"
                        matris_veri.append(satir)
                        
                    df_matris = pd.DataFrame(matris_veri)
                    df_matris.set_index("Öğrenci Adı", inplace=True)
                    
                    for t in tsl_res.data:
                        ogr_ad = next((o["ad_soyad"] for o in ogrenciler if o["id"] == t["ogrenci_id"]), None)
                        odv_ad = odev_map.get(t["odev_id"])
                        if ogr_ad and odv_ad:
                            df_matris.at[ogr_ad, odv_ad] = t["durum"]
                    
                    st.write(f"**{secilen_sinif_rapor} Sınıfı Ödev Takip Çizelgesi**")
                    st.dataframe(df_matris, use_container_width=True)

                    col_btn1, col_btn2 = st.columns(2)
                    html_tablo = df_matris.to_html(border=1, justify='center')
                    html_icerik_rapor = f"""
                    <html><head><meta charset='utf-8'><title>{secilen_sinif_rapor} Ödev Raporu</title></head>
                    <body onload='window.print()'>
                    <div style="margin-bottom: 20px; overflow: hidden;">
                        {logo_html}
                        <h2 style="margin-top: 10px;">Sadiye ve Abdullah Tan Ortaokulu - {secilen_sinif_rapor} Sınıfı Ödev Takip Çizelgesi</h2>
                    </div>
                    {html_tablo}
                    </body></html>
                    """
                    with col_btn1:
                        st.download_button(label="📄 PDF Olarak Kaydet", data=html_icerik_rapor, file_name=f"{secilen_sinif_rapor}_Odev_Raporu.html", mime="text/html")
                    with col_btn2:
                        st.download_button(label="📊 Excel İçin İndir", data=df_matris.to_csv(index=True, sep=";", encoding="utf-8-sig").encode("utf-8-sig"), file_name=f"{secilen_sinif_rapor}_Odev_Raporu.csv", mime="text/csv")
            except Exception as e:
                st.error(f"Rapor oluşturulurken hata yaşandı: {str(e)}")

# --- MODÜL 5: LGS TAKİP ---
elif menu == "LGS Takip":
    st.header("🎯 LGS Hazırlık ve Takip Modülü")
    
    sinif_8_listesi = [s for s in sinif_listesi if s.startswith("8")]
    
    if not sinif_8_listesi:
        st.info("Sistemde kayıtlı 8. sınıf bulunmamaktadır. Bu modül sadece 8. sınıflar için aktiftir.")
    else:
        secilen_sinif_lgs = st.selectbox("Sınıf Seçin", sinif_8_listesi, key="lgs_sinif_secim")
        try:
            ogrenciler_res = supabase.table("ogrenciler").select("id, ad_soyad").eq("sinif", secilen_sinif_lgs).execute()
            
            if not ogrenciler_res.data:
                st.warning("Bu sınıfta öğrenci kaydı bulunmuyor.")
            else:
                ogrenciler = ogrenciler_res.data
                ogr_secenekleri = {ogr["ad_soyad"]: ogr["id"] for ogr in ogrenciler}
                ogr_idler = [ogr["id"] for ogr in ogrenciler]
                
                tab_lgs1, tab_lgs2, tab_lgs3 = st.tabs(["📝 Deneme Notu İşlem Paneli", "📊 Sınıf Genel Sıralaması", "🎯 Öğrenci Özel Analizi"])
                
                # --- LGS TAB 1: DENEME GİRİŞ/DÜZENLEME ---
                with tab_lgs1:
                    islem_tipi = st.radio("İşlem Tipi Seçin:", ["➕ Yeni Deneme Girişi Yap", "✏️ Mevcut Denemeyi Düzenle / Sil"], horizontal=True)
                    
                    if islem_tipi == "➕ Yeni Deneme Girişi Yap":
                        deneme_adi = st.text_input("Yeni Deneme Sınavı Adı (Örn: Özdebir LGS-1)")
                        lgs_tablo_verisi = []
                        for ogr in ogrenciler:
                            lgs_tablo_verisi.append({
                                "Öğrenci ID": ogr["id"], "Kayıt ID": None, "Öğrenci Adı": ogr["ad_soyad"],
                                "Katılım": "Katıldı",
                                "Türkçe D": 0, "Türkçe Y": 0, "Matematik D": 0, "Matematik Y": 0,
                                "Fen D": 0, "Fen Y": 0, "Sosyal/İnkılap D": 0, "Sosyal/İnkılap Y": 0,
                                "Din D": 0, "Din Y": 0, "İngilizce D": 0, "İngilizce Y": 0,
                                "LGS Puanı": 200.0, "Yüzdelik Dilim": 100.0
                            })
                        df_lgs_toplu = pd.DataFrame(lgs_tablo_verisi)
                        st.write("Aşağıdaki matrise sınıfın verilerini girip tek tıkla toplu (Bulk) kayıt yapabilirsiniz.")
                        st.info("Sınava girmeyen öğrenciler için 'Katılım' sütununu 'Girmedi' olarak değiştirin. Bu öğrencilere ait veri sisteme işlenmeyecektir.")
                    else:
                        mevcut_denemeler_res = supabase.table("lgs_denemeleri").select("deneme_adi").in_("ogrenci_id", ogr_idler).execute()
                        if mevcut_denemeler_res.data:
                            benzersiz_denemeler = list(set([d["deneme_adi"] for d in mevcut_denemeler_res.data]))
                            deneme_adi = st.selectbox("Düzenlenecek Deneme Sınavını Seçin", benzersiz_denemeler)
                            
                            col_del1, col_del2 = st.columns([4, 1])
                            with col_del2:
                                if st.button("🗑️ Bu Sınavı Tamamen Sil"):
                                    try:
                                        supabase.table("lgs_denemeleri").delete().eq("deneme_adi", deneme_adi).in_("ogrenci_id", ogr_idler).execute()
                                        st.success(f"✅ '{deneme_adi}' sınavına ait tüm kayıtlar silindi.")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Sınav silinirken hata oluştu: {str(e)}")
                            
                            deneme_verileri_res = supabase.table("lgs_denemeleri").select("*").eq("deneme_adi", deneme_adi).in_("ogrenci_id", ogr_idler).execute()
                            mevcut_veriler = {d["ogrenci_id"]: d for d in deneme_verileri_res.data}
                            
                            lgs_tablo_verisi = []
                            for ogr in ogrenciler:
                                d_veri = mevcut_veriler.get(ogr["id"], {})
                                lgs_tablo_verisi.append({
                                    "Öğrenci ID": ogr["id"], "Kayıt ID": d_veri.get("id", None), "Öğrenci Adı": ogr["ad_soyad"],
                                    "Katılım": "Katıldı" if pd.notnull(d_veri.get("id", None)) else "Girmedi",
                                    "Türkçe D": d_veri.get("turkce_d", 0), "Türkçe Y": d_veri.get("turkce_y", 0),
                                    "Matematik D": d_veri.get("mat_d", 0), "Matematik Y": d_veri.get("mat_y", 0),
                                    "Fen D": d_veri.get("fen_d", 0), "Fen Y": d_veri.get("fen_y", 0),
                                    "Sosyal/İnkılap D": d_veri.get("ink_d", 0), "Sosyal/İnkılap Y": d_veri.get("ink_y", 0),
                                    "Din D": d_veri.get("din_d", 0), "Din Y": d_veri.get("din_y", 0),
                                    "İngilizce D": d_veri.get("ing_d", 0), "İngilizce Y": d_veri.get("ing_y", 0),
                                    "LGS Puanı": float(d_veri.get("lgs_puani", 200.0)),
                                    "Yüzdelik Dilim": float(d_veri.get("yuzdelik_dilim", 100.0))
                                })
                            df_lgs_toplu = pd.DataFrame(lgs_tablo_verisi)
                        else:
                            st.info("Kayıtlı deneme sınavı verisi bulunamadı.")
                            df_lgs_toplu = pd.DataFrame()
                            deneme_adi = ""

                    if not df_lgs_toplu.empty:
                        duzenlenmis_lgs_df = st.data_editor(
                            df_lgs_toplu,
                            column_config={
                                "Öğrenci ID": None, "Kayıt ID": None,
                                "Öğrenci Adı": st.column_config.TextColumn(disabled=True),
                                "Katılım": st.column_config.SelectboxColumn("Katılım", options=["Katıldı", "Girmedi"], required=True),
                                "Türkçe D": st.column_config.NumberColumn(min_value=0, max_value=20, step=1),
                                "Türkçe Y": st.column_config.NumberColumn(min_value=0, max_value=20, step=1),
                                "Matematik D": st.column_config.NumberColumn(min_value=0, max_value=20, step=1),
                                "Matematik Y": st.column_config.NumberColumn(min_value=0, max_value=20, step=1),
                                "Fen D": st.column_config.NumberColumn(min_value=0, max_value=20, step=1),
                                "Fen Y": st.column_config.NumberColumn(min_value=0, max_value=20, step=1),
                                "Sosyal/İnkılap D": st.column_config.NumberColumn(min_value=0, max_value=10, step=1),
                                "Sosyal/İnkılap Y": st.column_config.NumberColumn(min_value=0, max_value=10, step=1),
                                "Din D": st.column_config.NumberColumn(min_value=0, max_value=10, step=1),
                                "Din Y": st.column_config.NumberColumn(min_value=0, max_value=10, step=1),
                                "İngilizce D": st.column_config.NumberColumn(min_value=0, max_value=10, step=1),
                                "İngilizce Y": st.column_config.NumberColumn(min_value=0, max_value=10, step=1),
                                "LGS Puanı": st.column_config.NumberColumn(min_value=200.0, max_value=500.0, step=0.01, format="%.2f"),
                                "Yüzdelik Dilim": st.column_config.NumberColumn(min_value=0.01, max_value=100.0, step=0.01, format="%.2f")
                            }, hide_index=True, use_container_width=True
                        )
                        
                        if st.button("Toplu Sınav Verilerini Veritabanına İşle", type="primary", use_container_width=True):
                            if not deneme_adi:
                                st.error("Lütfen deneme sınavı adını giriniz.")
                            else:
                                hata_var_mi = False
                                for index, row in duzenlenmis_lgs_df.iterrows():
                                    if row["Katılım"] == "Katıldı":
                                        if (row["Türkçe D"]+row["Türkçe Y"]>20) or (row["Matematik D"]+row["Matematik Y"]>20) or (row["Fen D"]+row["Fen Y"]>20) or (row["Sosyal/İnkılap D"]+row["Sosyal/İnkılap Y"]>10) or (row["Din D"]+row["Din Y"]>10) or (row["İngilizce D"]+row["İngilizce Y"]>10):
                                            st.error(f"❌ {row['Öğrenci Adı']} için ders kısıt sınırları aşıldı.")
                                            hata_var_mi = True
                                            break
                                
                                if not hata_var_mi:
                                    try:
                                        for index, row in duzenlenmis_lgs_df.iterrows():
                                            k_id = row.get("Kayıt ID")
                                            
                                            if row["Katılım"] == "Girmedi":
                                                if pd.notnull(k_id):
                                                    supabase.table("lgs_denemeleri").delete().eq("id", int(k_id)).execute()
                                                continue
                                                
                                            kayit_paketi = {
                                                "ogrenci_id": int(row["Öğrenci ID"]), "deneme_adi": deneme_adi,
                                                "turkce_d": int(row["Türkçe D"]), "turkce_y": int(row["Türkçe Y"]),
                                                "mat_d": int(row["Matematik D"]), "mat_y": int(row["Matematik Y"]),
                                                "fen_d": int(row["Fen D"]), "fen_y": int(row["Fen Y"]),
                                                "ink_d": int(row["Sosyal/İnkılap D"]), "ink_y": int(row["Sosyal/İnkılap Y"]),
                                                "din_d": int(row["Din D"]), "din_y": int(row["Din Y"]),
                                                "ing_d": int(row["İngilizce D"]), "ing_y": int(row["İngilizce Y"]),
                                                "lgs_puani": float(row["LGS Puanı"]) if pd.notnull(row["LGS Puanı"]) else 200.0,
                                                "yuzdelik_dilim": float(row["Yüzdelik Dilim"]) if pd.notnull(row["Yüzdelik Dilim"]) else 100.0
                                            }
                                            if pd.notnull(k_id):
                                                supabase.table("lgs_denemeleri").update(kayit_paketi).eq("id", int(k_id)).execute()
                                            else:
                                                supabase.table("lgs_denemeleri").insert(kayit_paketi).execute()
                                        st.success("✅ Veriler başarıyla veri tabanına işlendi.")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Sınav verileri işlenirken hata oluştu: {str(e)}")

                # --- LGS TAB 2: SINIF GENEL SIRALAMASI MATRİSİ ---
                with tab_lgs2:
                    mevcut_denemeler_res = supabase.table("lgs_denemeleri").select("deneme_adi").in_("ogrenci_id", ogr_idler).execute()
                    if mevcut_denemeler_res.data:
                        benzersiz_denemeler = list(set([d["deneme_adi"] for d in mevcut_denemeler_res.data]))
                        secili_deneme_analiz = st.selectbox("Başarı Sıralaması Gösterilecek Sınavı Seçin", benzersiz_denemeler)
                        
                        s_veri_res = supabase.table("lgs_denemeleri").select("*").eq("deneme_adi", secili_deneme_analiz).in_("ogrenci_id", ogr_idler).execute()
                        if s_veri_res.data:
                            df_s = pd.DataFrame(s_veri_res.data)
                            if "lgs_puani" not in df_s.columns: df_s["lgs_puani"] = 200.0
                            if "yuzdelik_dilim" not in df_s.columns: df_s["yuzdelik_dilim"] = 100.0
                            
                            df_s["lgs_puani"] = pd.to_numeric(df_s["lgs_puani"], errors='coerce').fillna(200.0)
                            df_s["yuzdelik_dilim"] = pd.to_numeric(df_s["yuzdelik_dilim"], errors='coerce').fillna(100.0)
                            
                            df_s["Öğrenci"] = df_s["ogrenci_id"].apply(lambda x: next((ogr["ad_soyad"] for ogr in ogrenciler if ogr["id"] == x), "Bilinmiyor"))
                            
                            df_s["Türkçe Net"] = df_s["turkce_d"] - (df_s["turkce_y"] / 3)
                            df_s["Matematik Net"] = df_s["mat_d"] - (df_s["mat_y"] / 3)
                            df_s["Fen Net"] = df_s["fen_d"] - (df_s["fen_y"] / 3)
                            df_s["Sosyal/İnkılap Net"] = df_s["ink_d"] - (df_s["ink_y"] / 3)
                            df_s["Din Net"] = df_s["din_d"] - (df_s["din_y"] / 3)
                            df_s["İngilizce Net"] = df_s["ing_d"] - (df_s["ing_y"] / 3)
                            df_s["Toplam Net"] = df_s[["Türkçe Net", "Matematik Net", "Fen Net", "Sosyal/İnkılap Net", "Din Net", "İngilizce Net"]].sum(axis=1)
                            
                            df_s = df_s.sort_values(by="lgs_puani", ascending=False).reset_index(drop=True)
                            df_s.index += 1
                            df_s = df_s.reset_index().rename(columns={"index": "Sınıf Derecesi"})
                            
                            tablo_s = df_s[["Sınıf Derecesi", "Öğrenci", "Türkçe Net", "Matematik Net", "Fen Net", "Sosyal/İnkılap Net", "Din Net", "İngilizce Net", "Toplam Net", "lgs_puani", "yuzdelik_dilim"]].rename(columns={"lgs_puani": "LGS Puanı", "yuzdelik_dilim": "Yüzdelik Dilim (%)"})
                            st.subheader(f"🏆 {secili_deneme_analiz} Sınavı - Başarı ve Puan Sıralaması")
                            st.dataframe(tablo_s, hide_index=True, use_container_width=True)
                            
                            html_tablo_s = tablo_s.to_html(border=1, index=False, justify='center')
                            html_icerik_s = f"""
                            <html>
                            <head><meta charset='utf-8'><title>{secilen_sinif_lgs} Sıralama Raporu</title></head>
                            <body onload='window.print()'>
                                <div style="margin-bottom: 20px; overflow: hidden;">
                                    {logo_html}
                                    <h2 style='text-align:center;'>Sadiye ve Abdullah Tan Ortaokulu<br>{secilen_sinif_lgs} Sınıfı {secili_deneme_analiz} Sınavı Başarı Sıralaması</h2>
                                </div>
                                {html_tablo_s}
                            </body>
                            </html>
                            """
                            st.download_button(label="📄 Sınıf Genel Başarı Çizelgesini PDF İndir", data=html_icerik_s, file_name=f"{secilen_sinif_lgs}_{secili_deneme_analiz}_Siralama.html", mime="text/html")
                    else:
                        st.info("Sıralama oluşturulacak deneme sınavı kaydı bulunmuyor.")

                # --- LGS TAB 3: ÖĞRENCİ ÖZEL ANALİZİ VE GELİŞMİŞ KIYASLAMA ---
                with tab_lgs3:
                    secilen_ogr_analiz = st.selectbox("Analiz Edilecek Öğrenciyi Seçin", list(ogr_secenekleri.keys()), key="lgs_ogr_secim_analiz")
                    secilen_ogr_id_analiz = ogr_secenekleri[secilen_ogr_analiz]
                    
                    lgs_res = supabase.table("lgs_denemeleri").select("*").eq("ogrenci_id", secilen_ogr_id_analiz).execute()
                    
                    if not lgs_res.data:
                        st.info("Bu öğrenciye ait herhangi bir LGS deneme dökümü bulunmamaktadır.")
                    else:
                        df_lgs = pd.DataFrame(lgs_res.data)
                        if "lgs_puani" not in df_lgs.columns: df_lgs["lgs_puani"] = 200.0
                        if "yuzdelik_dilim" not in df_lgs.columns: df_lgs["yuzdelik_dilim"] = 100.0
                        
                        df_lgs["lgs_puani"] = pd.to_numeric(df_lgs["lgs_puani"], errors='coerce').fillna(200.0)
                        df_lgs["yuzdelik_dilim"] = pd.to_numeric(df_lgs["yuzdelik_dilim"], errors='coerce').fillna(100.0)
                        
                        df_lgs["Türkçe Net"] = df_lgs["turkce_d"] - (df_lgs["turkce_y"] / 3)
                        df_lgs["Matematik Net"] = df_lgs["mat_d"] - (df_lgs["mat_y"] / 3)
                        df_lgs["Fen Net"] = df_lgs["fen_d"] - (df_lgs["fen_y"] / 3)
                        df_lgs["Sosyal/İnkılap Net"] = df_lgs["ink_d"] - (df_lgs["ink_y"] / 3)
                        df_lgs["Din Net"] = df_lgs["din_d"] - (df_lgs["din_y"] / 3)
                        df_lgs["İngilizce Net"] = df_lgs["ing_d"] - (df_lgs["ing_y"] / 3)
                        df_lgs["Toplam Net"] = df_lgs[["Türkçe Net", "Matematik Net", "Fen Net", "Sosyal/İnkılap Net", "Din Net", "İngilizce Net"]].sum(axis=1)
                        
                        son_deneme_verisi = df_lgs.iloc[-1]
                        ortalama_puan = round(df_lgs["lgs_puani"].mean(), 2)
                        en_yuksek_puan = round(df_lgs["lgs_puani"].max(), 2)
                        
                        toplam_dogru = int(son_deneme_verisi[["turkce_d", "mat_d", "fen_d", "ink_d", "din_d", "ing_d"]].sum())
                        toplam_yanlis = int(son_deneme_verisi[["turkce_y", "mat_y", "fen_y", "ink_y", "din_y", "ing_y"]].sum())
                        toplam_isaretlenen = toplam_dogru + toplam_yanlis
                        isabet_orani = (toplam_dogru / toplam_isaretlenen * 100) if toplam_isaretlenen > 0 else 0
                        
                        ders_listesi = ["Türkçe Net", "Matematik Net", "Fen Net", "Sosyal/İnkılap Net", "Din Net", "İngilizce Net"]
                        std_sapmalar = df_lgs[ders_listesi].std().fillna(0)
                        ortalamalar = df_lgs[ders_listesi].mean()
                        
                        guclu_ders = ortalamalar.idxmax().replace(" Net", "")
                        en_istikrarsiz_ders = std_sapmalar.idxmax().replace(" Net", "")
                        en_sapma_degeri = std_sapmalar.max()
                        
                        sub_tab1, sub_tab2 = st.tabs(["📊 Genel Süreç Analiz Raporu", "⚖️ Gelişmiş Sınav Karşılaştırma (Kafa Kafaya)"])
                        
                        with sub_tab1:
                            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                            col_m1.metric("Son Sınav Puanı", f"{son_deneme_verisi['lgs_puani']:.2f} Puan")
                            col_m2.metric("Süreç Puan Ortalaması", f"{ortalama_puan} Puan")
                            col_m3.metric("Ulaşılan En Yüksek Puan", f"{en_yuksek_puan} Puan")
                            col_m4.metric("Son Yüzdelik Dilim", f"% {son_deneme_verisi['yuzdelik_dilim']:.2f}")
                            
                            isabet_yorumu = ""
                            if isabet_orani >= 85:
                                isabet_yorumu = "Öğrenci konu bütünlüğüne hakimdir. İşlem veya okuma hatası minimum düzeydedir. Deneme pratiği aynı rutinde sürdürülmelidir."
                            elif isabet_orani >= 65:
                                isabet_yorumu = "Öğrenci riskli işaretleme yapmaktadır veya spesifik alt kazanımlarda kavram yanılgılarına sahiptir. Yanlış yapılan soruların analiz edilmesi gereklidir."
                            else:
                                isabet_yorumu = "Kritik seviye. Rastgele işaretleme davranışı tespit edilmiştir veya konunun temel kazanımları oturmamıştır. Konu anlatım süreçlerine geri dönülmelidir."

                            risk_metinleri = []
                            if isabet_orani < 65:
                                risk_metinleri.append(f"Genel isabet oranı (%{isabet_orani:.1f}) kritik seviyededir.")
                            if en_sapma_degeri >= 2.5:
                                risk_metinleri.append(f"'{en_istikrarsiz_ders}' dersinde yüksek performans dalgalanması (Sapma: {en_sapma_degeri:.2f}) mevcuttur.")

                            if risk_metinleri:
                                st.error(f"⚠️ **KRİTİK AKADEMİK RİSK UYARISI:** {' '.join(risk_metinleri)}")

                            st.write("#### 📖 Kavramsal Çerçeve (Metrik Tanımları)")
                            st.info("""
                            * **İsabet Oranı (Emin Olma Yüzdesi):** Doğru yapılan soru sayısının, toplam işaretlenen soru sayısına oranıdır. Öğrencinin bilmediği sorularda boş bırakma stratejisi geliştirebilme veya gereksiz risk alarak net kaybetme durumunu ölçer. Hedef %85 üzeridir.
                            * **Performans Tutarlılığı (Standart Sapma):** Sınavlar arasındaki net değişim aralığıdır. Düşük sapma bilgilerin kalıcı olarak öğrenildiğini; yüksek sapma ise performansın soru tipine veya sınav zorluğuna göre istikrarsızlaştığını gösterir.
                            """)

                            st.write("#### 🔍 Öğrenciye Özel Dinamik Teşhis Raporu")
                            st.markdown(f"**🎯 Sınav İsabet Oranı:** `%{isabet_orani:.1f}`")
                            st.write(f"**Analiz Sonucu:** {isabet_yorumu}")

                            st.markdown(f"**📉 Performans Tutarlılığı:** En yüksek dalgalanma olan ders: `{en_istikrarsiz_ders}`")
                            st.write("**Analiz Sonucu:** Bu dersteki istikrarsızlık, öğrencinin soru tipine veya sınav zorluğuna göre performansının çok değiştiğini, bilgilerin henüz tam olarak pekişmediğini gösterir.")

                            st.markdown("**📈 Branş İvmesi (Son 3 Sınav Yönelimi):**")
                            ivme_liste = []
                            if len(df_lgs) >= 3:
                                for ders in ders_listesi:
                                    ders_adi = ders.replace(" Net", "")
                                    son_3_veri = df_lgs[ders].iloc[-3:].tolist()
                                    egim = (son_3_veri[2] - son_3_veri[0]) / 2
                                    if egim > 0.5:
                                        ivme_liste.append(f"<li><b>{ders_adi}:</b> :green[Yükseliş İvmesinde] (+{egim:.2f} net hızı)</li>")
                                    elif egim < -0.5:
                                        ivme_liste.append(f"<li><b>{ders_adi}:</b> :red[Düşüş Eğiliminde] ({egim:.2f} net gerileme)</li>")
                                    else:
                                        ivme_liste.append(f"<li><b>{ders_adi}:</b> Yatay / Stabil Seyir</li>")
                                st.markdown(f"<ul>{''.join(ivme_liste)}</ul>", unsafe_allow_html=True)
                            else:
                                st.write("Son 3 sınav yöneliminin ölçülmesi için en az 3 sınav kaydı bulunmalıdır.")
                            
                            st.write("#### 📊 Süreç İlerleme Grafikleri")
                            col_g1, col_g2, col_g3 = st.columns(3)
                            
                            with col_g1:
                                st.write("**LGS Puan Gelişimi**")
                                fig_puan, ax_puan = plt.subplots(figsize=(5, 3))
                                ax_puan.plot(df_lgs["deneme_adi"], df_lgs["lgs_puani"], marker='o', color='#2196F3', linewidth=2)
                                ax_puan.tick_params(axis='x', rotation=45)
                                for label in ax_puan.get_xticklabels():
                                    label.set_ha('right')
                                ax_puan.tick_params(axis='both', labelsize=8)
                                ax_puan.grid(True, linestyle='--', alpha=0.4)
                                st.pyplot(fig_puan)
                                
                                buf_puan = io.BytesIO()
                                fig_puan.savefig(buf_puan, format='png', bbox_inches='tight', dpi=100)
                                buf_puan.seek(0)
                                puan_trend_b64 = base64.b64encode(buf_puan.read()).decode('utf-8')
                                plt.close(fig_puan)

                            with col_g2:
                                st.write("**Toplam Net Gelişimi**")
                                fig_net, ax_net = plt.subplots(figsize=(5, 3))
                                ax_net.plot(df_lgs["deneme_adi"], df_lgs["Toplam Net"], marker='s', color='#4CAF50', linewidth=2)
                                ax_net.yaxis.set_major_locator(MultipleLocator(1))
                                ax_net.tick_params(axis='x', rotation=45)
                                for label in ax_net.get_xticklabels():
                                    label.set_ha('right')
                                ax_net.tick_params(axis='both', labelsize=8)
                                ax_net.grid(True, linestyle='--', alpha=0.4)
                                st.pyplot(fig_net)
                                
                                buf_net = io.BytesIO()
                                fig_net.savefig(buf_net, format='png', bbox_inches='tight', dpi=100)
                                buf_net.seek(0)
                                net_trend_b64 = base64.b64encode(buf_net.read()).decode('utf-8')
                                plt.close(fig_net)

                            with col_g3:
                                st.write("**Yüzdelik Dilim Trendi (%)**")
                                fig_yuzde, ax_yuzde = plt.subplots(figsize=(5, 3))
                                ax_yuzde.plot(df_lgs["deneme_adi"], df_lgs["yuzdelik_dilim"], marker='v', color='#FF9800', linewidth=2)
                                ax_yuzde.invert_yaxis()
                                ax_yuzde.tick_params(axis='x', rotation=45)
                                for label in ax_yuzde.get_xticklabels():
                                    label.set_ha('right')
                                ax_yuzde.tick_params(axis='both', labelsize=8)
                                ax_yuzde.grid(True, linestyle='--', alpha=0.4)
                                st.pyplot(fig_yuzde)
                                
                                buf_yuzde = io.BytesIO()
                                fig_yuzde.savefig(buf_yuzde, format='png', bbox_inches='tight', dpi=100)
                                buf_yuzde.seek(0)
                                yuzde_trend_b64 = base64.b64encode(buf_yuzde.read()).decode('utf-8')
                                plt.close(fig_yuzde)
                                
                            st.write("#### 📈 Ders Bazlı Net İlerleme Grafikleri")
                            cols_ders = st.columns(2)
                            ders_grafikleri_html = ""
                            
                            for idx, ders in enumerate(ders_listesi):
                                fig_ders, ax_ders = plt.subplots(figsize=(5, 3))
                                ax_ders.plot(df_lgs["deneme_adi"], df_lgs[ders], marker='o', color='#673AB7', linewidth=2)
                                ax_ders.set_title(f"{ders} Trendi", fontsize=10)
                                ax_ders.yaxis.set_major_locator(MultipleLocator(1))
                                ax_ders.tick_params(axis='x', rotation=45)
                                for label in ax_ders.get_xticklabels():
                                    label.set_ha('right')
                                ax_ders.tick_params(axis='both', labelsize=8)
                                ax_ders.grid(True, linestyle='--', alpha=0.4)
                                max_val = 20 if ders in ["Türkçe Net", "Matematik Net", "Fen Net"] else 10
                                ax_ders.set_ylim(-1, max_val + 1)
                                
                                with cols_ders[idx % 2]:
                                    st.pyplot(fig_ders)
                                    
                                buf_ders = io.BytesIO()
                                fig_ders.savefig(buf_ders, format='png', bbox_inches='tight', dpi=100)
                                buf_ders.seek(0)
                                b64_ders = base64.b64encode(buf_ders.read()).decode('utf-8')
                                plt.close(fig_ders)
                                ders_grafikleri_html += f'<div style="display: inline-block; width: 48%; margin: 1%; text-align: center;"><img src="data:image/png;base64,{b64_ders}" style="width: 100%; max-width: 300px;"></div>'

                        with sub_tab2:
                            st.write("Karşılaştırılacak iki farklı deneme seçerek kafa kafaya (Head-to-Head) performans analizi yapabilirsiniz.")
                            deneme_listesi = df_lgs["deneme_adi"].tolist()
                            varsayilan_secim = deneme_listesi[-2:] if len(deneme_listesi) >= 2 else deneme_listesi
                            karsilastirma_secimi = st.multiselect("Karşılaştırılacak İki Sınavı Seçin", deneme_listesi, default=varsayilan_secim)
                            
                            if len(karsilastirma_secimi) != 2:
                                st.warning("Lütfen tam olarak iki (2) adet deneme sınavı seçiniz.")
                            else:
                                d1_isim, d2_isim = karsilastirma_secimi[0], karsilastirma_secimi[1]
                                d1_veri = df_lgs[df_lgs["deneme_adi"] == d1_isim].iloc[0]
                                d2_veri = df_lgs[df_lgs["deneme_adi"] == d2_isim].iloc[0]
                                
                                fark_verisi = []
                                for d in ders_listesi + ["Toplam Net", "lgs_puani", "yuzdelik_dilim"]:
                                    v1 = d1_veri[d]
                                    v2 = d2_veri[d]
                                    fark = v2 - v1
                                    
                                    if d == "yuzdelik_dilim":
                                        f_icon = "🟢" if fark < 0 else ("🔴" if fark > 0 else "⚪")
                                    else:
                                        f_icon = "🟢" if fark > 0 else ("🔴" if fark < 0 else "⚪")
                                        
                                    fark_metni = f"{fark:+.2f} {f_icon}" if fark != 0 else "0.00 ⚪"
                                    etiket_isim = d.replace(" Net","").replace("lgs_puani","LGS Puanı").replace("yuzdelik_dilim", "Yüzdelik Dilim")
                                    
                                    fark_verisi.append({
                                        "Kriter": etiket_isim,
                                        d1_isim: f"{v1:.2f}",
                                        d2_isim: f"{v2:.2f}",
                                        "Fark (Delta)": fark_metni,
                                        "_f": fark 
                                    })
                                df_fark = pd.DataFrame(fark_verisi)
                                
                                df_dersler_fark = df_fark.iloc[:-3].copy() 
                                df_dersler_fark["_f"] = pd.to_numeric(df_dersler_fark["_f"]) 
                                
                                max_f = df_dersler_fark.loc[df_dersler_fark["_f"].idxmax()] 
                                min_f_row = df_dersler_fark.loc[df_dersler_fark["_f"].idxmin()]
                                puan_farki = df_fark.iloc[-2]["_f"]
                                
                                yorum_metni = f"Seçilen iki sınav arasında öğrenci **en büyük sıçramayı {max_f['Kriter']} (+{max_f['_f']:.2f} net)** dersinde yaparken, "
                                if min_f_row["_f"] < 0:
                                    yorum_metni += f"**en ciddi net kaybını {min_f_row['Kriter']} ({min_f_row['_f']:.2f} net)** dersinde yaşamıştır. "
                                else:
                                    yorum_metni += f"hiçbir derste net gerilemesi yaşamamıştır (En düşük hız: {min_f_row['Kriter']}). "
                                
                                puan_yonu = "pozitif yönlü" if puan_farki > 0 else ("negatif yönlü" if puan_farki < 0 else "sabit")
                                yorum_metni += f"Genel puan tablosunda ise **{puan_yonu} ({puan_farki:+.2f} Puan)** bir değişim görülmektedir."
                                
                                st.info(f"**🤖 Otomatik Karşılaştırma Analizi:** {yorum_metni}")
                                
                                col_radar, col_tablo = st.columns([1, 1])
                                with col_radar:
                                    st.write(f"**Gruplanmış Çubuk Karşılaştırma Grafiği**")
                                    labels_ui = ["Mat","Türkçe","Fen","Sosyal/İnkılap","Din","İng"]
                                    vals1 = [d1_veri[d] for d in ders_listesi]
                                    vals2 = [d2_veri[d] for d in ders_listesi]
                                    
                                    x = np.arange(len(labels_ui))
                                    width = 0.35
                                    
                                    fig_bar, ax_bar = plt.subplots(figsize=(6, 4))
                                    ax_bar.bar(x - width/2, vals1, width, label=d1_isim, color='#90CAF9')
                                    ax_bar.bar(x + width/2, vals2, width, label=d2_isim, color='#FFCC80')
                                    ax_bar.set_ylabel('Net Sayısı')
                                    ax_bar.set_xticks(x)
                                    ax_bar.set_xticklabels(labels_ui, fontsize=8)
                                    ax_bar.legend()
                                    ax_bar.grid(axis='y', linestyle='--', alpha=0.5)
                                    st.pyplot(fig_bar)
                                    
                                    buf_bar = io.BytesIO()
                                    plt.savefig(buf_bar, format='png', bbox_inches='tight', dpi=130)
                                    buf_bar.seek(0)
                                    bar_img_b64 = base64.b64encode(buf_bar.read()).decode('utf-8')
                                    plt.close(fig_bar)
                                    
                                with col_tablo:
                                    st.write(f"**Net Değişim Veri Matrisi**")
                                    st.dataframe(df_fark.drop(columns=["_f"]), hide_index=True, use_container_width=True)

                                html_karsilastirma = f"""
                                <html><head><meta charset='utf-8'><style>
                                    body {{ font-family: Arial; margin: 40px; color: #333; }}
                                    .h-container {{ margin-bottom: 30px; overflow: hidden; }}
                                    .h {{ text-align: center; background: #eee; padding: 10px; border-radius: 5px; margin-top: 10px; }}
                                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                                    th, td {{ border: 1px solid #ddd; padding: 10px; text-align: center; }}
                                    th {{ background: #f5f5f5; }}
                                    .img-c {{ text-align: center; margin-top: 30px; }}
                                    .info {{ background: #f9f9f9; border-left: 5px solid #FF9800; padding: 15px; margin-top: 20px; font-size: 13px; line-height: 1.5; }}
                                </style></head>
                                <body onload='window.print()'>
                                    <div class="h-container">
                                        {logo_html}
                                        <div class='h'><h2>LGS SINAV KARŞILAŞTIRMA RAPORU</h2></div>
                                    </div>
                                    <p><b>Öğrenci:</b> {secilen_ogr_analiz} | <b>Sınıf:</b> {secilen_sinif_lgs}</p>
                                    <p><b>Karşılaştırılan Sınavlar:</b> {d1_isim} vs {d2_isim}</p>
                                    <table>
                                        <thead><tr><th>Kriter</th><th>{d1_isim}</th><th>{d2_isim}</th><th>Fark (Değişim)</th></tr></thead>
                                        <tbody>
                                            {"".join([f"<tr><td>{r['Kriter']}</td><td>{r[d1_isim]}</td><td>{r[d2_isim]}</td><td>{r['Fark (Delta)']}</td></tr>" for i,r in df_fark.iterrows()])}
                                        </tbody>
                                    </table>
                                    <div class='img-c'><img src='data:image/png;base64,{bar_img_b64}' style='width: 100%; max-width: 650px;'></div>
                                    <div class='info'>
                                        <b>Pedagojik Karşılaştırma Yorumu:</b><br/>
                                        Seçilen sınav periyotları incelendiğinde öğrencinin en belirgin ivmelenmeyi <b>{max_f['Kriter']}</b> dersinde kaydettiği saptanmıştır. Süreç çalışma planlamasının gelişim yönlerine göre optimize edilmesi önerilir.
                                    </div>
                                </body></html>
                                """
                                st.divider()
                                st.write("#### 💾 Seçili Sınav Karşılaştırma Dökümünü PDF İndir")
                                st.download_button("📄 Karşılaştırma Raporunu PDF İndir", html_karsilastirma, file_name=f"{secilen_ogr_analiz}_Karsilastirma.html", mime="text/html")

                        df_pdf_tablo = df_lgs[["deneme_adi", "Türkçe Net", "Matematik Net", "Fen Net", "Sosyal/İnkılap Net", "Din Net", "İngilizce Net", "Toplam Net", "lgs_puani", "yuzdelik_dilim"]].rename(columns={"deneme_adi":"Sınav", "lgs_puani":"LGS Puanı", "yuzdelik_dilim": "Yüzdelik Dilim (%)"})
                        html_table_lgs = df_pdf_tablo.to_html(border=1, index=False, justify='center')
                        
                        pdf_ivme_metinleri = "<ul>" + "".join(ivme_liste).replace(":green[","<span style='color:green;font-weight:bold;'>").replace(":red[","<span style='color:red;font-weight:bold;'>").replace("]","</span>") + "</ul>" if len(df_lgs) >= 3 else "<p>Yetersiz veri.</p>"
                        
                        pdf_risk_html = ""
                        if risk_metinleri:
                            pdf_risk_html = f"""
                            <div style="background-color: #ffebee; border-left: 5px solid #f44336; padding: 15px; margin-bottom: 20px;">
                                <strong style="color: #f44336; font-size: 14px;">⚠️ KRİTİK AKADEMİK RİSK UYARISI:</strong><br>
                                <span style="font-size: 13px; color: #333;">{' '.join(risk_metinleri)}</span>
                            </div>
                            """

                        lgs_pdf_html = f"""
                        <html>
                        <head><meta charset="utf-8"><style>
                            body {{ font-family: Arial, sans-serif; margin: 35px; color: #333; }}
                            .title-container {{ margin-bottom: 30px; overflow: hidden; }}
                            .title {{ text-align: center; font-size: 22px; font-weight: bold; margin-bottom: 5px; margin-top: 10px; }}
                            .subtitle {{ text-align: center; font-size: 14px; color: #555; }}
                            .card-box {{ display: flex; justify-content: space-between; gap: 15px; margin-bottom: 25px; }}
                            .card {{ flex: 1; border: 1px solid #ccc; padding: 12px; text-align: center; background-color: #fafafa; border-radius: 5px; }}
                            .card h4 {{ margin: 0 0 6px 0; font-size: 12px; color: #666; text-transform: uppercase; }}
                            .card p {{ margin: 0; font-size: 18px; font-weight: bold; color: #111; }}
                            .section-title {{ font-size: 14px; font-weight: bold; color: #fff; background-color: #2196F3; padding: 6px 10px; margin-top: 25px; border-radius: 3px; }}
                            table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 12px; }}
                            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
                            th {{ background-color: #f5f5f5; }}
                            .graph-container {{ text-align: center; margin-top: 20px; }}
                            .graph-img {{ width: 32%; display: inline-block; vertical-align: top; }}
                            .pedagogic-box {{ font-size: 12px; line-height: 1.6; background-color: #f9fbfd; border-left: 4px solid #2196F3; padding: 15px; margin-top: 15px; }}
                            .pedagogic-title {{ font-weight: bold; color: #111; margin-top: 10px; font-size: 13px; }}
                        </style></head>
                        <body onload="window.print()">
                            <div class="title-container">
                                {logo_html}
                                <div class="title">LGS HAZIRLIK SÜRECİ AKADEMİK RAPORU</div>
                                <div class="subtitle">Sadiye ve Abdullah Tan Ortaokulu - Genel Süreç Analizi</div>
                            </div>
                            {pdf_risk_html}
                            <table style="width:100%; border:none; margin-bottom:20px;">
                                <tr>
                                    <td style="text-align:left; border:none; font-size:14px;"><b>Öğrenci Adı Soyadı:</b> {secilen_ogr_analiz}</td>
                                    <td style="text-align:right; border:none; font-size:14px;"><b>Sınıfı:</b> {secilen_sinif_lgs} | <b>Rapor Tarihi:</b> {date.today().strftime('%d.%m.%Y')}</td>
                                </tr>
                            </table>
                            <div class="card-box">
                                <div class="card"><h4>Son Sınav Puanı</h4><p>{son_deneme_verisi['lgs_puani']:.2f}</p></div>
                                <div class="card"><h4>Süreç Puan Ortalaması</h4><p>{ortalama_puan}</p></div>
                                <div class="card"><h4>Ulaşılan En Yüksek Puan</h4><p>{en_yuksek_puan}</p></div>
                                <div class="card"><h4>Son Yüzdelik Dilim</h4><p>% {son_deneme_verisi['yuzdelik_dilim']:.2f}</p></div>
                            </div>
                            <div class="section-title">📊 Deneme Sınavları Net ve Skor Dağılım Geçmişi</div>
                            {html_table_lgs}
                            <div class="section-title">📈 Ayrıştırılmış İlerleme ve Trend Grafikleri</div>
                            <div class="graph-container">
                                <img class="graph-img" src="data:image/png;base64,{puan_trend_b64}">
                                <img class="graph-img" src="data:image/png;base64,{net_trend_b64}">
                                <img class="graph-img" src="data:image/png;base64,{yuzde_trend_b64}">
                            </div>
                            <div class="section-title">📈 Ders Bazlı İlerleme Grafikleri</div>
                            <div style="text-align: center; margin-top: 10px;">
                                {ders_grafikleri_html}
                            </div>
                            <div class="section-title">🎯 Dinamik Teşhis Raporu ve Analiz Çıktıları</div>
                            <div class="pedagogic-box">
                                <div class="pedagogic-title">1. Sınav İsabet Oranı (Emin Olma Yüzdesi): %{isabet_orani:.1f}</div>
                                {isabet_yorumu}
                                <div class="pedagogic-title">2. Performans Tutarlılığı (Standart Sapma): {en_istikrarsiz_ders}</div>
                                Bu dersteki istikrarsızlık, öğrencinin soru tipine veya sınav zorluğuna göre performansının çok değiştiğini, bilgilerin henüz tam olarak pekişmediğini gösterir.
                                <div class="pedagogic-title">3. Branş İvmesi (Son 3 Sınav Yönelimi):</div>
                                {pdf_ivme_metinleri}
                            </div>
                        </body></html>
                        """
                        st.divider()
                        st.write("#### 💾 Bireysel Genel Gelişim Süreç Raporunu PDF İndir")
                        st.download_button(
                            label="📄 LGS Özel Genel Hazırlık Raporunu PDF İndir",
                            data=lgs_pdf_html,
                            file_name=f"{secilen_ogr_analiz}_LGS_Akademik_Raporu.html",
                            mime="text/html"
                        )
        except Exception as e:
            st.error(f"Sistem Hatası: LGS veritabanına erişilemedi. Detay: {str(e)}")

# --- MODÜL 6: ŞİFRE İŞLEMLERİ (SADECE ADMİN) ---
elif menu == "🔑 Şifre İşlemleri":
    st.header("🔑 Şifre Yönetim Paneli")
    st.info("Sistemdeki tüm yönetici ve öğretmen hesaplarının şifrelerini buradan güncelleyebilirsiniz.")
    
    try:
        k_res = supabase.table("kullanicilar").select("kullanici_adi, brans, rol").execute()
        if k_res.data:
            secenekler = []
            for k in k_res.data:
                etiket = f"{k['kullanici_adi']} ({'Yönetici' if k['rol'] == 'admin' else k['brans'] + ' Öğretmeni'})"
                secenekler.append(etiket)
                
            secili_etiket = st.selectbox("Şifresi Değiştirilecek Hesabı Seçin", secenekler)
            secili_k_adi = secili_etiket.split(" ")[0] 
            
            with st.form("sifre_formu", clear_on_submit=True):
                yeni_sifre = st.text_input("Yeni Şifre", type="password")
                yeni_sifre_tekrar = st.text_input("Yeni Şifre (Tekrar)", type="password")
                
                if st.form_submit_button("Şifreyi Güncelle", type="primary"):
                    if not yeni_sifre or not yeni_sifre_tekrar:
                        st.warning("Şifre alanları boş bırakılamaz.")
                    elif yeni_sifre != yeni_sifre_tekrar:
                        st.error("Girdiğiniz şifreler eşleşmiyor.")
                    elif len(yeni_sifre) < 6:
                        st.warning("Güvenlik gereği şifre en az 6 karakter olmalıdır.")
                    else:
                        try:
                            supabase.table("kullanicilar").update({"sifre": yeni_sifre}).eq("kullanici_adi", secili_k_adi).execute()
                            st.success(f"✅ '{secili_k_adi}' kullanıcısının şifresi başarıyla güncellendi.")
                        except Exception as e:
                            st.error(f"Şifre güncellenirken hata oluştu: {str(e)}")
    except Exception as e:
         st.error(f"Kullanıcı listesi yüklenemedi: {str(e)}")

# --- MODÜL 7: TEST VERİSİ MODÜLÜ (SADECE ADMİN) ---
elif menu == "🛠️ Test Verisi Modülü":
    st.header("🛠️ Test Verisi Kontrol Paneli")
    st.info("Bu modül, sistemi denemeniz için sahte öğrenciler ve notlar üretmenizi veya bu üretilen sahte verileri tek tuşla kalıcı olarak silmenizi sağlar.")

    col_test1, col_test2 = st.columns(2)

    with col_test1:
        if st.button("➕ Test Verilerini Üret ve Yükle", type="primary", use_container_width=True):
            isim_havuzu = ["Ahmet Yılmaz", "Ayşe Kaya", "Mehmet Demir", "Fatma Çelik", "Ali Can", "Zeynep Şahin", "Mustafa Yıldız", "Elif Özdemir", "Hasan Aydın", "Hatice Arslan"]
            durumlar = ["Yaptı", "Yarım", "Yapmadı", "Gelmedi"]

            try:
                with st.spinner("Sistem tohumlanıyor (Seeding)... Lütfen bekleyin."):
                    ogrenciler_data = []
                    for sinif in sinif_listesi:
                        secilenler = random.sample(isim_havuzu, 5)
                        for isim in secilenler:
                            ogrenciler_data.append({"ad_soyad": f"{isim} (Test)", "sinif": sinif})
                    res_ogr = supabase.table("ogrenciler").insert(ogrenciler_data).execute()

                    notlar_data = []
                    lgs_data = []
                    ogr_sinif_map = {ogr['id']: ogr['sinif'] for ogr in res_ogr.data}

                    for ogr_id, sinif in ogr_sinif_map.items():
                        for brans in branslar:
                            if brans == "Tümü": continue
                            notlar_data.append({
                                "ogrenci_id": ogr_id, "brans": brans,
                                "sinav_1": random.randint(40, 100), "sinav_2": random.randint(40, 100),
                                "perf_1": random.randint(50, 100), "perf_2": random.randint(50, 100),
                                "proje": random.randint(70, 100)
                            })
                        if sinif == "8-A":
                            for i in range(1, 9): 
                                t_d, t_y = random.randint(12, 19), random.randint(0, 5)
                                m_d, m_y = random.randint(6, 15), random.randint(0, 8)
                                f_d, f_y = random.randint(12, 18), random.randint(0, 5)
                                i_d, i_y = random.randint(6, 10), random.randint(0, 3)
                                d_d, d_y = random.randint(7, 10), random.randint(0, 2)
                                ing_d, ing_y = random.randint(6, 10), random.randint(0, 3)
                                
                                t_n = t_d - (t_y / 3)
                                m_n = m_d - (m_y / 3)
                                f_n = f_d - (f_y / 3)
                                i_n = i_d - (i_y / 3)
                                d_n = d_d - (d_y / 3)
                                ing_n = ing_d - (ing_y / 3)
                                
                                puan_hesap = 200 + (t_n * 4.2) + (m_n * 4.2) + (f_n * 4.2) + (i_n * 1.6) + (d_n * 1.6) + (ing_n * 1.6)
                                yuzdelik = round(random.uniform(1.0, 30.0), 2)
                                
                                lgs_data.append({
                                    "ogrenci_id": ogr_id, "deneme_adi": f"Deneme {i}",
                                    "turkce_d": t_d, "turkce_y": t_y, "mat_d": m_d, "mat_y": m_y,
                                    "fen_d": f_d, "fen_y": f_y, "ink_d": i_d, "ink_y": i_y,
                                    "din_d": d_d, "din_y": d_y, "ing_d": ing_d, "ing_y": ing_y,
                                    "lgs_puani": round(float(puan_hesap), 2), "yuzdelik_dilim": yuzdelik
                                })

                    supabase.table("notlar").insert(notlar_data).execute()
                    if lgs_data:
                        supabase.table("lgs_denemeleri").insert(lgs_data).execute()

                    odevler_data = []
                    for sinif in sinif_listesi:
                        for brans in branslar:
                            if brans == "Tümü": continue
                            for i in range(1, 4):
                                odevler_data.append({
                                    "brans": brans, "sinif": sinif, "odev_adi": f"Test Ödevi {i}",
                                    "aciklama": "Otomatik oluşturuldu.", "teslim_tarihi": str(date.today() - timedelta(days=random.randint(1, 15)))
                                })
                    res_odev = supabase.table("odevler").insert(odevler_data).execute()

                    teslimler_data = []
                    for odev in res_odev.data:
                        helpful_students = [k for k, v in ogr_sinif_map.items() if v == odev['sinif']]
                        for ogr_id in helpful_students:
                            teslimler_data.append({
                                "odev_id": odev['id'], "ogrenci_id": ogr_id, "durum": random.choice(durumlar), "ogretmen_notu": "Test notu."
                            })
                    
                    chunk_size = 500
                    for i in range(0, len(teslimler_data), chunk_size):
                        supabase.table("odev_teslimleri").insert(teslimler_data[i:i+chunk_size]).execute()

                st.success("✅ Test verileri başarıyla oluşturuldu ve veritabanına eklendi!")
            except Exception as e:
                st.error(f"Test verisi yüklenirken hata oluştu: {str(e)}")

    with col_test2:
        if st.button("🗑️ Tüm Test Verilerini Temizle", type="secondary", use_container_width=True):
            try:
                with st.spinner("Gerçek verileriniz korunuyor, sadece test verileri temizleniyor..."):
                    res_test_ogr = supabase.table("ogrenciler").select("id").like("ad_soyad", "%(Test)%").execute()
                    if res_test_ogr.data:
                        test_ogr_ids = [row["id"] for row in res_test_ogr.data]
                        supabase.table("notlar").delete().in_("ogrenci_id", test_ogr_ids).execute()
                        supabase.table("odev_teslimleri").delete().in_("ogrenci_id", test_ogr_ids).execute()
                        supabase.table("lgs_denemeleri").delete().in_("ogrenci_id", test_ogr_ids).execute()
                        supabase.table("ogrenciler").delete().in_("id", test_ogr_ids).execute()
                    
                    res_test_odev = supabase.table("odevler").select("id").like("odev_adi", "%Test Ödevi%").execute()
                    if res_test_odev.data:
                        test_odev_ids = [row["id"] for row in res_test_odev.data]
                        supabase.table("odev_teslimleri").delete().in_("odev_id", test_odev_ids).execute()
                        supabase.table("odevler").delete().in_("id", test_odev_ids).execute()
                    
                st.success("✅ Test verilerinin tamamı sistemden kalıcı olarak temizlendi.")
            except Exception as e:
                st.error(f"Test verileri temizlenirken hata oluştu: {str(e)}")
