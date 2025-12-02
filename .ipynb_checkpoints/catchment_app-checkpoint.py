import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="Virtual Catchment Lab", page_icon="🏔️", layout="wide")

st.title("🏔️ Virtual Catchment Laboratory")
st.markdown("""
**Physics-Based Rainfall-Runoff Modeling (ABCD Model)**
Simulate how land use changes affect river flow and groundwater recharge in Ghana.
""")

# --- THE PHYSICS ENGINE ---
class ABCDModel:
    def __init__(self, a, b, c, d, initial_soil=100, initial_gw=50):
        self.a = a 
        self.b = b 
        self.c = c 
        self.d = d 
        self.init_s = initial_soil
        self.init_g = initial_gw
        self.soil = initial_soil
        self.gw = initial_gw

    def step(self, P, PET):
        if pd.isna(P): P = 0.0
        if pd.isna(PET): PET = 5.0
        
        W = P + self.soil
        try:
            inner = ((W + self.b) / (2 * self.a))**2 - (W * self.b / self.a)
            if inner < 0: inner = 0
            Y = (W + self.b) / (2 * self.a) - np.sqrt(inner)
        except:
            Y = 0
            
        S_new = Y * np.exp(-PET / self.b)
        avail_mass = W - S_new
        
        GR = self.c * avail_mass       
        DIR = (1 - self.c) * avail_mass 
        
        BF = self.d * (self.gw + GR)   
        gw_new = (1 - self.d) * (self.gw + GR)
        
        Q = DIR + BF                   
        
        self.soil = S_new
        self.gw = gw_new
        
        return Q, DIR, BF, S_new, gw_new

    def run(self, df):
        results = []
        self.soil = self.init_s
        self.gw = self.init_g
        
        for _, row in df.iterrows():
            Q, DIR, BF, S, GW = self.step(row['Rain'], row['ETo'])
            results.append({
                "Date": row['Date'],
                "Rain": row['Rain'],
                "Flow_Total": Q,
                "Direct_Runoff": DIR,
                "Baseflow": BF,
                "Soil_Moisture": S,
                "Aquifer_Storage": GW
            })
        return pd.DataFrame(results)

# --- WEATHER DATA FETCH ---
@st.cache_data
def get_weather_data(lat, lon, past_days):
    if past_days > 92: past_days = 92
    
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=et0_fao_evapotranspiration,precipitation_sum&past_days={past_days}&forecast_days=7&timezone=GMT"
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        
        df = pd.DataFrame({
            "Date": data['daily']['time'],
            "ETo": data['daily']['et0_fao_evapotranspiration'],
            "Rain": data['daily']['precipitation_sum']
        })
        
        df['Date'] = pd.to_datetime(df['Date'])
        df['ETo'] = pd.to_numeric(df['ETo'], errors='coerce').fillna(0.0)
        df['Rain'] = pd.to_numeric(df['Rain'], errors='coerce').fillna(0.0)
        
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# --- SIDEBAR: CONTROLS ---
st.sidebar.header("1. Location & Duration")
loc_options = {
    "Densu Basin (Nsawam)": {"lat": 5.87, "lon": -0.38},
    "Pra Basin (Twifo Praso)": {"lat": 5.61, "lon": -1.55},
    "White Volta (Pwalugu)": {"lat": 10.58, "lon": -0.83},
    "Oti River (Saboba)": {"lat": 9.70, "lon": 0.32},
    "Custom": {"lat": 0.0, "lon": 0.0}
}
loc_name = st.sidebar.selectbox("Select Catchment", list(loc_options.keys()))

if loc_name == "Custom":
    col_lat, col_lon = st.sidebar.columns(2)
    lat = col_lat.number_input("Latitude", value=6.0, format="%.4f")
    lon = col_lon.number_input("Longitude", value=-1.0, format="%.4f")
else:
    lat = loc_options[loc_name]["lat"]
    lon = loc_options[loc_name]["lon"]

days_history = st.sidebar.slider("Simulation Duration (Days History)", 30, 92, 90, 
                               help="Open-Meteo allows max 92 days of history.")

st.sidebar.divider()
st.sidebar.header("2. Catchment Parameters")

preset = st.sidebar.radio("Load Preset:", ["Custom", "Pristine Forest", "Urban/Degraded"], index=0)

if preset == "Pristine Forest":
    def_a, def_b, def_c, def_d = 0.96, 400, 0.2, 0.05
elif preset == "Urban/Degraded":
    def_a, def_b, def_c, def_d = 0.99, 60, 0.1, 0.2
else:
    def_a, def_b, def_c, def_d = 0.98, 200, 0.1, 0.05

a = st.sidebar.slider("Parameter 'a' (Runoff Propensity)", 0.90, 0.999, def_a, 0.001)
b = st.sidebar.slider("Parameter 'b' (Soil Capacity mm)", 10, 600, def_b, 10)
c = st.sidebar.slider("Parameter 'c' (Recharge Split)", 0.0, 0.5, def_c, 0.05)
d = st.sidebar.slider("Parameter 'd' (Aquifer Discharge)", 0.0, 0.5, def_d, 0.01)

with st.sidebar.expander("Initial Conditions"):
    init_soil = st.number_input("Initial Soil Moisture (mm)", 0, 500, 100)
    init_gw = st.number_input("Initial Groundwater (mm)", 0, 500, 50)

# --- MAIN APP ---
if st.button("Run Simulation", type="primary"):
    with st.spinner(f"Fetching {days_history} days of weather history..."):
        df_weather = get_weather_data(lat, lon, days_history)
        
        if not df_weather.empty:
            model = ABCDModel(a, b, c, d, initial_soil=init_soil, initial_gw=init_gw)
            df_res = model.run(df_weather)
            
            # METRICS
            total_rain = df_res['Rain'].sum()
            total_flow = df_res['Flow_Total'].sum()
            runoff_ratio = (total_flow / total_rain) * 100 if total_rain > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Rainfall", f"{total_rain:.1f} mm")
            col2.metric("Total Streamflow", f"{total_flow:.1f} mm")
            
            status = "⚠️ Flashy (Flood Risk)" if runoff_ratio > 30 else "✅ Healthy Sponge"
            col3.metric("Runoff Coefficient", f"{runoff_ratio:.1f}%", delta=status, delta_color="inverse")
            
            with st.expander("📊 What does 'Runoff Coefficient' mean?"):
                st.markdown("""
                * **Definition:** The percentage of rain that becomes river flow.
                * **Low (< 20%):** Good. The landscape acts like a sponge (Forests).
                * **High (> 40%):** Bad. The landscape acts like a roof (Cities/Degraded Land).
                """)
            
            # HYDROGRAPH
            st.subheader(f"Combined Hyetograph & Hydrograph ({days_history} Days)")
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=df_res['Date'], y=df_res['Rain'], name='Rainfall (Input)',
                marker_color='blue', opacity=0.3, yaxis='y2'
            ))
            
            fig.add_trace(go.Scatter(
                x=df_res['Date'], y=df_res['Baseflow'], name='Baseflow (Groundwater)',
                stackgroup='one', fillcolor='rgba(31, 119, 180, 0.5)', line=dict(width=0)
            ))
            fig.add_trace(go.Scatter(
                x=df_res['Date'], y=df_res['Direct_Runoff'], name='Direct Runoff (Stormflow)',
                stackgroup='one', fillcolor='rgba(255, 127, 14, 0.5)', line=dict(width=0)
            ))
            fig.add_trace(go.Scatter(
                x=df_res['Date'], y=df_res['Flow_Total'], name='Total Hydrograph',
                line=dict(color='black', width=2)
            ))

            fig.update_layout(
                yaxis=dict(title="Streamflow Output (mm/day)"),
                yaxis2=dict(title="Rainfall Input (mm)", overlaying='y', side='right', range=[max(df_res['Rain'])*3, 0]),
                hovermode="x unified",
                legend=dict(orientation="h", y=1.1)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("🔎 How to read this Chart"):
                st.markdown("""
                **1. The Hyetograph (Top / Blue Bars)**: Represents the **Rainfall**. Taller bars = Heavier storms.
                **2. The Hydrograph (Bottom / Waves)**: Represents **River Flow**.
                * **🟠 Direct Runoff:** Flash floods (surface flow).
                * **🔵 Baseflow:** Groundwater flow (sustains river in dry season).
                """)

            # STATE VARIABLES
            st.subheader("Catchment Storage State")
            fig_state = go.Figure()
            fig_state.add_trace(go.Scatter(x=df_res['Date'], y=df_res['Soil_Moisture'], name='Soil Moisture'))
            fig_state.add_trace(go.Scatter(x=df_res['Date'], y=df_res['Aquifer_Storage'], name='Aquifer Storage'))
            fig_state.update_layout(yaxis_title="Storage (mm)", hovermode="x unified")
            st.plotly_chart(fig_state, use_container_width=True)
            
            # --- FINAL TOUCH: DOWNLOAD DATA ---
            st.divider()
            st.subheader("📥 Export Results")
            
            # Convert to CSV
            csv = df_res.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="Download Simulation Data (CSV)",
                data=csv,
                file_name=f"catchment_simulation_{loc_name}.csv",
                mime="text/csv",
                type="primary"
            )
            
        else:
            st.error("No weather data found.")