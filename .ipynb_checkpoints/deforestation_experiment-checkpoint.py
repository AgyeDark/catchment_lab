import numpy as np
import pandas as pd
import requests
import matplotlib.pyplot as plt

# --- 1. THE PHYSICS ENGINE (Reused) ---
class ABCDModel:
    def __init__(self, name, a=0.98, b=400, c=0.1, d=0.05, initial_soil=100, initial_gw=50):
        self.name = name
        self.a = a
        self.b = b  # <--- THIS IS THE KEY PARAMETER WE WILL CHANGE
        self.c = c
        self.d = d
        self.soil_storage = initial_soil
        self.gw_storage = initial_gw

    def step(self, P, PET):
        # Safety checks
        if pd.isna(P): P = 0.0
        if pd.isna(PET): PET = 5.0
        
        # 1. Water enters system
        W = P + self.soil_storage
        
        # 2. Evapotranspiration Opportunity (The "Sponge" Effect)
        # Deep soil (High b) allows more storage, less immediate saturation
        try:
            inner = ((W + self.b) / (2 * self.a))**2 - (W * self.b / self.a)
            if inner < 0: inner = 0
            Y = (W + self.b) / (2 * self.a) - np.sqrt(inner)
        except:
            Y = 0
            
        S_new = Y * np.exp(-PET / self.b)
        avail_mass = W - S_new
        
        # 3. Partitioning
        GR = self.c * avail_mass
        DIR = (1 - self.c) * avail_mass
        
        baseflow = self.d * (self.gw_storage + GR)
        gw_new = (1 - self.d) * (self.gw_storage + GR)
        Q = DIR + baseflow
        
        self.soil_storage = S_new
        self.gw_storage = gw_new
        
        return {"Q_Total": Q, "Direct_Runoff": DIR, "Baseflow": baseflow}

    def run_simulation(self, weather_df):
        results = []
        for _, row in weather_df.iterrows():
            res = self.step(row['Rain'], row['ETo'])
            res['Date'] = row['Date']
            results.append(res)
        return pd.DataFrame(results)

# --- 2. GET DATA (Using Fixed Manual URL) ---
def get_weather():
    print("🛰️ Fetching Rainfall Data...")
    # Using specific Lat/Lon for a forest zone (e.g., Near Kade/Atewa)
    url = "https://api.open-meteo.com/v1/forecast?latitude=6.15&longitude=-0.90&daily=et0_fao_evapotranspiration,precipitation_sum&past_days=92&forecast_days=7&timezone=GMT"
    
    r = requests.get(url)
    data = r.json()
    
    # FIX: Load raw lists first, then convert columns safely
    df = pd.DataFrame({
        "Date": data['daily']['time'],
        "ETo": data['daily']['et0_fao_evapotranspiration'],
        "Rain": data['daily']['precipitation_sum']
    })
    
    # Robust Conversion
    df['Date'] = pd.to_datetime(df['Date'])
    df['ETo'] = pd.to_numeric(df['ETo'], errors='coerce').fillna(0.0)
    df['Rain'] = pd.to_numeric(df['Rain'], errors='coerce').fillna(0.0)
    
    return df

# --- 3. THE EXPERIMENT ---
if __name__ == "__main__":
    df_weather = get_weather()
    
    # SCENARIO A: The Pristine Forest
    # b = 400 (Deep, spongy soil that holds 400mm of water)
    print("🌲 Simulating Forest Catchment...")
    forest_model = ABCDModel(name="Forest", a=0.96, b=400, c=0.2, d=0.05)
    df_forest = forest_model.run_simulation(df_weather)
    
    # SCENARIO B: The Deforested/Degraded Land
    # b = 60 (Compacted, shallow soil that only holds 60mm)
    print("🚜 Simulating Deforested Catchment...")
    degraded_model = ABCDModel(name="Degraded", a=0.99, b=60, c=0.2, d=0.05)
    df_degraded = degraded_model.run_simulation(df_weather)
    
    # --- 4. VISUAL PROOF ---
    print("📊 Generating Comparison Plot...")
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    
    # Plot 1: Rainfall
    ax1.bar(df_weather['Date'], df_weather['Rain'], color='blue', alpha=0.3, label='Rainfall Input')
    ax1.set_ylim(max(df_weather['Rain'])*1.5, 0)
    ax1.set_ylabel("Rain (mm)")
    ax1.legend()
    ax1.set_title("The Input: Rainfall Event")
    
    # Plot 2: The Flood Peaks Comparison
    # We plot the DIRECT RUNOFF (Stormflow) to show the flooding impact
    ax2.plot(df_degraded['Date'], df_degraded['Direct_Runoff'], color='red', lw=2, label='Degraded Land (b=60)')
    ax2.fill_between(df_degraded['Date'], 0, df_degraded['Direct_Runoff'], color='red', alpha=0.1)
    
    ax2.plot(df_forest['Date'], df_forest['Direct_Runoff'], color='green', lw=2, label='Pristine Forest (b=400)')
    ax2.fill_between(df_forest['Date'], 0, df_forest['Direct_Runoff'], color='green', alpha=0.3)
    
    ax2.set_ylabel("Surface Runoff (mm)")
    ax2.set_title("The Result: Forest vs. Deforested Flood Peaks")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Calculate the % Increase in Peak Flow
    peak_forest = df_forest['Direct_Runoff'].max()
    peak_degraded = df_degraded['Direct_Runoff'].max()
    increase = ((peak_degraded - peak_forest) / peak_forest) * 100
    
    plt.figtext(0.5, 0.02, f"CONCLUSION: Deforestation increased the peak flood flow by {increase:.1f}%", 
                ha="center", fontsize=12, bbox={"facecolor":"orange", "alpha":0.2, "pad":5})
    
    plt.savefig("Deforestation_Impact.png")
    plt.show()
    print(f"⚠️ RESULT: Peak Flood increased by {increase:.1f}%!")