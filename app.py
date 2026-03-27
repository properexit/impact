import streamlit as st
import json
import os
import re
import folium
import folium.plugins
from streamlit_folium import st_folium
from main import main
from report_pdf import generate_pdf

# ── MUST be first Streamlit call ──────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="Geo Due Diligence AI",
    page_icon="🧠",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Reset & base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: #e2e8f0;
}
.stApp { background: #080c14; }
.block-container {
    padding: 1.5rem 2rem 4rem !important;
    max-width: 1400px !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }

/* ── App header ── */
.geo-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 24px;
    background: #0d1117;
    border: 1px solid #1e2a3a;
    border-radius: 12px;
    margin-bottom: 20px;
}
.geo-header-left { display: flex; align-items: center; gap: 14px; }
.geo-header-icon {
    width: 40px; height: 40px;
    background: linear-gradient(135deg, #1e40af, #3b82f6);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; line-height: 1;
}
.geo-header h1 {
    margin: 0; font-size: 18px; font-weight: 600;
    color: #f0f6fc; letter-spacing: -0.4px;
}
.geo-header p { margin: 0; font-size: 12px; color: #5c7a9e; }
.geo-header-badge {
    font-size: 11px; font-weight: 500; color: #58a6ff;
    background: #0d2142; border: 1px solid #1e40af;
    padding: 4px 10px; border-radius: 20px; letter-spacing: 0.3px;
}

/* ── Panel cards ── */
.panel {
    background: #0d1117;
    border: 1px solid #1e2a3a;
    border-radius: 12px;
    padding: 16px;
    height: 100%;
}
.panel-label {
    font-size: 10px; font-weight: 600; color: #3b82f6;
    text-transform: uppercase; letter-spacing: 1.2px;
    margin-bottom: 10px; padding-bottom: 8px;
    border-bottom: 1px solid #1e2a3a;
}

/* ── Streamlit metric override ── */
div[data-testid="stMetric"] {
    background: #111827 !important;
    border: 1px solid #1e2a3a !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
}
div[data-testid="stMetricLabel"] p { color: #5c7a9e !important; font-size: 11px !important; }
div[data-testid="stMetricValue"] { color: #e2e8f0 !important; font-size: 20px !important; font-weight: 500 !important; }

/* ── Buttons ── */
.stButton > button {
    background: #1e40af !important;
    color: #eff6ff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    padding: 10px 0 !important;
    width: 100% !important;
    letter-spacing: 0.2px !important;
    transition: background 0.15s !important;
}
.stButton > button:hover { background: #2563eb !important; }
.stDownloadButton > button {
    background: #166534 !important;
    color: #dcfce7 !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    padding: 10px 0 !important;
    width: 100% !important;
}
.stDownloadButton > button:hover { background: #16a34a !important; }

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #111827 !important;
    border: 1px dashed #1e3a5f !important;
    border-radius: 8px !important;
    padding: 8px !important;
}
[data-testid="stFileUploader"] label { color: #5c7a9e !important; font-size: 12px !important; }

/* ── Status widget ── */
[data-testid="stStatusWidget"] {
    background: #0d1117 !important;
    border: 1px solid #1e2a3a !important;
    border-radius: 10px !important;
}

/* ── Alerts ── */
.stSuccess { background: #052e16 !important; border: 1px solid #166534 !important; color: #4ade80 !important; border-radius: 8px !important; }
.stInfo    { background: #0c1a2e !important; border: 1px solid #1e3a5f !important; color: #60a5fa !important; border-radius: 8px !important; }
.stWarning { background: #1c0f00 !important; border: 1px solid #92400e !important; color: #fbbf24 !important; border-radius: 8px !important; }
.stError   { background: #1c0505 !important; border: 1px solid #7f1d1d !important; color: #f87171 !important; border-radius: 8px !important; }

/* ── Expander ── */
details {
    background: #0d1117 !important;
    border: 1px solid #1e2a3a !important;
    border-radius: 8px !important;
}
summary { color: #5c7a9e !important; font-size: 13px !important; }

/* ── Divider ── */
hr { border-color: #1e2a3a !important; margin: 24px 0 !important; }

/* ── Risk dashboard ── */
.risk-dashboard {
    display: grid;
    grid-template-columns: 200px 1fr 1fr;
    gap: 12px;
    margin-bottom: 20px;
}

.risk-score-card {
    background: #0d1117;
    border: 1px solid #1e2a3a;
    border-radius: 12px;
    padding: 20px;
    display: flex; flex-direction: column; justify-content: center;
    position: relative; overflow: hidden;
}
.risk-score-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 3px;
}
.risk-low::before  { background: linear-gradient(90deg, #16a34a, #4ade80); }
.risk-med::before  { background: linear-gradient(90deg, #d97706, #fbbf24); }
.risk-high::before { background: linear-gradient(90deg, #dc2626, #f87171); }

.risk-score-label {
    font-size: 10px; font-weight: 600; color: #5c7a9e;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px;
}
.risk-score-number {
    font-size: 52px; font-weight: 700; line-height: 1;
    font-family: 'JetBrains Mono', monospace; letter-spacing: -2px;
}
.risk-low  .risk-score-number { color: #4ade80; }
.risk-med  .risk-score-number { color: #fbbf24; }
.risk-high .risk-score-number { color: #f87171; }

.risk-score-denom {
    font-size: 18px; font-weight: 400;
    color: #374151; font-family: 'JetBrains Mono', monospace;
}
.risk-pill {
    display: inline-flex; align-items: center; gap: 5px;
    margin-top: 10px; padding: 4px 10px;
    border-radius: 20px; font-size: 11px; font-weight: 600;
    letter-spacing: 0.5px; width: fit-content;
}
.risk-low  .risk-pill { background: #052e16; color: #4ade80; border: 1px solid #166534; }
.risk-med  .risk-pill { background: #1c0f00; color: #fbbf24; border: 1px solid #92400e; }
.risk-high .risk-pill { background: #1c0505; color: #f87171; border: 1px solid #7f1d1d; }

/* ── Location card ── */
.location-card {
    background: #0d1117;
    border: 1px solid #1e2a3a;
    border-radius: 12px;
    padding: 20px;
}
.loc-row { margin-bottom: 14px; }
.loc-row:last-child { margin-bottom: 0; }
.loc-key {
    font-size: 10px; font-weight: 600; color: #3b82f6;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 3px;
}
.loc-val { font-size: 16px; font-weight: 500; color: #e2e8f0; }
.loc-coords {
    font-size: 13px; color: #5c7a9e;
    font-family: 'JetBrains Mono', monospace; letter-spacing: 0.5px;
}

/* ── Flags panel ── */
.flags-card {
    background: #0d1117;
    border: 1px solid #1e2a3a;
    border-radius: 12px;
    padding: 20px;
    display: flex; flex-direction: column; gap: 8px;
}
.flags-card-title {
    font-size: 10px; font-weight: 600; color: #5c7a9e;
    text-transform: uppercase; letter-spacing: 1px;
    margin-bottom: 6px;
}
.flag-row {
    display: flex; align-items: flex-start; gap: 10px;
    padding: 10px 12px; border-radius: 8px;
    font-size: 13px; line-height: 1.5;
}
.flag-row.critical {
    background: #1c0505; border: 1px solid #7f1d1d;
    color: #fca5a5;
}
.flag-row.warning {
    background: #1c0f00; border: 1px solid #78350f;
    color: #fcd34d;
}
.flag-row.clear {
    background: #052e16; border: 1px solid #166534;
    color: #86efac;
}
.flag-icon { flex-shrink: 0; margin-top: 1px; font-size: 14px; }

/* ── Sections ── */
.sections-wrapper {
    background: #0d1117;
    border: 1px solid #1e2a3a;
    border-radius: 12px;
    overflow: hidden;
    margin-top: 20px;
}
.sections-header {
    display: flex; align-items: center; gap: 0;
    border-bottom: 1px solid #1e2a3a;
    overflow-x: auto; padding: 0 4px;
    background: #080c14;
}
.tab-btn {
    padding: 12px 16px; font-size: 12px; font-weight: 500;
    color: #5c7a9e; cursor: pointer; white-space: nowrap;
    border-bottom: 2px solid transparent;
    transition: color 0.15s, border-color 0.15s;
    user-select: none;
}
.tab-btn:hover { color: #93c5fd; }
.tab-btn.active { color: #58a6ff; border-bottom-color: #3b82f6; }

.section-body {
    padding: 24px 28px;
    color: #94a3b8;
    font-size: 14px;
    line-height: 1.8;
    min-height: 120px;
}
.section-body strong, .section-body b { color: #e2e8f0; font-weight: 500; }
.section-body br { display: block; margin: 4px 0; }

/* ── Stacked tab fallback (using Streamlit native tabs) ── */
.stTabs [data-baseweb="tab-list"] {
    background: #080c14 !important;
    border-bottom: 1px solid #1e2a3a !important;
    gap: 0 !important; padding: 0 8px !important;
    border-radius: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #5c7a9e !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    padding: 12px 16px !important;
    border-radius: 0 !important;
    border-bottom: 2px solid transparent !important;
    margin: 0 !important;
}
.stTabs [aria-selected="true"] {
    background: transparent !important;
    color: #58a6ff !important;
    border-bottom: 2px solid #3b82f6 !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: #0d1117 !important;
    border: none !important;
    border-top: 1px solid #1e2a3a !important;
    padding: 24px 28px !important;
    border-radius: 0 0 12px 12px !important;
}
.stTabs [data-baseweb="tab-border"] { display: none !important; }

/* ── Wrap tab group in border ── */
.stTabs {
    border: 1px solid #1e2a3a !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    background: #080c14 !important;
}

/* ── Section content ── */
.sec-content {
    color: #94a3b8;
    font-size: 14px;
    line-height: 1.85;
}
.sec-content strong { color: #e2e8f0; font-weight: 500; }

/* ── Upload badge ── */
.upload-badge {
    font-size: 11px; color: #4ade80; background: #052e16;
    border: 1px solid #166534; border-radius: 6px;
    padding: 3px 8px; margin-top: 4px; display: inline-block;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
def md_to_html(text: str) -> str:
    if not text:
        return "<span style='color:#374151'>No data available.</span>"
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"^#{1,3}\s+(.+)$", r"<strong>\1</strong>", text, flags=re.MULTILINE)
    text = text.replace("\n", "<br>")
    return text


def risk_class(score: int) -> str:
    return "risk-low" if score <= 3 else ("risk-med" if score <= 6 else "risk-high")

def risk_label(score: int) -> str:
    return "Low Risk" if score <= 3 else ("Medium Risk" if score <= 6 else "High Risk")

def risk_dot(score: int) -> str:
    return "🟢" if score <= 3 else ("🟡" if score <= 6 else "🔴")


# ── Render results ─────────────────────────────────────────────────────────────
def _render_results(report_data):
    if not isinstance(report_data, dict):
        st.markdown(report_data)
        return

    risk    = report_data.get("risk_score", 5)
    flags   = report_data.get("flags", [])
    warns   = report_data.get("warnings", [])
    sections = report_data.get("sections", {})
    location = report_data.get("location", {})
    rc       = risk_class(risk)
    rl       = risk_label(risk)

    # ── Divider with label ────────────────────────────────────────────────────
    st.markdown("""
    <div style="display:flex;align-items:center;gap:12px;margin:28px 0 20px">
      <div style="height:1px;flex:1;background:#1e2a3a"></div>
      <div style="font-size:10px;font-weight:600;color:#3b82f6;letter-spacing:1.2px;text-transform:uppercase">Analysis Results</div>
      <div style="height:1px;flex:1;background:#1e2a3a"></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Three-column dashboard ────────────────────────────────────────────────
    col_score, col_loc, col_flags = st.columns([1, 1.2, 2])

    with col_score:
        st.markdown(f"""
        <div class="risk-score-card {rc}">
          <div class="risk-score-label">Risk Score</div>
          <div class="risk-score-number">{risk}<span class="risk-score-denom">/10</span></div>
          <div class="risk-pill">{risk_dot(risk)} {rl}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_loc:
        st.markdown(f"""
        <div class="location-card">
          <div class="loc-row">
            <div class="loc-key">Location</div>
            <div class="loc-val">{location.get("city", "—")}, {location.get("country", "—")}</div>
          </div>
          <div class="loc-row">
            <div class="loc-key">ZIP / Postal</div>
            <div class="loc-val" style="font-size:14px">{location.get("zip_code") or "—"}</div>
          </div>
          <div class="loc-row">
            <div class="loc-key">Coordinates</div>
            <div class="loc-coords">{location.get("latitude","—")}°N &nbsp;·&nbsp; {location.get("longitude","—")}°E</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with col_flags:
        flag_html = '<div class="flags-card">'

        if flags:
            flag_html += '<div class="flags-card-title">Risk Flags</div>'
            for f in flags:
                flag_html += f'<div class="flag-row critical"><span class="flag-icon"></span><span>{f}</span></div>'

        if warns:
            flag_html += '<div class="flags-card-title" style="margin-top:8px">Warnings</div>'
            for w in warns:
                flag_html += f'<div class="flag-row warning"><span class="flag-icon"></span><span>{w}</span></div>'

        if not flags and not warns:
            flag_html += '<div class="flag-row clear"><span class="flag-icon">✓</span><span>No critical risk flags identified for this site.</span></div>'

        flag_html += '</div>'
        st.markdown(flag_html, unsafe_allow_html=True)

    # ── Section tabs ──────────────────────────────────────────────────────────
    SECTION_META = {
        "location_overview":      ("📍", "Location"),
        "executive_summary":      ("📋", "Summary"),
        "environmental_analysis": ("🌿", "Environment"),
        "technical_analysis":     ("⚙", "Technical"),
        "risk_assessment":        ("⚠", "Risk"),
        "planning_context":       ("🏗", "Planning"),
        "recommendation":         ("✅", "Recommendation"),
        "report":                 ("📄", "Report"),
    }

    tab_keys = [k for k in SECTION_META if k in sections and sections.get(k)]
    if not tab_keys:
        return

    st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)

    tab_labels = [f"{SECTION_META[k][0]} {SECTION_META[k][1]}" for k in tab_keys]
    tabs = st.tabs(tab_labels)

    for tab, key in zip(tabs, tab_keys):
        with tab:
            content = sections.get(key) or "No data available."
            st.markdown(
                f'<div class="sec-content">{md_to_html(content)}</div>',
                unsafe_allow_html=True
            )

    # ── Raw JSON + Download ───────────────────────────────────────────────────
    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
    dl_col, raw_col = st.columns([1, 3])

    with dl_col:
        try:
            pdf_path = generate_pdf(report_data)
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="Download PDF Report",
                    data=f,
                    file_name="geo_due_diligence_report.pdf",
                    mime="application/pdf",
                )
        except Exception as e:
            st.error(f"PDF error: {e}")

    with raw_col:
        with st.expander("Raw Report JSON"):
            st.json(report_data)


# ── APP LAYOUT ─────────────────────────────────────────────────────────────────

# Header
st.markdown("""
<div class="geo-header">
  <div class="geo-header-left">
    <div class="geo-header-icon">🧠</div>
    <div>
      <h1>Geo Due Diligence AI</h1>
      <p>AI-powered site analysis from polygon selection</p>
    </div>
  </div>
  <div class="geo-header-badge">NRW · Germany · WFS 1.1.0</div>
</div>
""", unsafe_allow_html=True)

# Two-column layout: map | sidebar
col_map, col_side = st.columns([3, 1], gap="medium")

with col_map:
    m = folium.Map(
    location=[51.45, 7.01],
    zoom_start=13,
    tiles="OpenStreetMap",   
    control_scale=True
)
    folium.plugins.Draw(
        export=False,
        draw_options={
            "polygon":   {"shapeOptions": {"color": "#3b82f6", "weight": 2, "fillOpacity": 0.12}},
            "rectangle": {"shapeOptions": {"color": "#3b82f6", "weight": 2, "fillOpacity": 0.12}},
            "circle": False, "marker": False, "circlemarker": False, "polyline": False,
        }
    ).add_to(m)

    if os.path.exists("data/polygon.json"):
        with open("data/polygon.json") as f:
            saved_coords = json.load(f)
        folium.Polygon(
            locations=[[c[1], c[0]] for c in saved_coords],
            color="#3b82f6", weight=1.5, fill=True, fill_opacity=0.1,
            tooltip="<b>Selected AOI</b>"
        ).add_to(m)

    if os.path.exists("data/flood_overlay.json"):
        with open("data/flood_overlay.json") as f:
            for poly_coords in json.load(f):
                folium.Polygon(
                    locations=[[c[1], c[0]] for c in poly_coords],
                    color="#ef4444", weight=1, fill=True, fill_opacity=0.3,
                    tooltip="Flood zone HQ100"
                ).add_to(m)

    if os.path.exists("data/protected_overlay.json"):
        with open("data/protected_overlay.json") as f:
            for poly_coords in json.load(f):
                folium.Polygon(
                    locations=[[c[1], c[0]] for c in poly_coords],
                    color="#22c55e", weight=1, fill=True, fill_opacity=0.2,
                    tooltip="Protected area"
                ).add_to(m)

    folium.LayerControl().add_to(m)
    map_data = st_folium(m, height=520, width=None, returned_objects=["last_active_drawing"])

# ... EVERYTHING ABOVE REMAINS EXACTLY SAME ...


with col_side:
    # ── Polygon section ────────────────────────────────────────────────────────
    st.markdown('<div class="panel-label">Area of Interest</div>', unsafe_allow_html=True)

    poly_saved = False
    if map_data and map_data.get("last_active_drawing"):
        geom = map_data["last_active_drawing"]["geometry"]
        coords = geom["coordinates"][0] if geom["type"] == "Polygon" else (
            geom["coordinates"][0][0] if geom["type"] == "MultiPolygon" else None
        )
        if coords and len(coords) >= 3:
            os.makedirs("data", exist_ok=True)
            with open("data/polygon.json", "w") as f:
                json.dump(coords, f)
            poly_saved = True

    if poly_saved or os.path.exists("data/polygon.json"):
        try:
            from shapely.geometry import Polygon as SPoly
            from tools.geo_utils import polygon_area_m2
            with open("data/polygon.json") as f:
                c = json.load(f)
            poly = SPoly(c)
            area = polygon_area_m2(poly)
            cen  = poly.centroid
            col_a, col_b = st.columns(2)
            col_a.metric("Area", f"{area/10_000:.1f} ha")
            col_b.metric("Points", str(len(c)-1))
            st.markdown(
                f'<div style="font-size:11px;color:#5c7a9e;font-family:JetBrains Mono,monospace;margin-top:4px">'
                f'{cen.y:.5f}°N &nbsp; {cen.x:.5f}°E</div>',
                unsafe_allow_html=True
            )
            if poly_saved:
                st.success("Polygon saved")
            if area > 10_000_000:
                st.warning("Large area — WFS may be slow")
        except Exception:
            st.info("Polygon loaded")
    else:
        st.markdown(
            '<div style="font-size:12px;color:#374151;padding:12px 0">Draw a polygon on the map to begin.</div>',
            unsafe_allow_html=True
        )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Documents section ──────────────────────────────────────────────────────
    st.markdown('<div class="panel-label">Supporting Documents</div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "Text, PDFs, CSVs, IMG",
        type=["pdf", "csv", "png", "jpg", "jpeg", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

# ✅ KEEP OUTSIDE (IMPORTANT FIX)
uploaded_txt_links = None

if uploaded_files:
    for uf in uploaded_files:
        size_kb = len(uf.getvalue()) / 1024

        st.markdown(
            f'<div class="upload-badge">📎 {uf.name} &nbsp;·&nbsp; {size_kb:.0f} KB</div>',
            unsafe_allow_html=True
        )

        # ✅ detect .txt file
        if uf.name.endswith(".txt"):
            try:
                content = uf.getvalue().decode("utf-8")
                uploaded_txt_links = [l.strip() for l in content.split("\n") if l.strip()]
                st.success(f"Loaded {len(uploaded_txt_links)} WFS links")
            except Exception as e:
                st.error(f"Failed to read txt: {e}")

# ✅ ALWAYS SHOW BUTTON (FIXED)
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
st.markdown('<div class="panel-label">Analysis</div>', unsafe_allow_html=True)

run = st.button("Analyse", type="primary", use_container_width=True)


# ── Pipeline execution ─────────────────────────────────────────────────────────
if run:
    if not os.path.exists("data/polygon.json"):
        st.error("No polygon found. Draw one on the map first.")
        st.stop()

    with st.status("Running analysis pipeline...", expanded=True) as status_box:
        try:
            report_data = main(
                status_callback=st.write,
                uploaded_files=uploaded_files,
                wfs_links=uploaded_txt_links
            )
            status_box.update(label="Analysis complete", state="complete")
        except Exception as e:
            status_box.update(label=f"Error: {e}", state="error")
            st.exception(e)
            st.stop()

    _render_results(report_data)

# ── Restore last result on reload ─────────────────────────────────────────────
elif os.path.exists("data/last_report.json"):
    try:
        with open("data/last_report.json") as f:
            _render_results(json.load(f))
    except Exception:
        pass