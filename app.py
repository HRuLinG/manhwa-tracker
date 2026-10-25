import streamlit as st
import json
import requests
import gspread
from google.oauth2.service_account import Credentials

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Manga & Webtoon Tracker", page_icon="🌌", layout="wide")

st.markdown("""
    <style>
    .gradient-text { font-weight: bold; background: -webkit-linear-gradient(45deg, #ff4b4b, #ff8f00); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2.5em; text-align: center; margin-bottom: 20px; }
    .stButton>button { border-radius: 20px; transition: all 0.3s ease; border: 1px solid #ff4b4b; }
    .stButton>button:hover { transform: scale(1.05); box-shadow: 0px 4px 15px rgba(255, 75, 75, 0.4); border: 1px solid #ff8f00; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# GOOGLE SHEETS VERİTABANI BAĞLANTISI (GÜÇLENDİRİLDİ)
# ==========================================
@st.cache_resource
def sheets_baglantisi_kur():
    try:
        # Telefondan kopyalarken oluşan fiziksel satır atlamalarını temizleyen zırh
        ham_veri = st.secrets["GOOGLE_JSON"]
        temiz_veri = ham_veri.replace('\n', '').replace('\r', '')
        json_verisi = json.loads(temiz_veri)
        
        kapsam = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        kimlik = Credentials.from_service_account_info(json_verisi, scopes=kapsam)
        istemci = gspread.authorize(kimlik)
        tablo = istemci.open("ManhwaDB").sheet1
        return tablo
    except Exception as e:
        st.error(f"Veritabanı bağlantı hatası. Detay: {e}")
        return None

tablo = sheets_baglantisi_kur()

def verileri_yukle():
    if not tablo: return {"kullanicilar": {}}
    try:
        kayitlar = tablo.get_all_records()
        veri = {"kullanicilar": {}}
        for satir in kayitlar:
            k_adi = str(satir.get("KullaniciAdi", ""))
            if not k_adi: continue
            sifre = str(satir.get("Sifre", ""))
            seriler_str = str(satir.get("Seriler", "{}"))
            try:
                seriler = json.loads(seriler_str)
            except:
                seriler = {}
            veri["kullanicilar"][k_adi] = {"sifre": sifre, "seriler": seriler}
        return veri
    except:
        return {"kullanicilar": {}}

def kullanici_kaydet(k_adi, sifre, seriler_dict):
    if not tablo: return
    seriler_json = json.dumps(seriler_dict, ensure_ascii=False)
    try:
        hucre = tablo.find(k_adi, in_column=1)
        if hucre is None:
            tablo.append_row([k_adi, sifre, seriler_json])
        else:
            tablo.update_cell(hucre.row, 3, seriler_json)
    except Exception:
        tablo.append_row([k_adi, sifre, seriler_json])

@st.cache_data 
def mangadex_ara(arama_metni):
    url = "https://api.mangadex.org/manga"
    parametreler = {"title": arama_metni, "availableTranslatedLanguage[]": "en", "limit": 10}
    try:
        cevap = requests.get(url, params=parametreler)
        cevap.raise_for_status()
        return cevap.json().get("data", [])
    except:
        return []

if "aktif_hesap" not in st.session_state:
    st.session_state.aktif_hesap = None
if "veri_onbellek" not in st.session_state:
    st.session_state.veri_onbellek = verileri_yukle()

veri = st.session_state.veri_onbellek

# ==========================================
# EKRANLAR
# ==========================================
if st.session_state.aktif_hesap is None:
    st.markdown('<div class="gradient-text">🌌 Manga & Webtoon Tracker</div>', unsafe_allow_html=True)
    st.write("<h5 style='text-align: center; color: gray;'>Her yerden erişilebilir bulut kütüphanen.</h5>", unsafe_allow_html=True)
    st.write("---")
    
    with st.container(border=True):
        sekme1, sekme2 = st.tabs(["🔑 Giriş Yap", "✨ Kayıt Ol"])
        
        with sekme1:
            g_kadi = st.text_input("Kullanıcı Adı", key="login_kadi")
            g_sifre = st.text_input("Şifre", type="password", key="login_sifre")
            if st.button("Giriş Yap", type="primary", use_container_width=True):
                if g_kadi in veri["kullanicilar"] and veri["kullanicilar"][g_kadi]["sifre"] == g_sifre:
                    st.session_state.aktif_hesap = g_kadi
                    st.rerun()
                else:
                    st.error("Kullanıcı adı veya şifre hatalı!")

        with sekme2:
            k_kadi = st.text_input("Yeni Kullanıcı Adı", key="reg_kadi")
            k_sifre = st.text_input("Yeni Şifre", type="password", key="reg_sifre")
            if st.button("Hesap Oluştur", use_container_width=True):
                if k_kadi in veri["kullanicilar"]:
                    st.warning("Bu kullanıcı adı zaten alınmış!")
                elif k_kadi and k_sifre:
                    veri["kullanicilar"][k_kadi] = {"sifre": k_sifre, "seriler": {}}
                    kullanici_kaydet(k_kadi, k_sifre, {})
                    st.success("Hesap oluşturuldu! Sol sekmeden giriş yapabilirsin.")
                else:
                    st.error("Kullanıcı adı ve şifre boş bırakılamaz.")

else:
    hesap = st.session_state.aktif_hesap
    kullanici_verisi = veri["kullanicilar"][hesap]
    
    st.sidebar.markdown(f"## 👤 Hoş Geldin, **{hesap}**")
    st.sidebar.write("---")
    menu = st.sidebar.radio("Navigasyon", ["📊 Profilim", "🔍 Seri Keşfet", "📖 Kütüphanem"], label_visibility="collapsed")
    
    st.sidebar.write("---")
    if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state.aktif_hesap = None
        st.session_state.veri_onbellek = verileri_yukle()
        st.rerun()

    if menu == "📊 Profilim":
        st.markdown('<div class="gradient-text" style="font-size: 2em; text-align: left;">İstatistiklerin</div>', unsafe_allow_html=True)
        toplam_bolum = sum(len(d.get("okunanlar", [])) for d in kullanici_verisi["seriler"].values())
        toplam_seri = len(kullanici_verisi["seriler"])
        
        m1, m2 = st.columns(2)
        with m1:
            with st.container(border=True):
                st.metric(label="📚 Takip Edilen Seri", value=toplam_seri)
        with m2:
            with st.container(border=True):
                st.metric(label="✅ Okunan Toplam Bölüm", value=toplam_bolum)
                
        with st.container(border=True):
            seviye = "Yeni Okuyucu" if toplam_bolum < 100 else ("Kıdemli Okuyucu" if toplam_bolum < 500 else "Manga Ustası")
            st.metric(label="🏆 Mevcut Seviye", value=seviye)

        st.write("### 📌 Hızlı Bakış")
        if not kullanici_verisi["seriler"]:
            st.info("Henüz okumaya başlamadın.")
        else:
            for seri_adi, detaylar in kullanici_verisi["seriler"].items():
                okunan = len(detaylar.get("okunanlar", []))
                st.progress(min(okunan / 200, 1.0), text=f"{seri_adi} - {okunan} Bölüm")

    elif menu == "🔍 Seri Keşfet":
        st.title("🔍 Yeni Seriler Keşfet")
        arama = st.text_input("Manga, Manhwa veya Webtoon adı girin:")
        
        if st.button("MangaDex'te Ara 🌍", type="primary", use_container_width=True):
            if arama:
                with st.spinner("Aranıyor..."):
                    sonuclar = mangadex_ara(arama)
                    if sonuclar:
                        for seri in sonuclar:
                            baslik_dict = seri["attributes"]["title"]
                            baslik = baslik_dict.get("en", list(baslik_dict.values())[0])
                            
                            with st.container(border=True):
                                st.subheader(f"📖 {baslik}")
                                if st.button("Kütüphaneme Ekle ➕", key=f"btn_{seri['id']}", use_container_width=True):
                                    if baslik not in kullanici_verisi["seriler"]:
                                        kullanici_verisi["seriler"][baslik] = {"okunanlar": []}
                                        kullanici_kaydet(hesap, kullanici_verisi["sifre"], kullanici_verisi["seriler"])
                                        st.toast(f"**{baslik}** eklendi!", icon="🎉")
                                    else:
                                        st.toast("Zaten kütüphanende var!", icon="⚠️")
                    else:
                        st.warning("Sonuç bulunamadı.")
                        
    elif menu == "📖 Kütüphanem":
        st.title("📖 Kişisel Kütüphanem")
        
        if not kullanici_verisi["seriler"]:
            st.info("Kütüphanen şu an boş.")
        else:
            secilen_seri = st.selectbox("Seriyi seç:", list(kullanici_verisi["seriler"].keys()))
            
            if secilen_seri:
                st.write("---")
                with st.container(border=True):
                    st.markdown(f"### 🔖 {secilen_seri}")
                    baslangic = st.number_input("Sayfa Başlangıcı:", min_value=1, value=1, step=50)
                    
                    bitis = baslangic + 49
                    okunan_listesi = kullanici_verisi["seriler"][secilen_seri].get("okunanlar", [])
                    
                    st.write("#### Bölüm Listesi")
                    
                    sutunlar = st.columns(4) 
                    degisiklik = False
                    
                    for bolum_no in range(baslangic, bitis + 1):
                        sutun_indeksi = (bolum_no - baslangic) % 4
                        with sutunlar[sutun_indeksi]:
                            okunmus_mu = bolum_no in okunan_listesi
                            isaret = st.checkbox(f"{bolum_no}", value=okunmus_mu, key=f"chk_{secilen_seri}_{bolum_no}")
                            
                            if isaret and not okunmus_mu:
                                okunan_listesi.append(bolum_no)
                                degisiklik = True
                            elif not isaret and okunmus_mu:
                                okunan_listesi.remove(bolum_no)
                                degisiklik = True
                    
                    if degisiklik:
                        kullanici_verisi["seriler"][secilen_seri]["okunanlar"] = list(set(okunan_listesi))
                        kullanici_kaydet(hesap, kullanici_verisi["sifre"], kullanici_verisi["seriler"])
                        st.toast("Buluta kaydedildi! ☁️", icon="✅")
