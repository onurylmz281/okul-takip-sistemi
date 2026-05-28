import streamlit as st
import pandas as pd
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
                                    status_counts, 
                                    labels=status_counts.index, 
                                    autopct='%1.1f%%', 
                                    startangle=90, 
                                    colors=current_colors,
                                    wedgeprops=dict(width=0.4, edgecolor='w')
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
                    st.subheader("🎯 LGS Deneme Sınavları Gelişimi")
                    
                    grafik_verisi = []
                    for d in lgs_res.data:
                        toplam = (d["turkce_d"] - d["turkce_y"]/3) + (d["mat_d"] - d["mat_y"]/3) + (d["fen_d"] - d["fen_y"]/3) + (d["ink_d"] - d["ink_y"]/3) + (d["din_d"] - d["din_y"]/3) + (d["ing_d"] - d["ing_y"]/3)
                        grafik_verisi.append({"Deneme": d["deneme_adi"], "Toplam Net": toplam})
                        
                    df_lgs_grafik = pd.DataFrame(grafik_verisi)
                    st.line_chart(df_lgs_grafik.set_index("Deneme"))
                    
                    fig2, ax2 = plt.subplots(figsize=(5.5, 2.5))
                    ax2.plot(df_lgs_grafik["Deneme"], df_lgs_grafik["Toplam Net"], marker='o', color='#2196F3', linewidth=2)
                    ax2.set_ylabel('Toplam Net')
                    ax2.grid(True, linestyle='--', alpha=0.5)
                    plt.xticks(rotation=15, fontsize=8)
                    buf2 = io.BytesIO()
                    plt.savefig(buf2, format='png', bbox_inches='tight', dpi=150)
                    buf2.seek(0)
                    lgs_line_base64 = base64.b64encode(buf2.read()).decode('utf-8')
                    plt.close(fig2)

            st.sidebar.markdown("---")
            st.sidebar.subheader("Öğrenci Genel Durumu")
            st.sidebar.metric("Genel Not Ortalaması", f"{genel_ortalama} / 100")
            st.sidebar.metric("Ödev Tamamlama Oranı", f"% {odev_orani}")
            if is_8th_grade:
                st.sidebar.metric("Son Deneme Neti", f"{son_deneme_neti} Net")

            st.divider()
            st.write("#### 💾 Bireysel Raporu Dışa Aktar")
            
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
                .card h3 {{ margin: 0 0 10px 0; font-size: 13px; color: #666; }}
                .card p {{ margin: 0; font-size: 18px; font-weight: bold; color: #111; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }}
                th, td {{ border: 1px solid #ddd; padding: 10px; text-align: center; }}
                th {{ background-color: #f4f6f8; font-weight: bold; }}
                .section-title {{ margin-top: 30px; border-bottom: 2px solid #2196F3; padding-bottom: 5px; color: #111; }}
                .graph-container {{ text-align: center; margin-top: 15px; margin-bottom: 15px; width: 100%; }}
                .lgs-container {{ text-align: center; margin-top: 20px; }}
                .graph-img-lgs {{ max-width: 550px; height: auto; }}
                .filter-info {{ font-size: 12px; color: #555; background: #eef1f6; padding: 8px; border-radius: 4px; display: inline-block; margin-bottom: 15px; }}
            </style>
            </head>
            <body onload="window.print()">
                <table class="header-table">
                    <tr>
                        <td style="text-align: left; border: none; font-size: 22px; font-weight: bold;">{secilen_ogrenci} - Bireysel Gelişim Raporu</td>
                        <td style="text-align: right; border: none; color: #666;"><b>Sınıf:</b> {secilen_sinif} | <b>Tarih:</b> {date.today().strftime('%d.%m.%Y')}</td>
                    </tr>
                </table>
                
                <div class="card-container">
                    <div class="card">
                        <h3>Genel Not Ortalaması</h3>
                        <p>{genel_ortalama} / 100</p>
                    </div>
                    <div class="card">
                        <h3>Ödev Tamamlama Oranı (Genel)</h3>
                        <p>% {odev_orani}</p>
                    </div>
                    {"<div class='card'><h3>Son LGS Deneme Neti</h3><p>" + str(son_deneme_neti) + " Net</p></div>" if is_8th_grade else ""}
                </div>

                <h3 class="section-title">📊 Ders Notları Detayları</h3>
                {df_html_notlar if df_html_notlar else "<p>Kayıtlı not verisi bulunmuyor.</p>"}

                <h3 class="section-title">📚 Ödev Durumu ve Takip Analizi</h3>
                <div class="filter-info"><b>Uygulanan Rapor Filtreleri:</b> Ders: {filtre_brans} | Durum: {filtre_durum}</div>
                
                {f'<div class="graph-container"><h4>Genel Ödev Dağılımı</h4><img src="data:image/png;base64,{genel_graph_base64}" style="max-width: 320px;"></div>' if genel_graph_base64 else ""}
                
                <div class="graph-container">
                    {pdf_brans_grafikleri_html if pdf_brans_grafikleri_html else ""}
                </div>
                
                <div style="margin-top: 15px;">
                    {df_html_odevler if df_html_odevler else "<p>Seçilen kriterlere uygun ödev verisi bulunmuyor.</p>"}
                </div>
            """
            
            if is_8th_grade and lgs_line_base64:
                html_icerik += f"""
                <h3 class="section-title">🎯 LGS Akademik Net Gelişim Grafiği</h3>
                <div class="lgs-container">
                    <img class="graph-img-lgs" src="data:image/png;base64,{lgs_line_base64}">
                </div>
                """
                
            html_icerik += """
            </body>
            </html>
            """
            
            st.download_button(
                label="👤 Seçili Filtrelerle Profil Raporunu PDF İndir",
                data=html_icerik,
                file_name=f"{secilen_ogrenci}_Gelişim_Raporu.html",
                mime="text/html"
            )
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
    tab1, tab2, tab3 = st.tabs(["📝 Yeni Ödev Tanımla", "✅ Ödev Kontrolü", "📊 Ödev Raporları"])
    
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
                    
                    st.success("Ödev kontrolleri başarıyla kaydedildi.")
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
                
                st.divider()
                st.write("#### 💾 Raporu Dışa Aktar")
                
                col_btn1, col_btn2 = st.columns(2)
                
                html_tablo = df_matris.to_html(border=1, justify='center')
                html_icerik_rapor = f"""
                <html>
                <head>
                <meta charset="utf-8">
                <title>{secilen_sinif_rapor} Ödev Raporu</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    h2 {{ text-align: center; color: #333; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }}
                    th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                    th {{ background-color: #f4f6f8; color: #333; }}
                    tr:nth-child(even) {{ background-color: #fafafa; }}
                </style>
                </head>
                <body onload="window.print()">
                    <h2>{secilen_sinif_rapor} Sınıfı Ödev Takip Çizelgesi</h2>
                    <p><b>Tarih Aralığı:</b> {baslangic_tarihi} - {bitis_tarihi}</p>
                    {html_tablo}
                </body>
                </html>
                """
                
                with col_btn1:
                    st.download_button(
                        label="📄 PDF Olarak Kaydet (Yazdırılabilir Form)",
                        data=html_icerik_rapor,
                        file_name=f"{secilen_sinif_rapor}_Odev_Raporu.html",
                        mime="text/html"
                    )
                
                csv = df_matris.to_csv(index=True, sep=";", encoding="utf-8-sig").encode("utf-8-sig")
                
                with col_btn2:
                    st.download_button(
                        label="📊 Excel İçin İndir",
                        data=csv,
                        file_name=f"{secilen_sinif_rapor}_Odev_Raporu.csv",
                        mime="text/csv"
                    )

elif menu == "LGS Takip":
    st.header("LGS Takip Modülü")
    
    # Sadece 8 ile başlayan sınıfları filtrele
    sinif_8_listesi = [s for s in sinif_listesi if s.startswith("8")]
    
    if not sinif_8_listesi:
        st.info("Sistemde kayıtlı 8. sınıf bulunmamaktadır. Bu modül şu anlık sadece 8. sınıflar için aktiftir.")
    else:
        secilen_sinif_lgs = st.selectbox("Sınıf Seçin", sinif_8_listesi, key="lgs_sinif_secim")
        
        ogrenciler_res = supabase.table("ogrenciler").select("id, ad_soyad").eq("sinif", secilen_sinif_lgs).execute()
        
        if not ogrenciler_res.data:
            st.warning("Bu sınıfta henüz kayıtlı öğrenci bulunmuyor. Lütfen Öğrenci Yönetimi modülünden öğrenci ekleyin.")
        else:
            ogrenciler = ogrenciler_res.data
            ogr_secenekleri = {ogr["ad_soyad"]: ogr["id"] for ogr in ogrenciler}
            
            tab_lgs1, tab_lgs2 = st.tabs(["📝 Deneme Notu Girişi", "📊 Başarı ve Gelişim Analizi"])
            
            with tab_lgs1:
                secilen_ogr_lgs = st.selectbox("Öğrenci Seçin", list(ogr_secenekleri.keys()), key="lgs_ogr_secim_giris")
                secilen_ogr_id = ogr_secenekleri[secilen_ogr_lgs]
                
                with st.form("lgs_not_giris_formu", clear_on_submit=True):
                    deneme_adi = st.text_input("Deneme Sınavı Adı (Örn: Deneme 1, Özdebir vb.)")
                    st.write("---")
                    st.write("**Doğru ve Yanlış Sayılarını Giriniz** (3 Yanlış 1 Doğruyu Götürür)")
                    
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown("##### 📕 Sözel Dersler")
                        turkce_d = st.number_input("Türkçe Doğru (Maks 20)", min_value=0, max_value=20, value=0)
                        turkce_y = st.number_input("Türkçe Yanlış", min_value=0, max_value=20, value=0)
                        st.divider()
                        ink_d = st.number_input("İnkılap T. Doğru (Maks 10)", min_value=0, max_value=10, value=0)
                        ink_y = st.number_input("İnkılap T. Yanlış", min_value=0, max_value=10, value=0)
                    
                    with c2:
                        st.markdown("##### 📘 Sayısal Dersler")
                        mat_d = st.number_input("Matematik Doğru (Maks 20)", min_value=0, max_value=20, value=0)
                        mat_y = st.number_input("Matematik Yanlış", min_value=0, max_value=20, value=0)
                        st.divider()
                        din_d = st.number_input("Din Kültürü Doğru (Maks 10)", min_value=0, max_value=10, value=0)
                        din_y = st.number_input("Din Kültürü Yanlış", min_value=0, max_value=10, value=0)
                        
                    with c3:
                        st.markdown("##### 🔬 Fen & Yabancı Dil")
                        fen_d = st.number_input("Fen Bilimleri Doğru (Maks 20)", min_value=0, max_value=20, value=0)
                        fen_y = st.number_input("Fen Bilimleri Yanlış", min_value=0, max_value=20, value=0)
                        st.divider()
                        ing_d = st.number_input("İngilizce Doğru (Maks 10)", min_value=0, max_value=10, value=0)
                        ing_y = st.number_input("İngilizce Yanlış", min_value=0, max_value=10, value=0)
                        
                    lgs_submit = st.form_submit_button("Deneme Sonucunu Veritabanına Kaydet", type="primary", use_container_width=True)
                    
                    if lgs_submit and deneme_adi:
                        if (turkce_d + turkce_y > 20) or (mat_d + mat_y > 20) or (fen_d + fen_y > 20) or (ink_d + ink_y > 10) or (din_d + din_y > 10) or (ing_d + ing_y > 10):
                            st.error("Girdiğiniz doğru ve yanlış sayıları toplamı, ilgili dersin toplam soru sayısını aşamaz!")
                        else:
                            kayit_verisi = {
                                "ogrenci_id": secilen_ogr_id,
                                "deneme_adi": deneme_adi,
                                "turkce_d": turkce_d, "turkce_y": turkce_y,
                                "mat_d": mat_d, "mat_y": mat_y,
                                "fen_d": fen_d, "fen_y": fen_y,
                                "ink_d": ink_d, "ink_y": ink_y,
                                "din_d": din_d, "din_y": din_y,
                                "ing_d": ing_d, "ing_y": ing_y
                            }
                            supabase.table("lgs_denemeleri").insert(kayit_verisi).execute()
                            st.success(f"{secilen_ogr_lgs} için {deneme_adi} verileri başarıyla kaydedildi.")
                            st.rerun()

            with tab_lgs2:
                secilen_ogr_analiz = st.selectbox("Öğrenci Seçin", list(ogr_secenekleri.keys()), key="lgs_ogr_secim_analiz")
                secilen_ogr_id_analiz = ogr_secenekleri[secilen_ogr_analiz]
                
                lgs_res = supabase.table("lgs_denemeleri").select("*").eq("ogrenci_id", secilen_ogr_id_analiz).execute()
                
                if not lgs_res.data:
                    st.info("Bu öğrenciye ait henüz LGS deneme sınavı verisi bulunmamaktadır.")
                else:
                    df_lgs = pd.DataFrame(lgs_res.data)
                    
                    # Net Formülleri (Doğru - Yanlış / 3)
                    df_lgs["Türkçe Net"] = df_lgs["turkce_d"] - (df_lgs["turkce_y"] / 3)
                    df_lgs["Matematik Net"] = df_lgs["mat_d"] - (df_lgs["mat_y"] / 3)
                    df_lgs["Fen Net"] = df_lgs["fen_d"] - (df_lgs["fen_y"] / 3)
                    df_lgs["İnkılap Net"] = df_lgs["ink_d"] - (df_lgs["ink_y"] / 3)
                    df_lgs["Din Net"] = df_lgs["din_d"] - (df_lgs["din_y"] / 3)
                    df_lgs["İngilizce Net"] = df_lgs["ing_d"] - (df_lgs["ing_y"] / 3)
                    
                    df_lgs["Toplam Net"] = df_lgs["Türkçe Net"] + df_lgs["Matematik Net"] + df_lgs["Fen Net"] + df_lgs["İnkılap Net"] + df_lgs["Din Net"] + df_lgs["İngilizce Net"]
                    
                    st.write("### 📈 Toplam Net Gelişim Grafiği")
                    df_grafik_tot = df_lgs[["deneme_adi", "Toplam Net"]].set_index("deneme_adi")
                    st.line_chart(df_grafik_tot, use_container_width=True)
                    
                    st.write("### 📊 Ders Bazlı Net Gelişimi")
                    df_grafik_dersler = df_lgs[["deneme_adi", "Türkçe Net", "Matematik Net", "Fen Net", "İnkılap Net", "Din Net", "İngilizce Net"]].set_index("deneme_adi")
                    st.line_chart(df_grafik_dersler, use_container_width=True)
                    
                    st.write("### 📋 Deneme Sonuçları Detay Tablosu")
                    df_tablo_gosterim = df_lgs[["deneme_adi", "Türkçe Net", "Matematik Net", "Fen Net", "İnkılap Net", "Din Net", "İngilizce Net", "Toplam Net"]].rename(columns={"deneme_adi": "Deneme Sınavı"})
                    st.dataframe(df_tablo_gosterim, hide_index=True, use_container_width=True)

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
                    for i in range(1, 9): # 8 adet deneme sınavı simüle ediliyor
                        lgs_data.append({
                            "ogrenci_id": ogr_id,
                            "deneme_adi": f"Deneme {i}",
                            "turkce_d": random.randint(12, 20), "turkce_y": random.randint(0, 5),
                            "mat_d": random.randint(6, 20), "mat_y": random.randint(0, 8),
                            "fen_d": random.randint(12, 20), "fen_y": random.randint(0, 5),
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
