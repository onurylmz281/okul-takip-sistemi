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
                    n = [row["1. Yazılı"], row["2. Yazılı"], row["1. Performans"], row["2. Performans"], row["Proje"]]
                    g = [float(x) for x in n if pd.notnull(x)]
                    return round(sum(g) / len(g), 2) if g else None
                    
                df_gosterim["Ortalama"] = df_gosterim.apply(satir_ort, axis=1)
                df_gosterim = df_gosterim[["Branş", "1. Yazılı", "2. Yazılı", "1. Performans", "2. Performans", "Proje", "Ortalama"]]
                
                st.dataframe(df_gosterim, hide_index=True, use_container_width=True)
            else:
                st.info("Bu öğrenciye ait herhangi bir not verisi bulunmamaktadır.")
                
            st.divider()

            # --- 3. ÖDEV TAKİP BİLGİLERİ ---
            st.subheader("📚 Ödev İstatistikleri ve Detayları")
            if odevler_res.data:
                df_odevler = pd.DataFrame(odevler_res.data)
                durum_dagilimi = df_odevler["durum"].value_counts()
                
                col_grafik, col_tablo = st.columns([1, 2])
                with col_grafik:
                    st.write("**Genel Dağılım**")
                    st.bar_chart(durum_dagilimi)
                
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
                        st.dataframe(pd.DataFrame(detay_liste), hide_index=True, use_container_width=True)
            else:
                st.info("Bu öğrenciye ait ödev değerlendirmesi bulunmamaktadır.")

            # --- 4. LGS TAKİP (SADECE 8. SINIFLAR) ---
            if is_8th_grade:
                st.divider()
                st.subheader("🎯 LGS Deneme Gelişimi")
                if lgs_res and lgs_res.data:
                    grafik_verisi = []
                    for d in lgs_res.data:
                        toplam = (d["turkce_d"] - d["turkce_y"]/3) + (d["mat_d"] - d["mat_y"]/3) + (d["fen_d"] - d["fen_y"]/3) + (d["ink_d"] - d["ink_y"]/3) + (d["din_d"] - d["din_y"]/3) + (d["ing_d"] - d["ing_y"]/3)
                        grafik_verisi.append({"Deneme": d["deneme_adi"], "Toplam Net": toplam})
                        
                    df_lgs_grafik = pd.DataFrame(grafik_verisi).set_index("Deneme")
                    st.line_chart(df_lgs_grafik)
                else:
                    st.info("Sisteme girilmiş LGS deneme verisi bulunmamaktadır.")
    else:
        st.warning("Bu sınıfta henüz kayıtlı öğrenci bulunmuyor.")

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
                    supabase.table("notlar").update(kayit_verisi).eq("id", int(row["Kayıt ID"])).execute()
                elif not_var_mi:
                    supabase.table("notlar").insert(kayit_verisi).execute()
            
            st.success("Notlar başarıyla kaydedildi.")
            st.rerun()

elif menu == "Ödev Takip":
    st.header(f"Ödev Takip Modülü - {secilen_brans}")
    tab1, tab2 = st.tabs(["📝 Yeni Ödev Tanımla", "✅ Ödev Kontrolü"])
    
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
                st.success("Ödev başarıyla tanımlandı. 'Ödev Kontrolü' sekmesinden değerlendirme yapabilirsiniz.")
                st.rerun()

    with tab2:
        secilen_sinif_kontrol = st.selectbox("Sınıf Seçin", sinif_listesi, key="odev_sinif_kontrol")
        
        odevler_res = supabase.table("odevler").select("*").eq("sinif", secilen_sinif_kontrol).eq("brans", secilen_brans).execute()
        
        if not odevler_res.data:
            st.info("Bu sınıfa ve branşa ait tanımlanmış bir ödev bulunmamaktadır.")
        else:
            odev_secenekleri = {f"{o['odev_adi']} (Teslim: {o['teslim_tarihi']})": o['id'] for o in odevler_res.data}
            secilen_odev_etiketi = st.selectbox("Kontrol Edilecek Ödevi Seçin", list(odev_secenekleri.keys()))
            secilen_odev_id = odev_secenekleri[secilen_odev_etiketi]
            
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
                
                st.write("Aşağıdaki tablodan öğrencilerin ödev durumlarını ve (varsa) açıklamanızı girip kaydedin.")
                
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
                
                if st.button("Ödev Durumlarını Kaydet", type="primary"):
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
                    
                    st.success("Ödev kontrolleri ve öğretmen notları başarıyla kaydedildi.")
                    st.rerun()

elif menu == "LGS Takip":
    st.header("LGS Takip Modülü")
    st.write("Bu modülün arayüzü 4. adımda entegre edilecektir.")
