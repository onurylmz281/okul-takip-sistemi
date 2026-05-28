import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client, Client
from datetime import date, timedelta
import matplotlib.pyplot as plt
import io
import base64
import random

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
menu = st.sidebar.radio("Modüller", ["Öğrenci Yönetimi", "Öğrenci Profil Paneli", "Not Takip", "Ödev Takip", "LGS Takip", "🛠️ Test Verisi Üret"])

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
                
                gecerli_ortalamalar = df_gosterim["Ortalama"].dropna().tolist()
                if gecerli_ortalamalar:
                    genel_ortalama = round(sum(gecerli_ortalamalar) / len(gecerli_ortalamalar), 2)
                
                st.subheader("📊 Branş Bazlı Not Durumu")
                st.dataframe(df_gosterim, hide_index=True, use_container_width=True)
                df_html_notlar = df_gosterim.to_html(border=1, index=False, justify='center')
            else:
                st.info("Bu öğrenciye ait herhangi bir not verisi bulunmamaktadır.")
            
            # --- ÖDEV VERİLERİ VE DİNAMİK FİLTRELEME ---
            odevler_res = supabase.table("odev_teslimleri").select("*").eq("ogrenci_id", ogr_id).execute()
            odev_orani = 0
            genel_graph_base64 = ""
            pdf_brans_grafikleri_html = ""
            df_html_odevler = ""
            
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
                            status_counts_genel, 
                            labels=status_counts_genel.index, 
                            autopct='%1.1f%%', 
                            startangle=90, 
                            colors=current_colors_genel,
                            wedgeprops=dict(width=0.4, edgecolor='w')
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

            son_deneme_neti = 0
            st.sidebar.markdown("---")
            st.sidebar.subheader("Öğrenci Genel Durumu")
            st.sidebar.metric("Genel Not Ortalaması", f"{genel_ortalama} / 100")
            st.sidebar.metric("Ödev Tamamlama Oranı", f"% {odev_orani}")

elif menu == "Not Takip":
    st.header(f"Not Takip Paneli - {secilen_brans}")
    secilen_sinif = st.selectbox("Sınıf Seçin", sinif_listesi, key="not_sinif")
    
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
        
        st.write("Aşağıdaki tablo üzerinden notları değiştirebilir veya silebilirsiniz. Yapılan değişiklikler **Notları Veri Tabanına Kaydet** butonuna basıldığında geçmiş verilerin üzerine yazılır (Update).")
        
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
        
        if st.button("Notları Veri Tabanına Kaydet (Ekle/Güncelle)", type="primary"):
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
            
            st.success("Not işlemleri (Kayıt/Güncelleme/Silme) başarıyla tamamlandı.")
            st.rerun()

elif menu == "Ödev Takip":
    st.header(f"Ödev Takip Modülü - {secilen_brans}")
    tab1, tab2, tab3 = st.tabs(["📝 Yeni Ödev Tanımla", "✅ Ödev Düzenle / Değerlendir", "📊 Ödev Raporları"])
    
    with tab1:
        secilen_sinif_odev = st.selectbox("Sınıf Seçin", sinif_listesi, key="odev_sinif_tanimla")
        with st.form("odev_tanimla_form", clear_on_submit=True):
            odev_adi = st.text_input("Ödev Adı / Konusu (Örn: Çarpanlar ve Katlar Test 1)")
            odev_aciklama = st.text_area("Ödev Açıklaması (İsteğe Bağlı)")
            teslim_tarihi = st.date_input("Teslim Tarihi")
            
            submit_odev = st.form_submit_button("Ödevi Sisteme Kaydet")
            
            if submit_odev and odev_adi:
                supabase.table("odevler").insert({
                    "brans": secilen_brans,
                    "sinif": secilen_sinif_odev,
                    "odev_adi": odev_adi,
                    "aciklama": odev_aciklama,
                    "teslim_tarihi": str(teslim_tarihi)
                }).execute()
                st.success("Ödev başarıyla tanımlandı.")
                st.rerun()

    with tab2:
        secilen_sinif_kontrol = st.selectbox("Sınıf Seçin", sinif_listesi, key="odev_sinif_kontrol")
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
                    supabase.table("odev_teslimleri").delete().eq("odev_id", secilen_odev_id).execute()
                    supabase.table("odevler").delete().eq("id", secilen_odev_id).execute()
                    st.success("Ödev ve tüm değerlendirmeler veri tabanından silindi.")
                    st.rerun()
            
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
                st.write("Aşağıdaki tablodan eski değerlendirmeleri doğrudan güncelleyebilirsiniz.")
                
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
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                if st.button("Değişiklikleri Veri Tabanına Kaydet", type="primary"):
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
                    
                    st.success("Ödev güncellemeleri başarıyla kaydedildi.")
                    st.rerun()

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
            secilen_rapor_branslar = st.multiselect("Görüntülenecek Branşlar", branslar, default=branslar, key="odev_brans_filtre")

        if len(secilen_tarih) != 2:
            st.warning("Lütfen tabloda verileri görmek için bir başlangıç ve bitiş tarihi aralığı seçin.")
        elif not secilen_rapor_branslar:
            st.warning("Lütfen tabloda verileri görmek için en az bir branş seçin.")
        else:
            baslangic_tarihi, bitis_tarihi = secilen_tarih
            
            ogr_res = supabase.table("ogrenciler").select("id, ad_soyad").eq("sinif", secilen_sinif_rapor).execute()
            odv_res = supabase.table("odevler").select("id, odev_adi, brans").eq("sinif", secilen_sinif_rapor).in_("brans", secilen_rapor_branslar).gte("teslim_tarihi", str(baslangic_tarihi)).lte("teslim_tarihi", str(bitis_tarihi)).execute()
            
            if not ogr_res.data:
                st.warning("Bu sınıfta kayıtlı öğrenci bulunmuyor.")
            elif not odv_res.data:
                st.info("Belirtilen tarih aralığı ve branşlarda bu sınıfa ait ödev verisi bulunmamaktadır.")
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
                html_icerik_rapor = f"<html><head><meta charset='utf-8'><title>{secilen_sinif_rapor} Ödev Raporu</title></head><body onload='window.print()'><h2>{secilen_sinif_rapor} Sınıfı Ödev Takip Çizelgesi</h2>{html_tablo}</body></html>"
                
                with col_btn1:
                    st.download_button(label="📄 PDF Olarak Kaydet", data=html_icerik_rapor, file_name=f"{secilen_sinif_rapor}_Odev_Raporu.html", mime="text/html")
                with col_btn2:
                    st.download_button(label="📊 Excel İçin İndir", data=df_matris.to_csv(index=True, sep=";", encoding="utf-8-sig").encode("utf-8-sig"), file_name=f"{secilen_sinif_rapor}_Odev_Raporu.csv", mime="text/csv")

elif menu == "LGS Takip":
    st.header("LGS Takip Modülü")
    
    sinif_8_listesi = [s for s in sinif_listesi if s.startswith("8")]
    
    if not sinif_8_listesi:
        st.info("Sistemde kayıtlı 8. sınıf bulunmamaktadır.")
    else:
        secilen_sinif_lgs = st.selectbox("Sınıf Seçin", sinif_8_listesi, key="lgs_sinif_secim")
        ogrenciler_res = supabase.table("ogrenciler").select("id, ad_soyad").eq("sinif", secilen_sinif_lgs).execute()
        
        if not ogrenciler_res.data:
            st.warning("Bu sınıfta öğrenci kaydı bulunmuyor.")
        else:
            ogrenciler = ogrenciler_res.data
            ogr_secenekleri = {ogr["ad_soyad"]: ogr["id"] for ogr in ogrenciler}
            ogr_idler = [ogr["id"] for ogr in ogrenciler]
            
            tab_lgs1, tab_lgs2, tab_lgs3 = st.tabs(["📝 Deneme Notu İşlem Paneli", "📊 Sınıf Genel Sıralaması", "🎯 Öğrenci Özel Analizi"])
            
            # --- TAB 1: DENEME GİRİŞ / DÜZENLEME ---
            with tab_lgs1:
                islem_tipi = st.radio("İşlem Tipi Seçin:", ["➕ Yeni Deneme Girişi Yap", "✏️ Mevcut Denemeyi Düzenle / Sil"], horizontal=True)
                
                if islem_tipi == "➕ Yeni Deneme Girişi Yap":
                    deneme_adi = st.text_input("Yeni Deneme Sınavı Adı (Örn: Özdebir-1)")
                    
                    lgs_tablo_verisi = []
                    for ogr in ogrenciler:
                        lgs_tablo_verisi.append({
                            "Öğrenci ID": ogr["id"], "Kayıt ID": None, "Öğrenci Adı": ogr["ad_soyad"],
                            "Türkçe D": 0, "Türkçe Y": 0, "Matematik D": 0, "Matematik Y": 0,
                            "Fen D": 0, "Fen Y": 0, "İnkılap D": 0, "İnkılap Y": 0,
                            "Din D": 0, "Din Y": 0, "İngilizce D": 0, "İngilizce Y": 0
                        })
                    df_lgs_toplu = pd.DataFrame(lgs_tablo_verisi)
                    st.write("Aşağıdaki tablo üzerinden klavyenizle hızlıca geçiş yaparak verileri işleyebilirsiniz.")
                
                else:
                    mevcut_denemeler_res = supabase.table("lgs_denemeleri").select("deneme_adi").in_("ogrenci_id", ogr_idler).execute()
                    if mevcut_denemeler_res.data:
                        benzersiz_denemeler = list(set([d["deneme_adi"] for d in mevcut_denemeler_res.data]))
                        deneme_adi = st.selectbox("Düzenlenecek Denemeyi Seçin", benzersiz_denemeler)
                        
                        col_del1, col_del2 = st.columns([4, 1])
                        with col_del2:
                            if st.button("🗑️ Bu Sınavı Tamamen Sil"):
                                supabase.table("lgs_denemeleri").delete().eq("deneme_adi", deneme_adi).in_("ogrenci_id", ogr_idler).execute()
                                st.success("Sınav verileri başarıyla silindi.")
                                st.rerun()
                        
                        # Mevcut deneme verilerini çek
                        deneme_verileri_res = supabase.table("lgs_denemeleri").select("*").eq("deneme_adi", deneme_adi).in_("ogrenci_id", ogr_idler).execute()
                        mevcut_veriler = {d["ogrenci_id"]: d for d in deneme_verileri_res.data}
                        
                        lgs_tablo_verisi = []
                        for ogr in ogrenciler:
                            d_veri = mevcut_veriler.get(ogr["id"], {})
                            lgs_tablo_verisi.append({
                                "Öğrenci ID": ogr["id"], "Kayıt ID": d_veri.get("id", None), "Öğrenci Adı": ogr["ad_soyad"],
                                "Türkçe D": d_veri.get("turkce_d", 0), "Türkçe Y": d_veri.get("turkce_y", 0),
                                "Matematik D": d_veri.get("mat_d", 0), "Matematik Y": d_veri.get("mat_y", 0),
                                "Fen D": d_veri.get("fen_d", 0), "Fen Y": d_veri.get("fen_y", 0),
                                "İnkılap D": d_veri.get("ink_d", 0), "İnkılap Y": d_veri.get("ink_y", 0),
                                "Din D": d_veri.get("din_d", 0), "Din Y": d_veri.get("din_y", 0),
                                "İngilizce D": d_veri.get("ing_d", 0), "İngilizce Y": d_veri.get("ing_y", 0)
                            })
                        df_lgs_toplu = pd.DataFrame(lgs_tablo_verisi)
                        st.write("Verileri doğrudan tablo üzerinden düzenleyebilirsiniz.")
                    else:
                        st.info("Bu sınıfa ait kaydedilmiş deneme verisi bulunmuyor.")
                        df_lgs_toplu = pd.DataFrame()
                        deneme_adi = ""

                if not df_lgs_toplu.empty:
                    duzenlenmis_lgs_df = st.data_editor(
                        df_lgs_toplu,
                        column_config={
                            "Öğrenci ID": None, "Kayıt ID": None,
                            "Öğrenci Adı": st.column_config.TextColumn(disabled=True),
                            "Türkçe D": st.column_config.NumberColumn(min_value=0, max_value=20, step=1),
                            "Türkçe Y": st.column_config.NumberColumn(min_value=0, max_value=20, step=1),
                            "Matematik D": st.column_config.NumberColumn(min_value=0, max_value=20, step=1),
                            "Matematik Y": st.column_config.NumberColumn(min_value=0, max_value=20, step=1),
                            "Fen D": st.column_config.NumberColumn(min_value=0, max_value=20, step=1),
                            "Fen Y": st.column_config.NumberColumn(min_value=0, max_value=20, step=1),
                            "İnkılap D": st.column_config.NumberColumn(min_value=0, max_value=10, step=1),
                            "İnkılap Y": st.column_config.NumberColumn(min_value=0, max_value=10, step=1),
                            "Din D": st.column_config.NumberColumn(min_value=0, max_value=10, step=1),
                            "Din Y": st.column_config.NumberColumn(min_value=0, max_value=10, step=1),
                            "İngilizce D": st.column_config.NumberColumn(min_value=0, max_value=10, step=1),
                            "İngilizce Y": st.column_config.NumberColumn(min_value=0, max_value=10, step=1),
                        }, hide_index=True, use_container_width=True
                    )
                    
                    if st.button("Tüm İşlemleri Veri Tabanına Kaydet", type="primary", use_container_width=True):
                        if not deneme_adi:
                            st.error("Deneme adı boş bırakılamaz!")
                        else:
                            hata_var_mi = False
                            for index, row in duzenlenmis_lgs_df.iterrows():
                                if (row["Türkçe D"]+row["Türkçe Y"]>20) or (row["Matematik D"]+row["Matematik Y"]>20) or (row["Fen D"]+row["Fen Y"]>20) or (row["İnkılap D"]+row["İnkılap Y"]>10) or (row["Din D"]+row["Din Y"]>10) or (row["İngilizce D"]+row["İngilizce Y"]>10):
                                    st.error(f"❌ {row['Öğrenci Adı']} için soru limiti aşıldı! İşlem durduruldu.")
                                    hata_var_mi = True
                                    break
                            
                            if not hata_var_mi:
                                for index, row in duzenlenmis_lgs_df.iterrows():
                                    kayit_paketi = {
                                        "ogrenci_id": int(row["Öğrenci ID"]), "deneme_adi": deneme_adi,
                                        "turkce_d": int(row["Türkçe D"]), "turkce_y": int(row["Türkçe Y"]),
                                        "mat_d": int(row["Matematik D"]), "mat_y": int(row["Matematik Y"]),
                                        "fen_d": int(row["Fen D"]), "fen_y": int(row["Fen Y"]),
                                        "ink_d": int(row["İnkılap D"]), "ink_y": int(row["İnkılap Y"]),
                                        "din_d": int(row["Din D"]), "din_y": int(row["Din Y"]),
                                        "ing_d": int(row["İngilizce D"]), "ing_y": int(row["İngilizce Y"])
                                    }
                                    k_id = row.get("Kayıt ID")
                                    # Herhangi bir veri girilmişse ekle veya güncelle
                                    if sum([kayit_paketi[k] for k in kayit_paketi if k not in ["ogrenci_id", "deneme_adi"]]) > 0:
                                        if pd.notnull(k_id):
                                            supabase.table("lgs_denemeleri").update(kayit_paketi).eq("id", int(k_id)).execute()
                                        else:
                                            supabase.table("lgs_denemeleri").insert(kayit_paketi).execute()
                                    elif pd.notnull(k_id): # Veri sıfırlandıysa sil
                                        supabase.table("lgs_denemeleri").delete().eq("id", int(k_id)).execute()
                                
                                st.success("Sınav işlemleri başarıyla tamamlandı.")
                                st.rerun()

            # --- TAB 2: SINIF GENEL SIRALAMASI ---
            with tab_lgs2:
                mevcut_denemeler_res = supabase.table("lgs_denemeleri").select("deneme_adi").in_("ogrenci_id", ogr_idler).execute()
                if mevcut_denemeler_res.data:
                    benzersiz_denemeler = list(set([d["deneme_adi"] for d in mevcut_denemeler_res.data]))
                    secili_deneme_analiz = st.selectbox("Analiz Edilecek Denemeyi Seçin", benzersiz_denemeler)
                    
                    s_veri_res = supabase.table("lgs_denemeleri").select("*").eq("deneme_adi", secili_deneme_analiz).in_("ogrenci_id", ogr_idler).execute()
                    
                    if s_veri_res.data:
                        df_s = pd.DataFrame(s_veri_res.data)
                        df_s["Öğrenci"] = df_s["ogrenci_id"].apply(lambda x: next((ogr["ad_soyad"] for ogr in ogrenciler if ogr["id"] == x), "Bilinmiyor"))
                        
                        df_s["Türkçe Net"] = df_s["turkce_d"] - (df_s["turkce_y"] / 3)
                        df_s["Matematik Net"] = df_s["mat_d"] - (df_s["mat_y"] / 3)
                        df_s["Fen Net"] = df_s["fen_d"] - (df_s["fen_y"] / 3)
                        df_s["İnkılap Net"] = df_s["ink_d"] - (df_s["ink_y"] / 3)
                        df_s["Din Net"] = df_s["din_d"] - (df_s["din_y"] / 3)
                        df_s["İngilizce Net"] = df_s["ing_d"] - (df_s["ing_y"] / 3)
                        
                        df_s["Toplam Net"] = df_s[["Türkçe Net", "Matematik Net", "Fen Net", "İnkılap Net", "Din Net", "İngilizce Net"]].sum(axis=1)
                        
                        # Sıralama
                        df_s = df_s.sort_values(by="Toplam Net", ascending=False).reset_index(drop=True)
                        df_s.index += 1
                        df_s = df_s.reset_index().rename(columns={"index": "Sınıf Derecesi"})
                        
                        tablo_s = df_s[["Sınıf Derecesi", "Öğrenci", "Türkçe Net", "Matematik Net", "Fen Net", "İnkılap Net", "Din Net", "İngilizce Net", "Toplam Net"]]
                        
                        st.subheader(f"🏆 {secili_deneme_analiz} - Sınıf Başarı Sıralaması")
                        st.dataframe(tablo_s, hide_index=True, use_container_width=True)
                else:
                    st.info("Sınıf sıralaması oluşturulacak herhangi bir deneme verisi bulunmuyor.")

            # --- TAB 3: ÖĞRENCİ ÖZEL ANALİZİ ---
            with tab_lgs3:
                secilen_ogr_analiz = st.selectbox("Öğrenci Seçin", list(ogr_secenekleri.keys()), key="lgs_ogr_secim_analiz")
                secilen_ogr_id_analiz = ogr_secenekleri[secilen_ogr_analiz]
                
                lgs_res = supabase.table("lgs_denemeleri").select("*").eq("ogrenci_id", secilen_ogr_id_analiz).execute()
                
                if not lgs_res.data:
                    st.info("Bu öğrenciye ait LGS analizi oluşturulacak veri bulunmamaktadır.")
                else:
                    df_lgs = pd.DataFrame(lgs_res.data)
                    df_lgs["Türkçe Net"] = df_lgs["turkce_d"] - (df_lgs["turkce_y"] / 3)
                    df_lgs["Matematik Net"] = df_lgs["mat_d"] - (df_lgs["mat_y"] / 3)
                    df_lgs["Fen Net"] = df_lgs["fen_d"] - (df_lgs["fen_y"] / 3)
                    df_lgs["İnkılap Net"] = df_lgs["ink_d"] - (df_lgs["ink_y"] / 3)
                    df_lgs["Din Net"] = df_lgs["din_d"] - (df_lgs["din_y"] / 3)
                    df_lgs["İngilizce Net"] = df_lgs["ing_d"] - (df_lgs["ing_y"] / 3)
                    
                    df_lgs["Toplam Net"] = df_lgs[["Türkçe Net", "Matematik Net", "Fen Net", "İnkılap Net", "Din Net", "İngilizce Net"]].sum(axis=1)
                    
                    # MEB Benzeri Tahmini LGS Puanı (Katsayı Oranlarına Göre Yaklaşık Formül: T,M,F=4.2; İ,D,İ=1.6; Taban=200, Max=500)
                    df_lgs["Tahmini Puan"] = 200 + (df_lgs["Türkçe Net"]*4.2) + (df_lgs["Matematik Net"]*4.2) + (df_lgs["Fen Net"]*4.2) + (df_lgs["İnkılap Net"]*1.6) + (df_lgs["Din Net"]*1.6) + (df_lgs["İngilizce Net"]*1.6)
                    df_lgs["Tahmini Puan"] = df_lgs["Tahmini Puan"].round(2)
                    
                    son_deneme_verisi = df_lgs.iloc[-1]
                    
                    col_m1, col_m2, col_m3 = st.columns(3)
                    col_m1.metric("Mevcut Toplam Net", f"{son_deneme_verisi['Toplam Net']:.2f} Net")
                    col_m2.metric("Tahmini LGS Puanı", f"{son_deneme_verisi['Tahmini Puan']} Puan")
                    
                    # İvme Hesaplama (Son 2 sınav farkı)
                    if len(df_lgs) > 1:
                        ivme = df_lgs.iloc[-1]["Toplam Net"] - df_lgs.iloc[-2]["Toplam Net"]
                        if ivme > 0:
                            col_m3.metric("Son Sınav İvmesi", f"+{ivme:.2f} Net", "Artış Trendi")
                        else:
                            col_m3.metric("Son Sınav İvmesi", f"{ivme:.2f} Net", "-Düşüş Trendi", delta_color="inverse")
                    else:
                        col_m3.metric("Son Sınav İvmesi", "Veri Yetersiz")
                    
                    st.divider()
                    
                    # Dalgalanma & Güçlü Alan Analizi (Standart Sapma ve Ortalama)
                    ders_netleri = ["Türkçe Net", "Matematik Net", "Fen Net", "İnkılap Net", "Din Net", "İngilizce Net"]
                    std_devs = df_lgs[ders_netleri].std()
                    ortalamalar = df_lgs[ders_netleri].mean()
                    
                    guclu_ders = ortalamalar.idxmax().replace(" Net", "")
                    en_dalgalan_ders = std_devs.idxmax().replace(" Net", "")
                    
                    st.write("#### 🔍 Gelişmiş Risk ve Potansiyel Analizi")
                    st.write(f"- **💪 En İstikrarlı ve Güçlü Ders:** :green[{guclu_ders}]")
                    st.write(f"- **⚠️ Sınav Kaygısı / Dalgalanma Riski Yüksek Ders:** :red[{en_dalgalan_ders}] (Net standardı sürekli değişiyor, öğrencinin bilgi kalıcılığı kontrol edilmeli.)")
                    
                    st.write("#### 📈 LGS Puan ve Net Gelişim Grafiği")
                    df_grafik_tot = df_lgs[["deneme_adi", "Toplam Net", "Tahmini Puan"]].set_index("deneme_adi")
                    st.line_chart(df_grafik_tot, use_container_width=True)

elif menu == "🛠️ Test Verisi Üret":
    st.header("Sisteme Rastgele Test Verisi Ekleme")
    st.warning("Bu işlem veritabanınıza rastgele öğrenciler, notlar ve ödevler ekleyecektir. Gerçek verilerinizle karışmaması için öğrencilerin ismine '(Test)' ibaresi eklenecektir.")

    if st.button("Verileri Üret ve Sisteme Yükle", type="primary"):
        isim_havuzu = ["Ahmet Yılmaz", "Ayşe Kaya", "Mehmet Demir", "Fatma Çelik", "Ali Can", "Zeynep Şahin", "Mustafa Yıldız", "Elif Özdemir", "Hasan Aydın", "Hatice Arslan", "Burak Polat", "Büşra Çetin", "Emre Erdoğan", "Merve Koç", "Oğuzhan Şen", "Ceren Yavuz", "Yunus Emre", "İrem Kurt", "Okan Aslan", "Selin Kılıç"]
        durumlar = ["Yaptı", "Yarım", "Yapmadı", "Gelmedi"]

        with st.spinner("Sistem tohumlanıyor (Seeding)... Lütfen bekleyin."):
            ogrenciler_data = []
            for sinif in sinif_listesi:
                secilenler = random.sample(isim_havuzu, 10)
                for isim in secilenler:
                    ogrenciler_data.append({"ad_soyad": f"{isim} (Test)", "sinif": sinif})
            res_ogr = supabase.table("ogrenciler").insert(ogrenciler_data).execute()

            notlar_data = []
            lgs_data = []
            ogr_sinif_map = {ogr['id']: ogr['sinif'] for ogr in res_ogr.data}

            for ogr_id, sinif in ogr_sinif_map.items():
                for brans in branslar:
                    notlar_data.append({
                        "ogrenci_id": ogr_id,
                        "brans": brans,
                        "sinav_1": random.randint(40, 100),
                        "sinav_2": random.randint(40, 100),
                        "perf_1": random.randint(50, 100),
                        "perf_2": random.randint(50, 100),
                        "proje": random.randint(70, 100)
                    })
                if sinif == "8-A":
                    # Trendi simüle etmek için artan zorluklar
                    for i in range(1, 9): 
                        lgs_data.append({
                            "ogrenci_id": ogr_id,
                            "deneme_adi": f"Deneme {i}",
                            "turkce_d": random.randint(12, 19), "turkce_y": random.randint(0, 5),
                            "mat_d": random.randint(6, 15), "mat_y": random.randint(0, 8),
                            "fen_d": random.randint(12, 18), "fen_y": random.randint(0, 5),
                            "ink_d": random.randint(6, 10), "ink_y": random.randint(0, 3),
                            "din_d": random.randint(7, 10), "din_y": random.randint(0, 2),
                            "ing_d": random.randint(6, 10), "ing_y": random.randint(0, 3)
                        })

            supabase.table("notlar").insert(notlar_data).execute()
            if lgs_data:
                supabase.table("lgs_denemeleri").insert(lgs_data).execute()

            odevler_data = []
            for sinif in sinif_listesi:
                for brans in branslar:
                    for i in range(1, 4):
                        odevler_data.append({
                            "brans": brans,
                            "sinif": sinif,
                            "odev_adi": f"Test Ödevi {i}",
                            "aciklama": "Sistem testi için otomatik oluşturuldu.",
                            "teslim_tarihi": str(date.today() - timedelta(days=random.randint(1, 15)))
                        })
            res_odev = supabase.table("odevler").insert(odevler_data).execute()

            teslimler_data = []
            for odev in res_odev.data:
                ilgili_ogrenciler = [k for k, v in ogr_sinif_map.items() if v == odev['sinif']]
                for ogr_id in ilgili_ogrenciler:
                    teslimler_data.append({
                        "odev_id": odev['id'], 
                        "ogrenci_id": ogr_id, 
                        "durum": random.choice(durumlar),
                        "ogretmen_notu": "Test notu."
                    })
            
            chunk_size = 500
            for i in range(0, len(teslimler_data), chunk_size):
                supabase.table("odev_teslimleri").insert(teslimler_data[i:i+chunk_size]).execute()

        st.success("Test verileri başarıyla oluşturuldu ve veritabanına eklendi!")
