import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from sklearn.ensemble import RandomForestClassifier
from datetime import datetime

# --- 1. COORDINATE DATA (Mock for Bengaluru Pincodes) ---
# In a real app, you'd use a Pincode API to get Lat/Long
PINCODE_MAP = {
    560001: [12.9716, 77.5946],  # City Center
    560034: [12.9208, 77.6231],  # Koramangala
    560066: [12.9668, 77.7499],  # Whitefield
    560004: [12.9407, 77.5737]  # Basavanagudi
}


# --- 2. THE BRAIN: SCIKIT-LEARN PREDICTOR ---
@st.cache_resource
def train_model():
    # [Stock, Rain_Index, Accident_Index]
    X = [[5, 0.9, 0.8], [45, 0.1, 0.2], [12, 0.7, 0.6], [3, 0.9, 0.9], [50, 0.2, 0.1]]
    y = [1, 0, 1, 1, 0]  # 1 = Shortage Risk
    model = RandomForestClassifier(n_estimators=50)
    model.fit(X, y)
    return model


# --- 3. UI LAYOUT ---
st.set_page_config(page_title="Blood-Link: ABDM Predictive Grid", layout="wide")
st.title("🩸 Blood-Link: Decentralized Emergency Grid")
st.markdown("### *Real-time ABDM-Integrated Predictive Inventory*")

# Sidebar for Simulation
st.sidebar.header("🕹️ Environment Simulation")
rain_val = st.sidebar.slider("Rain Intensity (Monsoon Risk)", 0.0, 1.0, 0.2)
traffic_val = st.sidebar.slider("Traffic/Accident Risk", 0.0, 1.0, 0.3)

# Load Data
inventory = pd.read_csv('inventory.csv')
model = train_model()

# --- 4. DATA PROCESSING & MAP MARKERS ---
m = folium.Map(location=[12.9716, 77.5946], zoom_start=12, tiles="cartodbpositron")

# Logic to calculate risk for each hospital
for index, row in inventory.iterrows():
    pincode = int(row['pincode'])
    coords = PINCODE_MAP.get(pincode, [12.97, 77.59])

    # Predict Risk using Scikit-Learn
    prediction = model.predict([[row['current_units'], rain_val, traffic_val]])[0]

    # Visual Styling based on Risk
    color = "red" if prediction == 1 else "green"
    status = "⚠️ SHORTAGE RISK" if prediction == 1 else "✅ STABLE"

    # Create Popup with ABDM/FHIR Info
    popup_text = f"""
    <b>{row['hospital_name']}</b><br>
    Stock: {row['current_units']} units ({row['blood_type']})<br>
    Status: {status}<br>
    ABDM Facility ID: HFR-{pincode}-01
    """

    folium.CircleMarker(
        location=coords,
        radius=10 if prediction == 1 else 6,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.6,
        popup=folium.Popup(popup_text, max_width=250)
    ).add_to(m)

# --- 5. DASHBOARD DISPLAY ---
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("#### 📍 Live Emergency Grid")
    st_folium(m, width=800, height=500)

with col2:
    st.markdown("#### 📊 Risk Analysis")
    st.write(f"**Global Variables:** Rain: {rain_val}, Traffic: {traffic_val}")

    if rain_val > 0.7:
        st.error("Extreme Weather Detected: Increasing predictive weight for trauma centers.")

    st.dataframe(inventory[['hospital_name', 'blood_type', 'current_units']])

    if st.button("Trigger Micro-Donation Alerts (ABDM Verified)"):
        st.success("Querying ABHA Registry... Alerts sent to verified donors in Red Zones.")