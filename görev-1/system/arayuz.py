# Operator arayuzu (Streamlit). Calistirmak icin: streamlit run arayuz.py
import os
import glob
import sys

import streamlit as st
import pandas as pd
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(__file__))
from denetim.cekirdek import Template, list_templates, inspect, imread_u

BASE_DIR = os.path.dirname(__file__)
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

st.set_page_config(page_title="Kutu Dizilim Kontrolü", layout="wide")


if "threshold" not in st.session_state:
    st.session_state.threshold = 0.60


def bgr_to_rgb(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def load_upload_as_bgr(uploaded_file) -> np.ndarray:
    data = np.frombuffer(uploaded_file.getvalue(), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


@st.cache_resource(show_spinner=False)
def get_template(name: str) -> Template:
    return Template.load(os.path.join(TEMPLATES_DIR, name))  # ayni sablonu tekrar tekrar diskten okumamak icin cache'le


def status_badge(status: str) -> str:
    return {"OK": "OK", "ROTATED": "Döndürülmüş", "SWAPPED": "Yer değişmiş",
            "MISMATCH": "Tanınmadı"}.get(status, status)


st.title("Kutu Dizilim Doğrulama")

templates = list_templates(TEMPLATES_DIR)
if not templates:
    st.error("Hiç referans şablon bulunamadı. Önce `kalibrasyon.py` ile bir model kalibre edin.")
    st.stop()

with st.sidebar:
    st.header("Ürün Modeli")
    model = st.selectbox("Referans şablon", templates, index=0)
    tpl = get_template(model)
    st.image(bgr_to_rgb(tpl.ref_image), caption=f"{model} referansı ({len(tpl.boxes)} kutu)",
              use_container_width=True)
    st.divider()
    st.header("Hassasiyet")
    st.session_state.threshold = st.slider(
        "Eşik değeri", min_value=0.30, max_value=0.90,
        value=st.session_state.threshold, step=0.01,
        help="Bir kutunun 'doğru' sayılması için referansla ne kadar benzemesi gerektiği.")
    st.caption(
        "**Yüksek değer** → sistem daha sıkı davranır; şüpheli kutuları NOK sayar "
        "(hatalı bir paketi yanlışlıkla onaylama riski azalır, ama iyi bir paketi "
        "gereksiz yere reddetme riski artar).\n\n"
        "**Düşük değer** → sistem daha toleranslıdır (ışık/gölge farklarına karşı "
        "daha hoşgörülü, ama gerçek bir hatayı kaçırma riski artar)."
    )
threshold = st.session_state.threshold

tab1, tab2 = st.tabs(["Tekli Kontrol", "Toplu Kontrol"])

with tab1:
    col_in, col_out = st.columns([1, 1.4])
    with col_in:
        src = st.radio("Görüntü kaynağı", ["Dosyadan yükle", "Kameradan çek"], horizontal=True)
        img_bgr = None
        if src == "Dosyadan yükle":
            up = st.file_uploader("Kontrol edilecek fotoğraf", type=["jpg", "jpeg", "png", "bmp"])
            if up is not None:
                img_bgr = load_upload_as_bgr(up)
        else:
            cam = st.camera_input("Fotoğraf çek")
            if cam is not None:
                img_bgr = load_upload_as_bgr(cam)
        if img_bgr is not None:
            st.image(bgr_to_rgb(img_bgr), caption="Girdi", use_container_width=True)

    with col_out:
        if img_bgr is not None:
            with st.spinner("Kontrol ediliyor..."):
                result = inspect(tpl, img_bgr, threshold=threshold)  # asıl kontrol burada yapiliyor
            if result.error:
                st.error(f"Kontrol yapılamadı: {result.error}")
            else:
                if result.ok:
                    st.success("## UYGUN (OK)")
                else:
                    bad = [b for b in result.boxes if b.status != "OK"]
                    st.error(f"## UYGUNSUZ (NOK) — {len(bad)} hatalı kutu")
                st.image(bgr_to_rgb(result.annotated), caption="Sonuç (kırmızı = hatalı kutu)",
                          use_container_width=True)
                with st.expander("Kutu bazlı detay"):
                    df = pd.DataFrame([{
                        "Kutu": b.id, "Durum": status_badge(b.status),
                        "Benzerlik": round(b.score, 3),
                        "Açıklama": b.detail,
                    } for b in result.boxes])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                st.caption(f"Hizalama: {result.align_message}")
        else:
            st.info("Soldan bir fotoğraf yükleyin veya kamerayla çekin.")

with tab2:
    st.write("Bir klasördeki tüm görüntüleri tek seferde işleyin.")
    folder = st.text_input("Klasör yolu", value="")
    run = st.button("Klasördeki tüm görüntüleri işle", type="primary", disabled=not folder)

    if run:
        exts = ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.JPG", "*.JPEG", "*.PNG")
        files = []
        for e in exts:
            files.extend(glob.glob(os.path.join(folder, "**", e), recursive=True))  # alt klasorler dahil tum resimler
        files = sorted(set(files))
        if not files:
            st.warning("Klasörde görüntü bulunamadı.")
        else:
            progress = st.progress(0.0, text=f"0/{len(files)}")
            rows = []              # tabloya yazilacak sonuc satirlari
            annotated_cache = {}   # isaretli goruntuler (sonradan gostermek icin)
            for i, f in enumerate(files):
                img = imread_u(f)
                if img is None:
                    rows.append({"Dosya": os.path.basename(f), "Sonuç": "OKUNAMADI",
                                 "Hatalı Kutular": "-"})
                else:
                    res = inspect(tpl, img, threshold=threshold)  # her goruntu tek tek kontrol edilir
                    if res.error:
                        rows.append({"Dosya": os.path.basename(f), "Sonuç": "HİZALAMA HATASI",
                                     "Hatalı Kutular": res.error})
                    else:
                        bad = [f"{b.id}({b.status})" for b in res.boxes if b.status != "OK"]
                        rows.append({
                            "Dosya": os.path.basename(f),
                            "Sonuç": "OK" if res.ok else "NOK",
                            "Hatalı Kutular": ", ".join(bad) if bad else "-",
                        })
                        annotated_cache[f] = res.annotated
                progress.progress((i + 1) / len(files), text=f"{i+1}/{len(files)}")

            df = pd.DataFrame(rows)
            n_ok = (df["Sonuç"] == "OK").sum()
            n_total = len(df)
            c1, c2, c3 = st.columns(3)
            c1.metric("Toplam görüntü", n_total)
            c2.metric("UYGUN (OK)", int(n_ok))
            c3.metric("UYGUNSUZ / HATA", int(n_total - n_ok))

            st.dataframe(df, use_container_width=True, hide_index=True)
            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("Raporu CSV olarak indir", csv, file_name="kontrol_raporu.csv")

            bad_files = [f for f in files if f in annotated_cache and
                         df.loc[df["Dosya"] == os.path.basename(f), "Sonuç"].iloc[0] == "NOK"]
            if bad_files:
                st.subheader("Uygunsuz (NOK) görüntüler")
                cols = st.columns(3)
                for i, f in enumerate(bad_files):
                    with cols[i % 3]:
                        st.image(bgr_to_rgb(annotated_cache[f]), caption=os.path.basename(f),
                                  use_container_width=True)
