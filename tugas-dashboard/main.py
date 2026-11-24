"""Flower Dashboard: simulasi 1 server, 3 klien (Streamlit, Python murni)."""
import math
import random
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Flower Dashboard", page_icon="🌼", layout="wide")

WIB = timezone(timedelta(hours=7))
SERVER = {"x": 520, "y": 195}
CLIENTS = [
    {"id": 1, "name": "Klien 1", "x": 110, "y": 70, "color": "#6fa8ff", "n": 4200},
    {"id": 2, "name": "Klien 2", "x": 110, "y": 195, "color": "#2ee6c9", "n": 5100},
    {"id": 3, "name": "Klien 3", "x": 110, "y": 320, "color": "#ff9a6b", "n": 3700},
]
SPEED = {"Lambat": 1.6, "Normal": 1.0, "Cepat": 0.5}

st.markdown("""
<style>
#MainMenu, footer {visibility: hidden;}
.hero {background: linear-gradient(120deg, #1b1240, #3b1d7a 60%, #e0307f);
       padding: 22px 28px; border-radius: 18px; margin-bottom: 14px;
       box-shadow: 0 14px 30px -18px rgba(60,30,140,.8);}
.hero h1 {margin: 0; font-size: 2rem; color: #fff; padding: 0;}
.hero p {margin: 6px 0 0; color: #e7defc; font-size: 1rem;}
[data-testid="stMetric"] {background: #fff; border: 1px solid #e3dcf7; border-left: 6px solid #e0307f;
       border-radius: 14px; padding: 12px 16px; box-shadow: 0 8px 20px -14px rgba(70,40,160,.55);}
[data-testid="stMetricLabel"], [data-testid="stMetricValue"] {color: #1e1537;}
section[data-testid="stSidebar"] .stButton > button,
section[data-testid="stSidebar"] .stDownloadButton > button {width: 100%; border-radius: 10px;}
.stButton > button[kind="primary"] {background: #e0307f; border: 0; color: #fff; font-weight: 700;}
button[role="tab"] {font-size: 1rem;}
</style>
<div class="hero"><h1>🌼 Flower Dashboard</h1>
<p>Simulasi federated learning: 1 server dan 3 klien saling bertukar model tanpa membagikan data.
Angka akurasi dan loss adalah simulasi, bukan hasil pelatihan sungguhan.</p></div>
""", unsafe_allow_html=True)


def g_acc(r):
    return min(0.86, 0.1 + 0.72 * (1 - math.exp(-r / 3.6)))


def g_loss(r):
    return 0.35 + 1.95 * math.exp(-r / 3.2)


def new_state():
    return {
        "phase": "Siap. Tekan Mulai di panel kiri.",
        "st": {c["id"]: "idle" for c in CLIENTS},
        "pg": {c["id"]: 0.0 for c in CLIENTS},
        "tl": {c["id"]: None for c in CLIENTS},
        "ea": {c["id"]: None for c in CLIENTS},
        "srv": "FedAvg", "hot": set(), "srv_hot": False, "pk": [],
    }


def topo_svg(S):
    o = ['<svg viewBox="0 0 640 440" xmlns="http://www.w3.org/2000/svg" '
         'style="width:100%;border-radius:18px;font-family:sans-serif">'
         '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
         '<stop offset="0" stop-color="#1b1240"/><stop offset="1" stop-color="#2e1a68"/></linearGradient>'
         '<radialGradient id="sun" cx="0.5" cy="0.5" r="0.5">'
         '<stop offset="0" stop-color="#ffc93c" stop-opacity="0.35"/>'
         '<stop offset="1" stop-color="#ffc93c" stop-opacity="0"/></radialGradient>'
         '<filter id="glow"><feGaussianBlur stdDeviation="3" result="b"/>'
         '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
         '<rect width="640" height="440" fill="url(#bg)"/>'
         f'<circle cx="{SERVER["x"]}" cy="{SERVER["y"]}" r="150" fill="url(#sun)"/>']
    for c in CLIENTS:
        o.append(f'<line x1="{c["x"]+36}" y1="{c["y"]}" x2="{SERVER["x"]-48}" y2="{SERVER["y"]}" '
                 'stroke="#4a3b8a" stroke-width="2" stroke-dasharray="4 5"/>')
    for c in CLIENTS:
        hot = c["id"] in S["hot"]
        fl = ' filter="url(#glow)"' if hot else ""
        o.append(f'<circle cx="{c["x"]}" cy="{c["y"]}" r="34" fill="#1b1240" stroke="{c["color"]}" '
                 f'stroke-width="{6 if hot else 3}"{fl}/>')
        o.append(f'<text x="{c["x"]}" y="{c["y"]+8}" text-anchor="middle" font-size="22">📱</text>')
        o.append(f'<text x="{c["x"]}" y="{c["y"]+54}" text-anchor="middle" fill="#f3efff" font-size="13" font-weight="bold">{c["name"]}</text>')
        o.append(f'<text x="{c["x"]}" y="{c["y"]+69}" text-anchor="middle" fill="#a79ccf" font-size="11">{S["st"][c["id"]]}</text>')
        o.append(f'<rect x="{c["x"]-35}" y="{c["y"]+76}" width="70" height="5" rx="2.5" fill="#3a2f6b"/>')
        o.append(f'<rect x="{c["x"]-35}" y="{c["y"]+76}" width="{70*S["pg"][c["id"]]:.1f}" height="5" rx="2.5" fill="{c["color"]}"/>')
    fl = ' filter="url(#glow)"' if S["srv_hot"] else ""
    o.append(f'<rect x="{SERVER["x"]-48}" y="{SERVER["y"]-48}" width="96" height="96" rx="20" fill="#1b1240" '
             f'stroke="#ffc93c" stroke-width="{6 if S["srv_hot"] else 4}"{fl}/>')
    o.append(f'<text x="{SERVER["x"]}" y="{SERVER["y"]+11}" text-anchor="middle" font-size="32">🌼</text>')
    o.append(f'<text x="{SERVER["x"]}" y="{SERVER["y"]+72}" text-anchor="middle" fill="#f3efff" font-size="13" font-weight="bold">SuperLink + ServerApp</text>')
    o.append(f'<text x="{SERVER["x"]}" y="{SERVER["y"]+88}" text-anchor="middle" fill="#a79ccf" font-size="11">{S["srv"]}</text>')
    for x, y, color, label in S["pk"]:
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="{color}" stroke="#fff" stroke-width="2" filter="url(#glow)"/>')
        o.append(f'<text x="{x:.1f}" y="{y-14:.1f}" text-anchor="middle" fill="#f3efff" font-size="10">{label}</text>')
    for cx, col, txt in [(170, "#ffc93c", "model / eval dari server"), (330, "#6fa8ff", "Δw dari klien"), (430, "#2ee6c9", "metrik")]:
        o.append(f'<circle cx="{cx}" cy="428" r="5" fill="{col}"/>')
        o.append(f'<text x="{cx+10}" y="432" fill="#a79ccf" font-size="11">{txt}</text>')
    o.append("</svg>")
    return "".join(o)


def run(total, speed):
    S = new_state()
    hist, logs = [], []
    dt = 0.04 * speed

    def log(msg):
        logs.append(f"{datetime.now(WIB).strftime('%H:%M:%S')}  {msg}")
        log_ph.markdown("\n".join(f"- {m}" for m in reversed(logs[-8:])))

    def draw():
        phase_ph.markdown(f"**{S['phase']}**")
        topo_ph.markdown(topo_svg(S), unsafe_allow_html=True)

    def draw_table():
        df = pd.DataFrame([{"Node": c["name"], "Status": S["st"][c["id"]],
                            "Progres": int(S["pg"][c["id"]] * 100), "Data": c["n"],
                            "Train loss": S["tl"][c["id"]], "Eval acc (%)": S["ea"][c["id"]]}
                           for c in CLIENTS])
        tbl_ph.dataframe(df, hide_index=True, column_config={
            "Progres": st.column_config.ProgressColumn("Progres", min_value=0, max_value=100, format="%d%%"),
        })

    def move(specs, steps=14):
        for i in range(steps + 1):
            t = i / steps
            e = 2 * t * t if t < .5 else 1 - (-2 * t + 2) ** 2 / 2
            S["pk"] = [(a["x"] + (b["x"] - a["x"]) * e, a["y"] + (b["y"] - a["y"]) * e, col, lab)
                       for a, b, col, lab in specs]
            draw()
            time.sleep(dt)
        S["pk"] = []

    draw(); draw_table()
    for r in range(1, total + 1):
        s_round.metric("Ronde", f"{r}/{total}")
        log(f"Ronde {r} dimulai")

        S["phase"] = f"Ronde {r}: server mengirim bobot global ke klien"
        S["srv_hot"] = True
        for c in CLIENTS:
            S["st"][c["id"]], S["pg"][c["id"]] = "menerima", 0.0
        move([(SERVER, c, "#ffc93c", "model") for c in CLIENTS])
        S["srv_hot"] = False

        S["phase"] = f"Ronde {r}: klien melatih model pada data lokal"
        ratios = [0.75, 1.0, 0.65]
        steps = 40
        for k in range(1, steps + 1):
            for c, ra in zip(CLIENTS, ratios):
                p = min(1.0, k / (steps * ra))
                S["pg"][c["id"]] = p
                S["st"][c["id"]] = "training" if p < 1 else "selesai"
            S["hot"] = {c["id"] for c in CLIENTS if S["pg"][c["id"]] < 1}
            draw()
            if k % 5 == 0:
                draw_table()
            time.sleep(dt * 1.2)
        S["hot"] = set()
        for i, c in enumerate(CLIENTS):
            c["loss"] = g_loss(r - 1) + 0.12 * (i - 1) + random.uniform(-.06, .06)
            S["tl"][c["id"]] = round(c["loss"], 3)
        draw_table()
        log("Semua klien selesai training")

        S["phase"] = f"Ronde {r}: klien mengirim pembaruan bobot (Δw) ke server"
        move([(c, SERVER, c["color"], "Δw") for c in CLIENTS])

        S["phase"] = f"Ronde {r}: server menggabungkan bobot dengan FedAvg"
        S["srv"], S["srv_hot"] = "mengagregasi…", True
        tot = sum(c["n"] for c in CLIENTS)
        log("FedAvg: bobot " + " / ".join(f"{c['n']/tot:.0%}" for c in CLIENTS))
        draw(); time.sleep(1.1 * speed)
        S["srv"], S["srv_hot"] = "FedAvg", False

        S["phase"] = f"Ronde {r}: server meminta evaluasi model global"
        move([(SERVER, c, "#ffc93c", "eval") for c in CLIENTS])
        for c in CLIENTS:
            S["st"][c["id"]] = "evaluasi"
        draw(); time.sleep(0.9 * speed)
        accs = [max(0, g_acc(r) + random.uniform(-.015, .015) + .01 * (i - 1)) for i in range(3)]
        for c, a in zip(CLIENTS, accs):
            S["ea"][c["id"]] = round(a * 100, 1)
        move([(c, SERVER, "#2ee6c9", "metrik") for c in CLIENTS])
        for c in CLIENTS:
            S["st"][c["id"]] = "idle"

        acc = sum(a * c["n"] for a, c in zip(accs, CLIENTS)) / tot
        loss = sum(c["loss"] * c["n"] for c in CLIENTS) / tot
        hist.append({"Ronde": r, "Akurasi global (%)": round(acc * 100, 1)})
        s_acc.metric("Akurasi global", f"{acc*100:.1f}%")
        s_loss.metric("Loss global", f"{loss:.3f}")
        chart_ph.line_chart(pd.DataFrame(hist).set_index("Ronde"), color="#e0307f")
        draw_table()
        log(f"Ronde {r} selesai: akurasi global {acc*100:.1f}%")

    S["phase"] = f"Selesai: {total} ronde. Model akhir disimpan sebagai final_model.keras"
    draw()
    st.balloons()


with st.sidebar:
    st.header("⚙️ Pengaturan")
    total = st.slider("Jumlah ronde", 1, 50, 8)
    speed = SPEED[st.radio("Kecepatan", list(SPEED), index=1, horizontal=True)]
    start = st.button("▶ Mulai", type="primary")
    st.button("⟲ Reset")
    st.caption("Mengubah pengaturan saat berjalan akan mengulang simulasi dari awal.")

    st.divider()
    st.subheader("📄 Dokumen")
    docs_dir = Path(__file__).parent / "docs"
    word_files = sorted(docs_dir.glob("*.docx")) if docs_dir.exists() else []
    if word_files:
        f = word_files[0]
        st.download_button(
            "Unduh dokumen diagram (Word)",
            f.read_bytes(),
            file_name=f.name,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    else:
        st.caption("File Word belum ditemukan di folder docs.")

tab_sim, tab_info = st.tabs(["🌼 Simulasi", "📘 Penjelasan"])

with tab_sim:
    left, right = st.columns([3, 2])
    with left:
        st.subheader("Alur komunikasi")
        phase_ph = st.empty()
        topo_ph = st.empty()
    with right:
        st.subheader("Status run")
        c1, c2, c3 = st.columns(3)
        s_round, s_acc, s_loss = c1.empty(), c2.empty(), c3.empty()
        s_round.metric("Ronde", f"0/{total}")
        s_acc.metric("Akurasi global", "–")
        s_loss.metric("Loss global", "–")
        st.subheader("Akurasi per ronde")
        chart_ph = st.empty()
    st.subheader("Node (SuperNode)")
    tbl_ph = st.empty()
    st.subheader("Log")
    log_ph = st.empty()

with tab_info:
    st.subheader("Apa yang terjadi di simulasi ini?")
    st.markdown(
        "Bayangkan 3 anak belajar menggambar kucing di rumah masing-masing, dan 1 guru "
        "mengumpulkan **cerita belajar** mereka, bukan gambarnya. Itulah *federated learning*."
    )
    st.markdown(
        "- **model**: server mengirim otak terbaru ke klien\n"
        "- **Δw**: klien mengirim perubahan hasil belajarnya\n"
        "- **FedAvg**: server merata-rata perubahan, lebih berat untuk klien yang datanya lebih banyak\n"
        "- **eval / metrik**: server meminta tes, klien melapor nilainya"
    )
    with st.expander("Apakah angkanya asli?"):
        st.write("Bukan. Akurasi dan loss dihitung dengan rumus kurva belajar agar animasinya mudah dipahami. "
                 "Pelatihan sungguhan ada di proyek Flower + TensorFlow (`flwr run`).")

if start:
    run(total, speed)
else:
    S0 = new_state()
    phase_ph.markdown(f"**{S0['phase']}**")
    topo_ph.markdown(topo_svg(S0), unsafe_allow_html=True)
