import streamlit as st
import json
import os
import folium
import folium.plugins

from streamlit_folium import st_folium

from main import main
from report_pdf import generate_pdf


st.set_page_config(layout="wide")
st.title("🧠 Geo Due Diligence AI")

m = folium.Map(location=[52.52, 13.405], zoom_start=13)

draw = folium.plugins.Draw(export=True)
draw.add_to(m)

map_data = st_folium(m, height=500, width=900)

if map_data and map_data.get("last_active_drawing"):
    coords = map_data["last_active_drawing"]["geometry"]["coordinates"][0]

    os.makedirs("data", exist_ok=True)

    with open("data/polygon.json", "w") as f:
        json.dump(coords, f)

    st.success("Polygon saved!")

    if st.button("🚀 Run Analysis"):
        report = main()

        st.subheader("📍 Location & Report")
        st.markdown(report)

        pdf_path = generate_pdf(report)

        with open(pdf_path, "rb") as f:
            st.download_button(
                "📥 Download PDF Report",
                f,
                "report.pdf"
            )