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
branslar = ["Matematik", "Türkçe", "Fen Bilimleri", "Sosyal Bilgiler", "İngilizce", "Din Kültürü", "İnkılap Tarihi"]
sinif_listesi = ["5-A", "6-A", "7-A", "8-A"]

def get_base64_logo():
    if os.path.exists("logo.png"):
        with open("logo.png", "rb") as f:
            data = f.read()
            return base64.b64encode(data).decode()
    return None

# --- 4. OTURUM YÖNETİMİ ---
if "giris_yapildi" not in st.session_state:
    st.session_state.giris_yapildi = False

# --- 5. GİRİŞ EKRANI (WELCOME PAGE) ---
if not st.session_state.giris_yapildi:
    col_l, col_r = st.columns([1, 4])
    with col_l:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=150)
        else:
            st.title("🎓")
    with col_r:
        st.title("Sadiye ve Abdullah Tan Ortaokulu")
        st.subheader("Okul Takip Paneline Hoşgeldiniz")
        st.info("Bu panel üzerinden öğrenci akademik gelişimini, ödev takiplerini ve LGS deneme analizlerini yönetebilirsiniz.")

    st.divider()
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        with st.form("giris_formu"):
            st.write("#### 🔐 Yetkili Girişi")
            k_adi = st.text_input("Kullanıcı Adı")
            sifre = st.text_input("Şifre", type="password")
            if st.form_submit_button("Sisteme Giriş Yap", use_container_width=True):
                if k_adi == "admin" and sifre == "123456":
                    st.session_state.giris_yapildi = True
                    st.rerun()
                else:
                    st.error("Hatalı bilgiler.")
    st.stop()

# --- 6. ANA UYGULAMA (GİRİŞ YAPILDIKTAN SONRA) ---

# --- Üst Bar (Başlık + Sağ Üst Logo) ---
top_col1, top_col2 = st.columns([8, 1])
with top_col1:
    st.title("🚀 Okul Takip Sistemi")
with top_col2:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=80)

# Sidebar
if st.sidebar.button("🚪 Güvenli Çıkış", use_container_width=True):
    st.session_state.giris_yapildi = False
    st.rerun()

st.sidebar.divider()
secilen_brans = st.sidebar.selectbox("İşlem Yapılacak Branş", branslar)
menu = st.sidebar.radio("Modüller", ["Öğrenci Yönetimi", "Öğrenci Profil Paneli", "Not Takip", "Ödev Takip", "LGS Takip", "🛠️ Test Verisi Üret"])

# --- MODÜL 1: ÖĞRENCİ YÖNETİMİ ---
if menu == "Öğrenci Yönetimi":
    st.header("👥 Öğrenci Yönetimi")
    t1, t2 = st.tabs(["➕ Ekle / Listele", "🗑️ Öğrenci Sil"])
    
    with t1:
        s_sec = st.selectbox("Sınıf Seçin", sinif_listesi, key="o_e_s")
        with st.form("ogr_ekle", clear_on_submit=True):
            ad = st.text_input("Adı Soyadı")
            if st.form_submit_button("Kaydet") and ad:
                supabase.table("ogrenciler").insert({"ad_soyad": ad, "sinif": s_sec}).execute()
                st.success("Kaydedildi.")
                st.rerun()
        
        res = supabase.table("ogrenciler").select("*").eq("sinif", s_sec).execute()
        if res.data:
            st.dataframe(pd.DataFrame(res.data)[["ad_soyad"]], use_container_width=True, hide_index=True)

    with t2:
        s_sil = st.selectbox("Sınıf Seçin", sinif_listesi, key="o_s_s")
        res_sil = supabase.table("ogrenciler").select("id, ad_soyad").eq("sinif", s_sil).execute()
        if res_sil.data:
            ogr_dict = {o["ad_soyad"]: o["id"] for o in res_sil.data}
            sil_ad = st.selectbox("Silinecek Öğrenci", list(ogr_dict.keys()))
            if st.button("Kalıcı Olarak Sil", type="primary"):
                oid = ogr_dict[sil_ad]
                supabase.table("notlar").delete().eq("ogrenci_id", oid).execute()
                supabase.table("odev_teslimleri").delete().eq("ogrenci_id", oid).execute()
                supabase.table("lgs_denemeleri").delete().eq("ogrenci_id", oid).execute()
                supabase.table("ogrenciler").delete().eq("id", oid).execute()
                st.success("Tüm veriler silindi.")
                st.rerun()

# --- MODÜL 2: ÖĞRENCİ PROFİL PANELİ ---
elif menu == "Öğrenci Profil Paneli":
    st.header("👤 Öğrenci Profil Paneli")
    s_p = st.selectbox("Sınıf Seçin", sinif_listesi)
    res_p = supabase.table("ogrenciler").select("*").eq("sinif", s_p).execute()
    
    if res_p.data:
        o_isimler = [o["ad_soyad"] for o in res_p.data]
        secili_o = st.selectbox("Öğrenci Seçin", ["Seçiniz..."] + o_isimler)
        
        if secili_o != "Seçiniz...":
            o_data = next(o for o in res_p.data if o["ad_soyad"] == secili_o)
            oid = o_data["id"]
            
            # Notlar
            n_res = supabase.table("notlar").select("*").eq("ogrenci_id", oid).execute()
            g_ort = 0
            n_html = ""
            if n_res.data:
                df_n = pd.DataFrame(n_res.data).rename(columns={"brans":"Branş","sinav_1":"S1","sinav_2":"S2","perf_1":"P1","perf_2":"P2","proje":"PRJ"})
                def calc_ort(row):
                    vals = [row["S1"], row["S2"], row["P1"], row["P2"], row["PRJ"]]
                    vals = [float(v) for v in vals if v is not None]
                    return round(sum(vals)/len(vals), 2) if vals else 0
                df_n["Ortalama"] = df_n.apply(calc_ort, axis=1)
                st.subheader("📊 Not Durumu")
                st.dataframe(df_n[["Branş","S1","S2","P1","P2","PRJ","Ortalama"]], use_container_width=True, hide_index=True)
                n_html = df_n[["Branş","S1","S2","P1","P2","PRJ","Ortalama"]].to_html(index=False, border=1)
                g_ort = round(df_n["Ortalama"].mean(), 2)

            # Ödevler
            h_res = supabase.table("odev_teslimleri").select("durum, odevler(brans)").eq("ogrenci_id", oid).execute()
            h_html = ""
            h_orani = 0
            if h_res.data:
                df_h = pd.DataFrame([{"Branş": x["odevler"]["brans"], "Durum": x["durum"]} for x in h_res.data])
                h_orani = round((df_h[df_h["Durum"]=="Yaptı"].shape[0] / len(df_h)) * 100, 1)
                st.subheader("📚 Ödev İstatistiği")
                st.write(f"Ödev Tamamlama Oranı: %{h_orani}")
                h_html = df_h.to_html(index=False, border=1)
            
            # PDF Rapor Butonu
            pdf_html = f"<html><body onload='window.print()'><h2>{secili_o} Raporu</h2><p>Ortalama: {g_ort} | Ödev: %{h_orani}</p>{n_html}<br>{h_html}</body></html>"
            st.download_button("📄 PDF Raporu İndir", pdf_html, file_name=f"{secili_o}_profil.html", mime="text/html")

# --- MODÜL 3: NOT TAKİP ---
elif menu == "Not Takip":
    st.header(f"📝 Not Girişi - {secilen_brans}")
    snf = st.selectbox("Sınıf Seçin", sinif_listesi)
    o_res = supabase.table("ogrenciler").select("id, ad_soyad").eq("sinif", snf).execute()
    
    if o_res.data:
        n_res = supabase.table("notlar").select("*").eq("brans", secilen_brans).in_("ogrenci_id", [x["id"] for x in o_res.data]).execute()
        n_map = {x["ogrenci_id"]: x for x in n_res.data}
        
        raw_data = []
        for o in o_res.data:
            m = n_map.get(o["id"], {})
            raw_data.append({
                "Kayıt ID": m.get("id"), "Öğrenci ID": o["id"], "Öğrenci": o["ad_soyad"],
                "Sınav 1": m.get("sinav_1"), "Sınav 2": m.get("sinav_2"),
                "Perf 1": m.get("perf_1"), "Perf 2": m.get("perf_2"), "Proje": m.get("proje")
            })
        
        df_edit = st.data_editor(pd.DataFrame(raw_data), column_config={"Kayıt ID":None,"Öğrenci ID":None}, use_container_width=True, hide_index=True)
        
        if st.button("Notları Kaydet", type="primary"):
            for _, r in df_edit.iterrows():
                pak = {
                    "ogrenci_id": r["Öğrenci ID"], "brans": secilen_brans,
                    "sinav_1": r["Sınav 1"], "sinav_2": r["Sınav 2"],
                    "perf_1": r["Perf 1"], "perf_2": r["Perf 2"], "proje": r["Proje"]
                }
                if r["Kayıt ID"]:
                    supabase.table("notlar").update(pak).eq("id", r["Kayıt ID"]).execute()
                else:
                    if any([r["Sınav 1"], r["Sınav 2"], r["Perf 1"], r["Perf 2"], r["Proje"]]):
                        supabase.table("notlar").insert(pak).execute()
            st.success("Kaydedildi.")
            st.rerun()

# --- MODÜL 4: ÖDEV TAKİP ---
elif menu == "Ödev Takip":
    st.header(f"📦 Ödev Takip - {secilen_brans}")
    tab1, tab2 = st.tabs(["📝 Ödev Tanımla", "✅ Değerlendir"])
    
    with tab1:
        s_o = st.selectbox("Sınıf", sinif_listesi, key="s_o")
        with st.form("o_tanim"):
            baslik = st.text_input("Ödev Konusu")
            tarih = st.date_input("Teslim Tarihi")
            if st.form_submit_button("Ödev Oluştur") and baslik:
                supabase.table("odevler").insert({"brans":secilen_brans, "sinif":s_o, "odev_adi":baslik, "teslim_tarihi":str(tarih)}).execute()
                st.success("Ödev oluşturuldu.")

    with tab2:
        s_d = st.selectbox("Sınıf", sinif_listesi, key="s_d")
        o_list = supabase.table("odevler").select("*").eq("brans", secilen_brans).eq("sinif", s_d).execute()
        if o_list.data:
            o_sec = st.selectbox("Ödev Seçin", [f"{x['odev_adi']} ({x['teslim_tarihi']})" for x in o_list.data])
            o_id = next(x["id"] for x in o_list.data if f"{x['odev_adi']} ({x['teslim_tarihi']})" == o_sec)
            
            ogrs = supabase.table("ogrenciler").select("id, ad_soyad").eq("sinif", s_d).execute()
            tsl = supabase.table("odev_teslimleri").select("*").eq("odev_id", o_id).execute()
            tsl_map = {x["ogrenci_id"]: x for x in tsl.data}
            
            h_data = []
            for og in ogrs.data:
                m = tsl_map.get(og["id"], {})
                h_data.append({"Kayıt ID": m.get("id"), "Öğrenci ID": og["id"], "Öğrenci": og["ad_soyad"], "Durum": m.get("durum", "Yapmadı")})
            
            df_h = st.data_editor(pd.DataFrame(h_data), column_config={"Durum": st.column_config.SelectboxColumn(options=["Yaptı","Yarım","Yapmadı","Gelmedi"]), "Kayıt ID":None, "Öğrenci ID":None}, hide_index=True)
            if st.button("Teslimleri Kaydet"):
                for _, r in df_h.iterrows():
                    if r["Kayıt ID"]:
                        supabase.table("odev_teslimleri").update({"durum": r["Durum"]}).eq("id", r["Kayıt ID"]).execute()
                    else:
                        supabase.table("odev_teslimleri").insert({"odev_id": o_id, "ogrenci_id": r["Öğrenci ID"], "durum": r["Durum"]}).execute()
                st.success("Güncellendi.")

# --- MODÜL 5: LGS TAKİP ---
elif menu == "LGS Takip":
    st.header("🎯 LGS Hazırlık Süreci")
    snf8 = "8-A" # Prototipte 8-A baz alındı
    t1, t2, t3 = st.tabs(["📝 Giriş", "🏆 Sıralama", "⚖️ Karşılaştırma"])
    
    with t1:
        d_ad = st.text_input("Deneme Adı (Örn: Özdebir-1)")
        o8 = supabase.table("ogrenciler").select("id, ad_soyad").eq("sinif", snf8).execute()
        if o8.data:
            l_data = []
            for o in o8.data:
                l_data.append({"Öğrenci ID":o["id"],"Öğrenci":o["ad_soyad"],"Mat D":0,"Mat Y":0,"Türk D":0,"Türk Y":0,"Fen D":0,"Fen Y":0,"İnk D":0,"İnk Y":0,"Din D":0,"Din Y":0,"İng D":0,"İng Y":0,"Puan":200.0})
            
            df_l = st.data_editor(pd.DataFrame(l_data), column_config={"Öğrenci ID":None}, hide_index=True)
            if st.button("Toplu Deneme Kaydet") and d_ad:
                for _, r in df_l.iterrows():
                    supabase.table("lgs_denemeleri").insert({
                        "ogrenci_id":r["Öğrenci ID"],"deneme_adi":d_ad,"lgs_puani":r["Puan"],
                        "mat_d":r["Mat D"],"mat_y":r["Mat Y"],"turkce_d":r["Türk D"],"turkce_y":r["Türk Y"],
                        "fen_d":r["Fen D"],"fen_y":r["Fen Y"],"ink_d":r["İnk D"],"ink_y":r["İnk Y"],
                        "din_d":r["Din D"],"din_y":r["Din Y"],"ing_d":r["İng D"],"ing_y":r["İng Y"]
                    }).execute()
                st.success("Kaydedildi.")

    with t2:
        mevcut = supabase.table("lgs_denemeleri").select("deneme_adi").execute()
        if mevcut.data:
            d_list = list(set([x["deneme_adi"] for x in mevcut.data]))
            d_sec = st.selectbox("Sınav Seç", d_list)
            s_res = supabase.table("lgs_denemeleri").select("*, ogrenciler(ad_soyad)").eq("deneme_adi", d_sec).execute()
            if s_res.data:
                df_s = pd.DataFrame([{"Öğrenci": x["ogrenciler"]["ad_soyad"], "Puan": x["lgs_puani"]} for x in s_res.data])
                df_s = df_s.sort_values("Puan", ascending=False).reset_index(drop=True)
                df_s.index += 1
                st.dataframe(df_s, use_container_width=True)

    with t3:
        o_res = supabase.table("ogrenciler").select("id, ad_soyad").eq("sinif", snf8).execute()
        if o_res.data:
            o_sec_k = st.selectbox("Öğrenci", [x["ad_soyad"] for x in o_res.data])
            oid_k = next(x["id"] for x in o_res.data if x["ad_soyad"] == o_sec_k)
            d_res = supabase.table("lgs_denemeleri").select("*").eq("ogrenci_id", oid_k).execute()
            if len(d_res.data) >= 2:
                dnms = [x["deneme_adi"] for x in d_res.data]
                secim = st.multiselect("2 Sınav Seçin", dnms, default=dnms[-2:])
                if len(secim) == 2:
                    v1 = next(x for x in d_res.data if x["deneme_adi"] == secim[0])
                    v2 = next(x for x in d_res.data if x["deneme_adi"] == secim[1])
                    
                    labels = ["Mat","Türkçe","Fen","İnkılap","Din","İng"]
                    n1 = [v1["mat_d"]-v1["mat_y"]/3, v1["turkce_d"]-v1["turkce_y"]/3, v1["fen_d"]-v1["fen_y"]/3, v1["ink_d"]-v1["ink_y"]/3, v1["din_d"]-v1["din_y"]/3, v1["ing_d"]-v1["ing_y"]/3]
                    n2 = [v2["mat_d"]-v2["mat_y"]/3, v2["turkce_d"]-v2["turkce_y"]/3, v2["fen_d"]-v2["fen_y"]/3, v2["ink_d"]-v2["ink_y"]/3, v2["din_d"]-v2["din_y"]/3, v2["ing_d"]-v2["ing_y"]/3]
                    
                    fig, ax = plt.subplots()
                    x = np.arange(len(labels))
                    ax.bar(x - 0.2, n1, 0.4, label=secim[0])
                    ax.bar(x + 0.2, n2, 0.4, label=secim[1])
                    ax.set_xticks(x); ax.set_xticklabels(labels); ax.legend()
                    st.pyplot(fig)
                    
                    p_diff = v2["lgs_puani"] - v1["lgs_puani"]
                    st.metric("Puan Değişimi", f"{v2['lgs_puani']}", f"{p_diff:+.2f}")

# --- MODÜL 6: TEST VERİSİ ---
elif menu == "🛠️ Test Verisi Üret":
    st.header("🛠️ Test Verisi Üretme")
    if st.button("Rastgele Veri Yükle (Prototip)"):
        with st.spinner("Yükleniyor..."):
            isiml = ["Ali","Ayşe","Mehmet","Zeynep","Can"]
            for isim in isiml:
                # Ogr
                ins = supabase.table("ogrenciler").insert({"ad_soyad": f"{isim} (Test)", "sinif": "8-A"}).execute()
                new_id = ins.data[0]["id"]
                # Not
                for b in branslar:
                    supabase.table("notlar").insert({"ogrenci_id":new_id, "brans":b, "sinav_1":random.randint(50,100)}).execute()
            st.success("Test verileri eklendi.")
