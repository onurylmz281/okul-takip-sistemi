import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# SUPABASE BAĞLANTI BİLGİLERİ
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

st.set_page_config(page_title="Okul Takip Sistemi", layout="wide")

st.title("🏫 Okul Takip Sistemi")
st.write("Not, Ödev ve Veli Bilgilendirme Portalı")
st.markdown("---")

if "rol" not in st.session_state:
    st.session_state["rol"] = "ziyaretci"
if "brans" not in st.session_state:
    st.session_state["brans"] = None

# ---------------------------------------------------------------
# GİRİŞ EKRANLARI
# ---------------------------------------------------------------
if st.session_state["rol"] == "ziyaretci":
    giris_turu = st.radio("Sisteme Giriş Rolünüzü Seçin:", ["Öğretmen Girişi", "Veli Girişi"], horizontal=True)

    if giris_turu == "Öğretmen Girişi":
        st.subheader("👨‍🏫 Öğretmen Yönetim Paneli")
        secilen_brans = st.selectbox("Branşınız:", ["Matematik", "Türkçe", "Fen Bilimleri", "Sosyal Bilgiler", "İngilizce"])
        ogretmen_sifre = st.text_input("Öğretmen Giriş Şifresi:", type="password")
        
        if st.button("Giriş Yap", key="ogretmen_btn"):
            if ogretmen_sifre == "okultakip2026":
                st.session_state["rol"] = "ogretmen"
                st.session_state["brans"] = secilen_brans
                st.rerun()
            else:
                st.error("Hatalı şifre.")

    else:
        st.subheader("👨‍👩‍👦 Veli Bilgilendirme Sistemi")
        st.info("Veli giriş modülü, öğretmen paneli inşası tamamlandıktan sonra aktif edilecektir.")

# ---------------------------------------------------------------
# ÖĞRETMEN YÖNETİM PANELİ
# ---------------------------------------------------------------
elif st.session_state["rol"] == "ogretmen":
    st.subheader(f"👨‍🏫 Öğretmen Yönetim Paneli | Yetki: {st.session_state['brans']} Öğretmeni")
    
    if st.button("Çıkış Yap"):
        st.session_state["rol"] = "ziyaretci"
        st.session_state["brans"] = None
        st.rerun()
        
    st.markdown("---")
    
    # Menüye "Öğrenci Profili İncele" seçeneği eklendi
    islem = st.sidebar.selectbox("İşlem Menüsü:", ["Öğrenci Listesi & Ekleme", "Not Girişi Yap", "Ödev ve Görüş Ekle", "Öğrenci Profili İncele"])
    
    if islem == "Öğrenci Listesi & Ekleme":
        st.markdown("### ➕ Yeni Öğrenci Kaydı")
        yeni_ad = st.text_input("Adı Soyadı:")
        yeni_sinif = st.selectbox("Sınıfı:", ["5", "6", "7", "8"])
        yeni_no = st.text_input("Okul Numarası:")
        yeni_sifre = st.text_input("Veli Şifresi:", value="1234")
        
        if st.button("Kaydet"):
            if yeni_ad and yeni_no:
                ogrenci_verisi = {"ad_soyad": yeni_ad, "sinif": yeni_sinif, "okul_no": yeni_no, "sifre": yeni_sifre}
                url = f"{SUPABASE_URL}/rest/v1/ogrenciler"
                response = requests.post(url, headers=headers, json=ogrenci_verisi)
                if response.status_code in [200, 201]:
                    st.success("Kayıt başarılı.")
                    st.rerun()
                else:
                    st.error(f"Hata: {response.status_code}")
        
        st.markdown("---")
        st.markdown("### 📋 Öğrenci Listesi")
        url_liste = f"{SUPABASE_URL}/rest/v1/ogrenciler?select=*"
        res = requests.get(url_liste, headers=headers)
        
        if res.status_code == 200:
            if res.json():
                df = pd.DataFrame(res.json())
                st.dataframe(df[["okul_no", "ad_soyad", "sinif"]], use_container_width=True)
            else:
                st.info("Veri tabanında kayıtlı hiçbir öğrenci bulunmuyor.")
        else:
            st.error(f"Veri çekilemedi. Hata Kodu: {res.status_code}")

    elif islem == "Not Girişi Yap":
        st.markdown(f"### 📝 Not Giriş Ekranı ({st.session_state['brans']})")
        url_liste = f"{SUPABASE_URL}/rest/v1/ogrenciler?select=*"
        res = requests.get(url_liste, headers=headers)
        
        if res.status_code == 200 and res.json():
            ogrenciler = res.json()
            ogrenci_secenekleri = {o["id"]: f"{o['okul_no']} - {o['ad_soyad']}" for o in ogrenciler}
            secilen_id = st.selectbox("Öğrenci:", options=list(ogrenci_secenekleri.keys()), format_func=lambda x: ogrenci_secenekleri[x])
            
            ders = st.session_state["brans"]
            st.info(f"Ders kilitli: **{ders}**")
            
            y1 = st.number_input("1. Yazılı:", min_value=0, max_value=100, step=1, value=0)
            y2 = st.number_input("2. Yazılı:", min_value=0, max_value=100, step=1, value=0)
            p1 = st.number_input("1. Performans:", min_value=0, max_value=100, step=1, value=0)
            
            if st.button("Notları Kaydet"):
                not_verisi = {"ogrenci_id": secilen_id, "ders_adi": ders, "yazili_1": y1, "yazili_2": y2, "performans_1": p1}
                url_not = f"{SUPABASE_URL}/rest/v1/notlar"
                not_res = requests.post(url_not, headers=headers, json=not_verisi)
                if not_res.status_code in [200, 201]:
                    st.success(f"{ders} notları kaydedildi.")
                else:
                    st.error(f"Hata detayı: {not_res.text}")
        else:
            st.warning("Öğrenci kaydı mevcut değil.")
            
    elif islem == "Ödev ve Görüş Ekle":
        st.markdown(f"### 📚 Ödev ve Öğretmen Görüşü Ekranı ({st.session_state['brans']})")
        url_liste = f"{SUPABASE_URL}/rest/v1/ogrenciler?select=*"
        res = requests.get(url_liste, headers=headers)
        
        if res.status_code == 200 and res.json():
            ogrenciler = res.json()
            ogrenci_secenekleri = {o["id"]: f"{o['okul_no']} - {o['ad_soyad']}" for o in ogrenciler}
            secilen_id = st.selectbox("Öğrenci Seçimi:", options=list(ogrenci_secenekleri.keys()), format_func=lambda x: ogrenci_secenekleri[x])
            
            ders_adi = st.session_state["brans"]
            st.info(f"Ders kilitli: **{ders_adi}**")
            
            odev_basligi = st.text_input("Ödev Başlığı:")
            odev_durumu = st.selectbox("Ödev Durumu:", ["Tamamlandı", "Eksik", "Yapılmadı"])
            ogretmen_notu = st.text_area("Öğretmen Notu:")
            genel_degerlendirme = st.text_area("Genel Değerlendirme:")
            
            if st.button("Ödev ve Görüşü Kaydet"):
                if odev_basligi:
                    odev_verisi = {
                        "ogrenci_id": secilen_id,
                        "ders_adi": ders_adi,
                        "odev_basligi": odev_basligi,
                        "odev_durumu": odev_durumu,
                        "ogretmen_notu": ogretmen_notu,
                        "genel_degerlendirme": genel_degerlendirme,
                        "tarih": datetime.now().isoformat()
                    }
                    
                    url_odev = f"{SUPABASE_URL}/rest/v1/odevler_ve_gorusler"
                    odev_res = requests.post(url_odev, headers=headers, json=odev_verisi)
                    if odev_res.status_code in [200, 201]:
                        st.success("Veriler kaydedildi.")
                    else:
                        st.error(f"Hata detayı: {odev_res.text}")
                else:
                    st.warning("Ödev Başlığı zorunludur.")
        else:
            st.warning("Öğrenci listesi alınamadı.")

    # 4. MODÜL: ÖĞRENCİ PROFİLİ İNCELEME
    elif islem == "Öğrenci Profili İncele":
        st.markdown("### 📈 Öğrenci Başarı ve Profil Panosu")
        url_liste = f"{SUPABASE_URL}/rest/v1/ogrenciler?select=*"
        res = requests.get(url_liste, headers=headers)
        
        if res.status_code == 200 and res.json():
            ogrenciler = res.json()
            ogrenci_secenekleri = {o["id"]: f"{o['okul_no']} - {o['ad_soyad']} (Sınıf: {o['sinif']})" for o in ogrenciler}
            secilen_id = st.selectbox("İncelenecek Öğrenciyi Seçin:", options=list(ogrenci_secenekleri.keys()), format_func=lambda x: ogrenci_secenekleri[x])
            
            st.markdown("---")
            
            # Sütun yapısı ile verileri yan yana diziyoruz
            col1, col2 = st.columns(2)
            
            # 1. NOT VERİLERİNİ ÇEKME VE İŞLEME
            url_notlar = f"{SUPABASE_URL}/rest/v1/notlar?ogrenci_id=eq.{secilen_id}&select=*"
            res_notlar = requests.get(url_notlar, headers=headers)
            
            with col1:
                st.markdown("#### 📊 Akademik Durum")
                if res_notlar.status_code == 200 and res_notlar.json():
                    df_not = pd.DataFrame(res_notlar.json())
                    # Ders bazlı ortalama hesaplama
                    df_not["Ortalama"] = df_not[["yazili_1", "yazili_2", "performans_1"]].mean(axis=1).round(2)
                    
                    st.dataframe(df_not[["ders_adi", "yazili_1", "yazili_2", "performans_1", "Ortalama"]], use_container_width=True)
                    
                    # Genel ortalama hesaplama ve metrik gösterimi
                    genel_ort = df_not["Ortalama"].mean()
                    st.metric(label="Genel Akademik Ortalama", value=f"{genel_ort:.2f}")
                    
                    # Ders ortalamalarının çubuk grafiği
                    st.bar_chart(df_not.set_index("ders_adi")["Ortalama"])
                else:
                    st.info("Kayıtlı not verisi bulunamadı.")
                    
            # 2. ÖDEV VE GÖRÜŞ VERİLERİNİ ÇEKME VE İŞLEME
            url_odevler = f"{SUPABASE_URL}/rest/v1/odevler_ve_gorusler?ogrenci_id=eq.{secilen_id}&select=*"
            res_odevler = requests.get(url_odevler, headers=headers)
            
            with col2:
                st.markdown("#### 📝 Sorumluluk ve Ödev İstatistiği")
                if res_odevler.status_code == 200 and res_odevler.json():
                    df_odev = pd.DataFrame(res_odevler.json())
                    
                    # Ödev durum frekanslarını hesaplama
                    durum_sayilari = df_odev["odev_durumu"].value_counts()
                    st.dataframe(durum_sayilari, use_container_width=True)
                    st.bar_chart(durum_sayilari)
                else:
                    st.info("Kayıtlı ödev istatistiği bulunamadı.")

            st.markdown("---")
            st.markdown("#### 🗣️ Kronolojik Öğretmen Görüşleri ve Değerlendirmeler")
            
            if res_odevler.status_code == 200 and res_odevler.json():
                # Tarihe göre en yeniden eskiye sıralama
                df_odev = df_odev.sort_values(by="tarih", ascending=False)
                
                for index, row in df_odev.iterrows():
                    tarih_format = pd.to_datetime(row['tarih']).strftime('%d.%m.%Y')
                    durum_ikonu = "✅" if row['odev_durumu'] == "Tamamlandı" else "⚠️" if row['odev_durumu'] == "Eksik" else "❌"
                    
                    # Verilerin kutular (expander) içinde akış formatında gösterimi
                    with st.expander(f"{row['ders_adi']} | {tarih_format} | Ödev: {row['odev_basligi']} {durum_ikonu}"):
                        st.write(f"**Durum:** {row['odev_durumu']}")
                        st.write(f"**Öğretmen Notu:** {row['ogretmen_notu']}")
                        st.write(f"**Genel Değerlendirme:** {row['genel_degerlendirme']}")
            else:
                st.info("Bu öğrenci için henüz bir öğretmen değerlendirmesi girilmemiştir.")
        else:
            st.warning("Veri çekilemedi.")
