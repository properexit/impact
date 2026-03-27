import streamlit as st
import json
import os
import folium
import folium.plugins
from streamlit_folium import st_folium
from main import main
from report_pdf import generate_pdf

# ── DEFINE FUNCTION EARLY (FIX) ───────────────────────────────────────────────
def _render_results(report_data):
    st.divider()
    st.markdown("## 📊 Analysis Results")

    if not isinstance(report_data, dict):
        st.markdown(report_data)
        return

    risk = report_data.get("risk_score", 5)
    flags = report_data.get("flags", [])
    warnings_list = report_data.get("warnings", [])
    sections = report_data.get("sections", {})
    location = report_data.get("location", {})

    risk_cls = "risk-low" if risk <= 3 else ("risk-medium" if risk <= 6 else "risk-high")
    risk_label = "Low Risk" if risk <= 3 else ("Medium Risk" if risk <= 6 else "High Risk")

    c1, c2, c3 = st.columns([1, 1, 2])

    with c1:
        st.markdown(f"""
        <div class="risk-banner {risk_cls}">
          <div style="font-size:11px;color:#8b949e;text-transform:uppercase;letter-spacing:.6px;margin-bottom:6px">Risk Score</div>
          <div class="risk-score-num">{risk}<span style="font-size:18px;color:#8b949e">/10</span></div>
          <div class="risk-label">{risk_label}</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="metric-card" style="height:100%">
          <div class="label">Location</div>
          <div class="value">{location.get("city","—")}</div>
          <div style="margin-top:10px" class="label">Country</div>
          <div class="value">{location.get("country","—")}</div>
          <div style="margin-top:10px" class="label">Coordinates</div>
          <div style="font-size:13px;color:#8b949e;font-family:'DM Mono',monospace">
            {location.get("latitude","—")}°N &nbsp; {location.get("longitude","—")}°E
          </div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        if flags:
            st.markdown('<div class="section-title">RED FLAGS</div>', unsafe_allow_html=True)
            for f in flags:
                st.markdown(f'<div class="flag-item flag-critical">{f}</div>', unsafe_allow_html=True)
        if warnings_list:
            st.markdown('<div class="section-title">Warnings</div>', unsafe_allow_html=True)
            for w in warnings_list:
                st.markdown(f'<div class="flag-item flag-warning">{w}</div>', unsafe_allow_html=True)
        if not flags and not warnings_list:
            st.markdown('<div class="flag-item flag-critical" style="border-color:#238636;background:#0d1f17;color:#3fb950">No critical risk flags identified</div>', unsafe_allow_html=True)

    st.divider()

    section_titles = {
        "location_overview":    "📍 Location",
        "executive_summary":    "📋 Summary",
        "environmental_analysis": "🌿 Environment",
        "technical_analysis":   "⚙️ Technical",
        "risk_assessment":      "⚠️ Risk",
        "planning_context":     "🏗️ Planning",
        "recommendation":       "✅ Recommendation",
        "report":               "📄 Report",
    }

    tab_keys = [k for k in section_titles if k in sections and sections[k]]
    if tab_keys:
        tabs = st.tabs([section_titles[k] for k in tab_keys])
        for tab, key in zip(tabs, tab_keys):
            with tab:
                content = sections[key] or "No data available."
                import re
                html_content = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", content)
                html_content = html_content.replace("\n", "<br>")
                st.markdown(
                    f'<div class="section-card">{html_content}</div>',
                    unsafe_allow_html=True
                )

    with st.expander("🔍 Raw Report JSON"):
        st.json(report_data)

    st.divider()
    pdf_path = generate_pdf(report_data)
    with open(pdf_path, "rb") as f:
        st.download_button(
            label="📥 Download PDF Report",
            data=f,
            file_name="geo_due_diligence_report.pdf",
            mime="application/pdf",
        )



st.set_page_config(layout="wide", page_title="Geo Due Diligence AI", page_icon="🧠")

# ── Professional dark theme ───────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

  html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

  /* App background */
  .stApp { background: #0d1117; }
  section[data-testid="stSidebar"] { background: #0d1117; }

  /* Main content area */
  .block-container { padding-top: 1.5rem !important; }

  /* Header */
  .app-header {
    background: linear-gradient(135deg, #161b22 0%, #1c2128 100%);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 20px 28px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .app-header h1 { margin: 0; font-size: 22px; font-weight: 600; color: #e6edf3; letter-spacing: -0.3px; }
  .app-header p  { margin: 0; font-size: 13px; color: #8b949e; }

  /* Risk banner */
  .risk-banner {
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 12px;
    border: 1px solid;
  }
  .risk-low    { background: #0d1f17; border-color: #238636; }
  .risk-medium { background: #1f1a0e; border-color: #9e6a03; }
  .risk-high   { background: #1f0d0d; border-color: #da3633; }

  .risk-score-num { font-size: 42px; font-weight: 600; line-height: 1; font-family: 'DM Mono', monospace; }
  .risk-low    .risk-score-num { color: #3fb950; }
  .risk-medium .risk-score-num { color: #d29922; }
  .risk-high   .risk-score-num { color: #f85149; }

  .risk-label {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 11px; font-weight: 600; letter-spacing: 0.8px; text-transform: uppercase;
    margin-top: 6px;
  }
  .risk-low    .risk-label { background: #238636; color: #aff5b4; }
  .risk-medium .risk-label { background: #9e6a03; color: #ffd33d; }
  .risk-high   .risk-label { background: #da3633; color: #ffa198; }

  /* Metric cards */
  .metric-card {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 10px; padding: 14px 18px;
  }
  .metric-card .label { font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 4px; }
  .metric-card .value { font-size: 18px; font-weight: 500; color: #e6edf3; }

  /* Flag / warning items */
  .flag-item {
    display: flex; align-items: flex-start; gap: 8px;
    padding: 8px 12px; margin: 4px 0; border-radius: 6px;
    font-size: 13px; border-left: 3px solid;
  }
  .flag-critical { background: #1f0d0d; border-color: #f85149; color: #ffa198; }
  .flag-warning  { background: #1f1a0e; border-color: #d29922; color: #ffd33d; }

  /* Section content card */
  .section-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 20px 24px;
    color: #c9d1d9 !important;
    font-size: 14px;
    line-height: 1.75;
    min-height: 60px;
  }
  .section-card b, .section-card strong { color: #e6edf3; }
  .section-card p { color: #c9d1d9; margin: 0 0 8px 0; }

  /* Tabs styling */
  .stTabs [data-baseweb="tab-list"] {
    background: #161b22;
    border-radius: 8px 8px 0 0;
    border: 1px solid #30363d;
    border-bottom: none;
    padding: 4px 8px 0;
    gap: 2px;
  }
  .stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #8b949e !important;
    border-radius: 6px 6px 0 0;
    font-size: 13px;
    font-weight: 500;
    padding: 8px 14px;
    border: none !important;
  }
  .stTabs [aria-selected="true"] {
    background: #0d1117 !important;
    color: #58a6ff !important;
    border-bottom: 2px solid #1f6feb !important;
  }
  .stTabs [data-baseweb="tab-panel"] {
    background: #0d1117;
    border: 1px solid #30363d;
    border-top: none;
    border-radius: 0 0 8px 8px;
    padding: 16px;
  }

  /* Streamlit widgets */
  .stButton > button {
    background: #1f6feb; color: #fff; border: none;
    border-radius: 8px; font-weight: 500; font-size: 14px;
    padding: 10px 20px; width: 100%;
    transition: background 0.2s;
  }
  .stButton > button:hover { background: #388bfd; }

  div[data-testid="stMetric"] {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 10px; padding: 12px 16px;
  }
  div[data-testid="stMetric"] label { color: #8b949e !important; font-size: 12px !important; }
  div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #e6edf3 !important; font-size: 24px !important; }

  .stSuccess, .stInfo, .stWarning, .stError {
    border-radius: 8px !important;
    border: 1px solid !important;
  }
  .stSuccess { background: #0d1f17 !important; border-color: #238636 !important; color: #3fb950 !important; }
  .stInfo    { background: #0d1626 !important; border-color: #1f6feb !important; color: #58a6ff !important; }
  .stWarning { background: #1f1a0e !important; border-color: #9e6a03 !important; color: #d29922 !important; }

  /* Status box */
  [data-testid="stStatusWidget"] { background: #161b22 !important; border: 1px solid #30363d !important; border-radius: 10px !important; }

  /* Download button */
  .stDownloadButton > button {
    background: #238636; color: #fff; border: none;
    border-radius: 8px; font-weight: 500; font-size: 14px; width: 100%;
  }
  .stDownloadButton > button:hover { background: #2ea043; }

  /* Expander */
  details { background: #161b22 !important; border: 1px solid #30363d !important; border-radius: 8px !important; }
  summary { color: #8b949e !important; }

  /* Divider */
  hr { border-color: #21262d !important; margin: 20px 0 !important; }

  /* Section title */
  .section-title {
    font-size: 11px; font-weight: 600; color: #8b949e;
    text-transform: uppercase; letter-spacing: 0.8px;
    margin: 16px 0 8px;
  }
</style>
""", unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
  <div>
    <h1>🧠 Geo Due Diligence AI</h1>
    <p>Draw a polygon on the map → Run Analysis → Download PDF report</p>
  </div>
</div>
""", unsafe_allow_html=True)

col_map, col_ctrl = st.columns([3, 1])

with col_map:
    m = folium.Map(location=[51.45, 7.01], zoom_start=13)

    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attr="CartoDB Dark Matter",
        name="Dark",
    ).add_to(m)

    draw = folium.plugins.Draw(
        export=True,
        draw_options={
            "polygon":   {"shapeOptions": {"color": "#58a6ff", "weight": 2, "fillOpacity": 0.15}},
            "rectangle": {"shapeOptions": {"color": "#58a6ff", "weight": 2, "fillOpacity": 0.15}},
            "circle": False, "marker": False, "circlemarker": False, "polyline": False,
        }
    )
    draw.add_to(m)

    if os.path.exists("data/polygon.json"):
        with open("data/polygon.json") as f:
            coords = json.load(f)
        folium.Polygon(
            locations=[[c[1], c[0]] for c in coords],
            color="#58a6ff", weight=2, fill=True, fill_opacity=0.12,
            tooltip="Selected area"
        ).add_to(m)

    if os.path.exists("data/flood_overlay.json"):
        with open("data/flood_overlay.json") as f:
            flood_data = json.load(f)
        for poly_coords in flood_data:
            folium.Polygon(
                locations=[[c[1], c[0]] for c in poly_coords],
                color="#f85149", weight=1, fill=True, fill_opacity=0.3,
                tooltip="Flood zone HQ100"
            ).add_to(m)

    if os.path.exists("data/protected_overlay.json"):
        with open("data/protected_overlay.json") as f:
            prot_data = json.load(f)
        for poly_coords in prot_data:
            folium.Polygon(
                locations=[[c[1], c[0]] for c in poly_coords],
                color="#3fb950", weight=1, fill=True, fill_opacity=0.2,
                tooltip="Protected area"
            ).add_to(m)

    folium.LayerControl().add_to(m)
    map_data = st_folium(m, height=520, width=None, returned_objects=["last_active_drawing"])

with col_ctrl:
    st.markdown('<div class="section-title">Polygon</div>', unsafe_allow_html=True)

    if map_data and map_data.get("last_active_drawing"):
        geom = map_data["last_active_drawing"]["geometry"]
        if geom["type"] == "Polygon":
            coords = geom["coordinates"][0]
        elif geom["type"] == "MultiPolygon":
            coords = geom["coordinates"][0][0]
        else:
            coords = None

        if coords:
            os.makedirs("data", exist_ok=True)
            with open("data/polygon.json", "w") as f:
                json.dump(coords, f)

            from shapely.geometry import Polygon as SPoly
            from tools.geo_utils import polygon_area_m2
            poly = SPoly(coords)
            area = polygon_area_m2(poly)
            centroid = poly.centroid

            st.success("✅ Polygon saved")
            st.metric("Area", f"{area/10_000:.1f} ha")
            st.metric("Centroid", f"{centroid.y:.4f}°N")

            if area > 10_000_000:
                st.warning("⚠️ Area >1000 ha — WFS calls may be slow.")

    elif os.path.exists("data/polygon.json"):
        st.info("📌 Previous polygon loaded")
    else:
        st.info("👆 Draw a polygon on the map")

    st.markdown('<div class="section-title">Analysis</div>', unsafe_allow_html=True)
    run = st.button("🚀 Run Full Analysis", type="primary")


# ── Pipeline ──────────────────────────────────────────────────────────────────
if run:
    if not os.path.exists("data/polygon.json"):
        st.error("❌ No polygon found. Draw one on the map first.")
        st.stop()

    with st.status("🔄 Running analysis pipeline...", expanded=True) as status_box:
        try:
            report_data = main(status_callback=st.write)
            status_box.update(label="✅ Analysis complete", state="complete")
        except Exception as e:
            status_box.update(label=f"❌ Error: {e}", state="error")
            st.exception(e)
            st.stop()

    _render_results(report_data)


# ... (imports remain unchanged)

#st.set_page_config(layout="wide", page_title="Geo Due Diligence AI", page_icon="🧠")


# ── REST OF YOUR ORIGINAL CODE CONTINUES UNCHANGED ────────────────────────────
# ── Re-render last result on page reload ─────────────────────────────────────
if not run and os.path.exists("data/last_report.json"):
    try:
        with open("data/last_report.json") as f:
            cached = json.load(f)
        _render_results(cached)
    except Exception:
        pass