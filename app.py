import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client, Client
from datetime import date, timedelta
import matplotlib.pyplot as plt
import io
import base64
import random
import os

# --- SAYFA AYARLARI ---
# Streamlit'te bu komut her zaman en üstte olmak zorundadır.
st.set_page_config(
    page_title="Sadiye ve Abdullah Tan Ortaokulu Okul Takip Paneli", 
    page_icon="🎓", 
    layout="wide"
)

# --- BAĞLANTI İLKLENDİRME ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- SABİTLER ---
branslar = ["Matematik", "Türkçe", "Fen Bilimleri", "Sosyal Bilgiler", "İngilizce", "Din Kültürü", "İnkılap Tarihi"]
sinif_listesi = ["5-A", "6-A", "7-A", "8-A"]

# --- OTURUM (LOGIN) YÖNETİMİ ---
if "giris_yapildi" not in st.session_state:
    st.session_state.giris_yapildi = False

# --- GİRİŞ YAPILMADIYSA: KARŞILAMA VE GİRİŞ EKRANI ---
if not st.session_state.giris_yapildi:
    
    # Karşılama Alanı Konteyneri
    with st.container():
        col_logo, col_baslik = st.columns([1, 6])
        
        # 1. Okul Logosunu Gösterme Denemesi
        with col_logo:
            # Kullanıcının dosya adının tam olarak 'logo.png' olduğunu ve app.py ile aynı yerde olduğunu varsayıyoruz
            logo_path = "logo.png" 
            if os.path.exists(logo_path):
                st.image(logo_path, width=120)
            else:
                # Logo yoksa boşluk veya ikon göster, hata verme
                st.write("🏢") 
        
        # 2. Hoşgeldiniz Başlığı ve Tanıtım Metni
        with col_baslik:
            st.title("🎓 Sadiye ve Abdullah Tan Ortaokulu")
            st.subheader("Okul Takip Paneline Hoşgeldiniz")
            st.markdown("""
            Bu panel, okul yönetim sürecini dijitalleştirerek öğretmen ve velilerimiz için veri odaklı 
            bir takip mekanizması sunar. Panel üzerinden aşağıdaki işlemleri gerçekleştirebilirsiniz:
            
            * **Öğrenci Yönetimi:** Öğrenci kayıtlarını sınıf bazlı oluşturabilir ve yönetebilirsiniz.
            * **Akademik Takip:** Not girişlerini yapabilir, branş bazlı ortalamaları izleyebilir ve PDF profil raporları alabilirsiniz.
            * **Ödev Süreçleri:** Ödev tanımlayabilir, teslim durumlarını puanlayabilir ve detaylı istatistikler tutabilirsiniz.
            * **LGS Hazırlık (8. Sınıflar):** Deneme sınavı sonuçlarını girebilir, sınıf sıralamalarını görebilir ve sınavları 'Kafa Kafaya' pedagojik analiz dökümleriyle kıyaslayabilirsiniz.
            """)
    
    st.divider()
    
    # Giriş Formu Alanı
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.write("#### 🔐 Yetkili Girişi")
        st.write("Devam etmek için lütfen kullanıcı bilgilerinizi girin.")
        
        with st.form("giris_formu"):
            k_adi = st.text_input("Kullanıcı Adı")
            sifre = st.text_input("Şifre", type="password")
            giris_butonu = st.form_submit_button("Sisteme Giriş Yap", use_container_width=True)
            
            if giris_butonu:
                if k_adi == "admin" and sifre == "123456":
                    st.session_state.giris_yapildi = True
                    st.rerun()
                else:
                    st.error("❌ Hatalı kullanıcı adı veya şifre.")
    
    # Giriş yapılmadıysa uygulamanın geri kalanını çalıştırma
    st.stop() 

# --- GİRİŞ YAPILDIYSA: ANA UYGULAMA PANELİ ---

# Sidebar Çıkış Butonu
if st.sidebar.button("🚪 Sistemden Güvenli Çıkış", use_container_width=True):
    st.session_state.giris_yapildi = False
    st.rerun()

st.sidebar.title("Sistem Ayarları")
# Branş Seçimi (Tüm filtreleri etkiler)
secilen_brans = st.sidebar.selectbox("Filtre Branş Seçimi", branslar)

st.sidebar.divider()
# Ana Menü
menu = st.sidebar.radio("Modüller", ["Öğrenci Yönetimi", "Öğrenci Profil Paneli", "Not Takip", "Ödev Takip", "LGS Takip", "🛠️ Test Verisi Üret"])


# --- ÖĞRENCİ YÖNETİMİ ---
if menu == "Öğrenci Yönetimi":
    st.header("Öğrenci Yönetimi")
    
    tab_ekle, tab_sil = st.tabs(["➕ Öğrenci Ekle / Listele", "🗑️ Öğrenci Sil"])
    
    with tab_ekle:
        secilen_sinif = st.selectbox("Sınıf Seçin", sinif_listesi, key="ogr_ekle_sinif")
        
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

    with tab_sil:
        st.warning("⚠️ Dikkat: Bir öğrenciyi sildiğinizde, o öğrenciye ait tüm not, ödev ve LGS deneme kayıtları ilişkili tablolardan kalıcı olarak temizlenir.")
        secilen_sinif_sil = st.selectbox("Sınıf Seçin", sinif_listesi, key="ogr_sil_sinif")
        ogrenciler_sil_res = supabase.table("ogrenciler").select("id, ad_soyad").eq("sinif", secilen_sinif_sil).execute()
        
        if not ogrenciler_sil_res.data:
            st.info("Bu sınıfta silinecek kayıtlı öğrenci bulunmuyor.")
        else:
            ogr_secenekleri_sil = {ogr["ad_soyad"]: ogr["id"] for ogr in ogrenciler_sil_res.data}
            silinecek_ogr_adi = st.selectbox("Silinecek Öğrenciyi Seçin", list(ogr_secenekleri_sil.keys()))
            silinecek_ogr_id = ogr_secenekleri_sil[silinecek_ogr_adi]
            
            if st.button(f"🗑️ '{silinecek_ogr_adi}' Adlı Öğrenciyi ve Tüm Verilerini Sil", type="primary"):
                # Zincirleme Veri Temizliği (Cascade)
                supabase.table("notlar").delete().eq("ogrenci_id", silinecek_ogr_id).execute()
                supabase.table("odev_teslimleri").delete().eq("ogrenci_id", silinecek_ogr_id).execute()
                supabase.table("lgs_denemeleri").delete().eq("ogrenci_id", silinecek_ogr_id).execute()
                supabase.table("ogrenciler").delete().eq("id", silinecek_ogr_id).execute()
                
                st.success(f"{silinecek_ogr_adi} ve ilişkili tüm akademik veriler sistemden tamamen silindi.")
                st.rerun()

# --- ÖĞRENCİ PROFİL PANELİ ---
elif menu == "Öğrenci Profil Paneli":
    st.header("Öğrenci Profil Paneli")
    secilen_sinif = st.selectbox("Sınıf Seçin", sinif_listesi, key="profil_sinif")
    is_8th_grade = secilen_sinif.startswith("8")
    
    ogrenciler_res = supabase.table("ogrenciler").select("*").eq("sinif", secilen_sinif).execute()
    
    if ogrenciler_res.data:
        ogrenci_isimleri = [ogr["ad_soyad"] for ogr in ogrenciler_res.data]
        secilen_ogrenci = st.selectbox("Profilini Görüntülemek İstediğiniz Öğrenciyi Seçin", ["Seçiniz..."] + ogrenci_isimleri)
        
        if secilen_ogrenci != "Seçiniz...":
            ogr_data = next(ogr for ogr in ogrenciler_res.data if ogr["ad_soyad"] == secilen_ogrenci)
            ogr_id = ogr_data["id"]
            
            st.markdown(f"### 👤 {secilen_ogrenci} - Akademik Gelişim Özet Raporu")
            
            # --- NOT VERİLERİ ---
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
            
            # --- ÖDEV VERİLERİ ---
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
                        
                        st.write("**Genel Ödev Dağılımı (Filtrelenmiş Veri)**")
                        status_counts_genel = df_filtered_odev["Durum"].value_counts()
                        current_colors_genel = [color_map.get(idx_name, "#2196F3") for idx_name in status_counts_genel.index]
                        
                        fig_genel, ax_genel = plt.subplots(figsize=(3.5, 3.5))
                        wedges, texts, autotexts = ax_genel.pie(
                            status_counts_genel, labels=status_counts_genel.index, autopct='%1.1f%%', 
                            startangle=90, colors=current_colors_genel, wedgeprops=dict(width=0.4, edgecolor='w')
                        )
                        plt.setp(autotexts, size=8, weight="bold")
                        plt.setp(texts, size=9)
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

            # --- SİDEBAR BİLGİLERİ (Öğrenciye Özel) ---
            st.sidebar.markdown("---")
            st.sidebar.subheader("Öğrenci Genel Durumu")
            st.sidebar.metric("Genel Not Ortalaması", f"{genel_ortalama} / 100")
            st.sidebar.metric("Ödev Tamamlama Oranı", f"% {odev_orani}")
            
            # --- PROFİL RAPORU PDF ---
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
                .title {{ text-align: center; font-size: 22px; font-weight: bold; margin-bottom: 5px; }}
                .subtitle {{ text-align: center; font-size: 14px; color: #555; margin-bottom: 25px; }}
                .kv-table {{ width: 100%; border: none; margin-bottom: 20px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 12px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
                th {{ background-color: #f5f5f5; font-weight: bold; }}
                .section-title {{ font-size: 15px; font-weight: bold; color: #fff; background-color: #2196F3; padding: 6px 10px; margin-top: 25px; border-radius: 3px; }}
                .summary-box {{ background-color: #f9fbfd; border-left: 4px solid #4CAF50; padding: 12px; margin-top: 15px; font-size: 13px; text-align: center; }}
            </style>
            </head>
            <body onload="window.print()">
                <div class="title">ÖĞRENCİ AKADEMİK PROFİL RAPORU</div>
                <div class="subtitle">Not ve Ödev Gelişim Dökümü</div>
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

# --- NOT TAKİP ---
elif menu == "Not Takip":
    st.header(f"Not Takip Paneli - {secilen_brans}")
    # ... (Not Takip Modülü kodları aynı kalır, buraya entegre edilir)
    
# --- ÖDEV TAKİP ---
elif menu == "Ödev Takip":
    st.header(f"Ödev Takip Modülü - {secilen_brans}")
    # ... (Ödev Takip Modülü kodları aynı kalır, buraya entegre edilir)

# --- LGS TAKİP MODÜLÜ ---
elif menu == "LGS Takip":
    st.header("LGS Hazırlık ve Takip Modülü")
    # ... (LGS Takip Modülü kodları aynı kalır, buraya entegre edilir)

# --- TEST VERİSİ ÜRETİMİ ---
elif menu == "🛠️ Test Verisi Üret":
    st.header("Sisteme Rastgele Test Verisi Ekleme")
    # ... (Test Verisi Üretimi kodları aynı kalır, buraya entegre edilir)
