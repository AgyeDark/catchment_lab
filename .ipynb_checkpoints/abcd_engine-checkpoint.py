import numpy as np
import pandas as pd
import requests
import matplotlib.pyplot as plt

print("🚀 Loading ABCD Model Engine (v2 - Robust)...")

class ABCDModel:
    def __init__(self, a=0.98, b=400, c=0.1, d=0.05, initial_soil=100, initial_gw=50):
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.soil_storage = initial_soil
        self.gw_storage = initial_gw

    def step(self, P, PET):
        # --- NUCLEAR SAFETY CHECKS ---
        # Force P (Precipitation) to be a float
        try:
            if pd.isna(P) or isinstance(P, (pd.Timestamp, np.datetime64)): 
                P = 0.0
            else:
                P = float(P)
        except:
            P = 0.0
            
        # Force PET (Evapotranspiration) to be a float
        try:
            if pd.isna(PET) or isinstance(PET, (pd.Timestamp, np.datetime64)):
                PET = 5.0 # Default fallback
            else:
                PET = float(PET)
        except:
            PET = 5.0

        # 1. Available Water (W)
        W = P + self.soil_storage
        
        # 2. Evapotranspiration Opportunity (Y)
        # The heart of the ABCD model
        try:
            # Prevent domain errors in sqrt
            inner_term = ((W + self.b) / (2 * self.a))**2 - (W * self.b / self.a)
            if inner_term < 0: inner_term = 0
            
            Y = (W + self.b) / (2 * self.a) - np.sqrt(inner_term)
        except Exception as e:
            print(f"Math Error with W={W}, P={P}: {e}")
            Y = 0
        
        # 3. Update Soil Storage
        S_new = Y * np.exp(-PET / self.b)
        
        # 4. Water Leaving Soil
        avail_mass = W - S_new
        
        # 5. Partition
        GR = self.c * avail_mass
        DIR = (1 - self.c) * avail_mass
        
        # 6. Groundwater Bucket
        baseflow = self.d * (self.gw_storage + GR)
        gw_new = (1 - self.d) * (self.gw_storage + GR)
        
        # 7. Total Streamflow
        Q = DIR + baseflow
        
        # Update State
        self.soil_storage = S_new
        self.gw_storage = gw_new
        
        return {
            "Q_Total": Q,
            "Direct_Runoff": DIR,
            "Baseflow": baseflow,
            "Soil_Moisture": S_new,
            "Groundwater_Storage": gw_new
        }

    def run_simulation(self, weather_df):
        results = []
        print("🌊 Running Hydro-Simulation...")
        
        for index, row in weather_df.iterrows():
            # Explicitly grab columns
            rain_val = row['Rain']
            eto_val = row['ETo']
            
            day_res = self.step(rain_val, eto_val)
            day_res['Date'] = row['Date']
            day_res['Rain'] = rain_val
            results.append(day_res)
            
        return pd.DataFrame(results)

# --- HELPER: GET REAL DATA ---
def get_ghana_weather(lat=6.10, lon=0.05):
    print(f"🛰️ Fetching Satellite Weather for Lat:{lat}, Lon:{lon}...")
    
    # 1. Build URL Manually
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=et0_fao_evapotranspiration,precipitation_sum&past_days=92&forecast_days=7&timezone=GMT"
    
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        
        # 2. Create DataFrame
        df = pd.DataFrame({
            "Date": data['daily']['time'],
            "ETo": data['daily']['et0_fao_evapotranspiration'],
            "Rain": data['daily']['precipitation_sum']
        })
        
        # 3. FORCE DATA TYPES
        print("DEBUG: Cleaning Data Types...")
        
        # Date
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Numbers - Convert columns to numeric, coerce errors to NaN, then fill with 0.0
        df['ETo'] = pd.to_numeric(df['ETo'], errors='coerce').fillna(0.0)
        df['Rain'] = pd.to_numeric(df['Rain'], errors='coerce').fillna(0.0)
        
        # 4. Verify Types
        print(f"DEBUG: Rain column type is {df['Rain'].dtype}")
        if not pd.api.types.is_numeric_dtype(df['Rain']):
            print("CRITICAL WARNING: Rain is still not numeric! Forcing float.")
            df['Rain'] = df['Rain'].astype(float)
            
        return df
        
    except Exception as e:
        print(f"❌ Error fetching weather: {e}")
        # Return dummy data to prevent crash
        dates = pd.date_range(end=pd.Timestamp.now(), periods=10)
        return pd.DataFrame({"Date": dates, "ETo": 5.0, "Rain": 0.0})

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # 1. Get Data
    df_weather = get_ghana_weather(lat=5.87, lon=-0.38)
    
    # 2. Initialize Model
    model = ABCDModel(a=0.96, b=200, c=0.2, d=0.01)
    
    # 3. Run
    df_res = model.run_simulation(df_weather)
    
    # 4. Visualize
    if not df_res.empty:
        print("📊 Plotting Hydrograph...")
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
        
        # Top Panel: Rainfall
        ax1.bar(df_res['Date'], df_res['Rain'], color='blue', alpha=0.5, label='Rainfall')
        ax1.set_ylim(max(df_res['Rain'])*1.5, 0)
        ax1.set_ylabel("Rainfall (mm)")
        ax1.legend(loc='upper right')
        ax1.set_title("Catchment Input (Rain)")
        
        # Bottom Panel: Flow
        ax2.plot(df_res['Date'], df_res['Q_Total'], color='black', lw=2, label='Total Streamflow')
        ax2.fill_between(df_res['Date'], 0, df_res['Baseflow'], color='#1f77b4', alpha=0.3, label='Baseflow')
        ax2.fill_between(df_res['Date'], df_res['Baseflow'], df_res['Q_Total'], color='#ff7f0e', alpha=0.3, label='Direct Runoff')
        
        ax2.set_ylabel("Flow (mm/day)")
        ax2.set_xlabel("Date")
        ax2.legend()
        ax2.set_title("Simulated Hydrograph (ABCD Model)")
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig("Hydrograph_Simulation.png")
        plt.show()
        print("✅ Done! Saved 'Hydrograph_Simulation.png'")
    else:
        print("❌ Simulation failed (No data)")