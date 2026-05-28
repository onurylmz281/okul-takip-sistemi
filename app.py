import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date, timedelta
import matplotlib.pyplot as plt
import io
import base64

# Sayfa Ayarları (Streamlit'te her zaman en üstte olmalıdır)
st.set_page_config(page_title="Okul Takip Sistemi", layout="wide")

# --- OTURUM (LOGIN) YÖNETİMİ ---
if "giris_yapildi" not in st.session_state:
    st.session_state.giris_yapildi = False

if not st.session_state.giris_yapildi:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.title("🔐 Sisteme Giriş")
        st.write("Lütfen yetkili kullanıcı bilgilerinizi girin.")
        
        with st.form("giris_formu"):
            k_adi = st.text_input("Kullanıcı Adı")
            sifre = st.text_input("Şifre", type="password")
            giris_butonu = st.form_submit_button("Giriş Yap", use_container_width=True)
            
            if giris_butonu:
                if k_adi == "admin" and sifre == "123456":
                    st.session_state.giris_yapildi = True
                    st.rerun()
                else:
                    st.error("Hatalı kullanıcı adı veya şifre.")
    st.stop() 

# --- GİRİŞ BAŞARILIYSA AŞAĞIDAKİ KODLAR ÇALIŞIR ---

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
    st.session_state.giris_yapildi = False
    st.rerun()

st.sidebar.title("Sistem Ayarları")
branslar = ["Matematik", "Türkçe", "Fen Bilimleri", "Sosyal Bilgiler", "İngilizce", "Din Kültürü", "İnkılap Tarihi"]
secilen_brans = st.sidebar.selectbox("Branş Seçimi", branslar)

st.sidebar.divider()
menu = st.sidebar.radio("Modüller", ["Öğrenci Yönetimi", "Öğrenci Profili", "Not Takip", "Ödev Takip", "LGS Takip"])

sinif_listesi = ["5-A", "6-A", "7-A", "8-A"]

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
            
            # --- NOT VERİLERİ VE TABLOSU ---
            notlar_res = supabase.table("notlar").select("*").eq("ogrenci_id", ogr_id).execute()
            genel_ortalama = 0
            df_html_notlar = ""
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
                
                # Genel Ortalama Hesaplama
                gecerli_ortalamalar = df_gosterim["Ortalama"].dropna().tolist()
                if gecerli_ortalamalar:
                    genel_ortalama = round(sum(gecerli_ortalamalar) / len(gecerli_ortalamalar), 2)
                
                st.subheader("📊 Branş Bazlı Not Durumu")
                st.dataframe(df_gosterim, hide_index=True, use_container_width=True)
                df_html_notlar = df_gosterim.to_html(border=1, index=False, justify='center')
            else:
                st.info("Bu öğrenciye ait herhangi bir not verisi bulunmamaktadır.")
            
            # --- ÖDEV VERİLERİ VE GRAFİĞİ ---
            odevler_res = supabase.table("odev_teslimleri").select("*").eq("ogrenci_id", ogr_id).execute()
            odev_orani = 0
            odev_pie_base64 = ""
            df_html_odevler = ""
            
            if odevler_res.data:
                df_odevler = pd.DataFrame(odevler_res.data)
                durum_dagilimi = df_odevler["durum"].value_counts()
                toplam_odev = len(df_odevler)
                yapti_sayisi = sum(1 for o in odevler_res.data if o["durum"] == "Yaptı")
                odev_orani = round((yapti_sayisi / toplam_odev) * 100, 1)
                
                st.divider()
                st.subheader("📚 Ödev İstatistikleri ve Detayları")
                col_grafik, col_tablo = st.columns([1, 2])
                
                with col_grafik:
                    st.write("**Genel Dağılım**")
                    st.bar_chart(durum_dagilimi)
                    
                    # PDF İçin Arka Planda Pasta Grafik Üretimi
                    fig, ax = plt.subplots(figsize=(3, 3))
                    durum_dagilimi.plot(kind='pie', autopct='%1.1f%%', ax=ax, startangle=90, cmap="Pastel1")
                    ax.set_ylabel('')
                    buf = io.BytesIO()
                    plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
                    buf.seek(0)
                    odev_pie_base64 = base64.b64encode(buf.read()).decode('utf-8')
                    plt.close(fig)
                
                with col_tablo:
                    st.write("**Ödev Geçmişi ve Öğretmen Notları**")
                    odev_detay_res = supabase.table("odev_teslimleri").select("durum, ogretmen_notu, odevler(odev_adi, brans)").eq("ogrenci_id", ogr_id).execute()
                    if odev_detay_res.data:
                        detay_liste = []
                        for d in odev_detay_res.data:
                            odev_bilgisi = d.get("odevler") or {}
                            detay_liste.append({
                                "Branş": odev_bilgisi.get("brans", ""),
                                "Ödev Adı": odev_bilgisi.get("odev_adi", ""),
                                "Durum": d.get("durum", ""),
                                "Açıklama/Not": d.get("ogretmen_notu", "")
                            })
                        df_detay_odev = pd.DataFrame(detay_liste)
                        st.dataframe(df_detay_odev, hide_index=True, use_container_width=True)
                        df_html_odevler = df_detay_odev.to_html(border=1, index=False, justify='center')
            else:
                st.info("Bu öğrenciye ait ödev değerlendirmesi bulunmamaktadır.")

            # --- LGS VERİLERİ VE GELİŞİM GRAFİĞİ ---
            son_deneme_neti = 0
            lgs_line_base64 = ""
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
                    
                    st.divider()
                    st.subheader("🎯 LGS Deneme Gelişimi")
                    
                    grafik_verisi = []
                    for d in lgs_res.data:
                        toplam = (d["turkce_d"] - d["turkce_y"]/3) + (d["mat_d"] - d["mat_y"]/3) + (d["fen_d"] - d["fen_y"]/3) + (d["ink_d"] - d["ink_y"]/3) + (d["din_d"] - d["din_y"]/3) + (d["ing_d"] - d["ing_y"]/3)
                        grafik_verisi.append({"Deneme": d["deneme_adi"], "Toplam Net": toplam})
                        
                    df_lgs_grafik = pd.DataFrame(grafik_verisi)
                    st.line_chart(df_lgs_grafik.set_index("Deneme"))
                    
                    # PDF İçin Çizgi Grafik Üretimi
                    fig2, ax2 = plt.subplots(figsize=(5, 2.5))
                    ax2.plot(df_lgs_grafik["Deneme"], df_lgs_grafik["Toplam Net"], marker='o', color='#2196F3', linewidth=2)
                    ax2.set_ylabel('Toplam Net')
                    ax2.grid(True, linestyle='--', alpha=0.5)
                    plt.xticks(rotation=15)
                    buf2 = io.BytesIO()
                    plt.savefig(buf2, format='png', bbox_inches='tight', dpi=150)
                    buf2.seek(0)
                    lgs_line_base64 = base64.b64encode(buf2.read()).decode('utf-8')
                    plt.close(fig2)

            # --- ÜST METRİK KARTLARINI EKRANDA GÖSTERME ---
            # Streamlit render akışı gereği kartlar en üstte yer alsın diye container kullanılabilir, 
            # ancak kod sadeliği için veriler hesaplandıktan sonra ara yüze basılmıştır.
            st.sidebar.markdown("---")
            st.sidebar.subheader("Öğrenci Özet Verileri")
            st.sidebar.metric("Genel Not Ortalanması", f"{genel_ortalama} / 100")
            st.sidebar.metric("Ödev Tamamlama Oranı", f"% {odev_orani}")
            if is_8th_grade:
                st.sidebar.metric("Son Deneme Neti", f"{son_deneme_neti} Net")

            # --- PDF / HTML RAPORU OLUŞTURMA VE DIŞA AKTARMA ---
            st.divider()
            st.write("#### 💾 Raporu İndir")
            
            # HTML Rapor Şablonu Tasarımı
            html_icerik = f"""
            <html>
            <head>
            <meta charset="utf-8">
            <title>{secilen_ogrenci} - Gelişim Raporu</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 30px; color: #333; }}
                .header-table {{ width: 100%; border: none; margin-bottom: 20px; }}
                .card-container {{ display: flex; justify-content: space-between; margin-bottom: 25px; gap: 15px; }}
                .card {{ flex: 1; border: 1px solid #ddd; border-radius: 6px; padding: 15px; text-align: center; background-color: #fafafa; }}
                .card h3 {{ margin: 0 0 10px 0; font-size: 14px; color: #666; }}
                .card p {{ margin: 0; font-size: 20px; font-weight: bold; color: #111; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }}
                th, td {{ border: 1px solid #ddd; padding: 10px; text-align: center; }}
                th {{ background-color: #f4f6f8; font-weight: bold; }}
                .section-title {{ margin-top: 30px; border-bottom: 2px solid #2196F3; padding-bottom: 5px; color: #111; }}
                .graph-container {{ text-align: center; margin-top: 20
