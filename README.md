 Virtual Catchment Laboratory

A Physics-Based Rainfall-Runoff Simulator for Ghanaian Basins.

🎯 Overview

Hydrological modeling often requires complex, expensive software (like HEC-HMS or SWAT) and hard-to-find data. This tool provides an accessible, web-based interface to simulate the ABCD Hydrological Model (Thomas, 1981).

It allows researchers, students, and policymakers to visualize how changes in land use (e.g., deforestation, urbanization) impact river flow and groundwater recharge using real-time satellite weather data.

🚀 Features

ABCD Physics Engine: A continuous soil moisture accounting simulation that tracks water storage day-by-day.

Live Satellite Data: Connects to the Open-Meteo API to fetch live rainfall and evapotranspiration data for any coordinate in Ghana.

Land Use Scenarios: Includes preset parameters to simulate "Pristine Forest" vs. "Degraded Land" scenarios instantly.

Interactive Hydrographs: Visualizes the separation of Baseflow (Groundwater) vs. Direct Runoff (Flash Floods).

Data Export: Allows users to download the full simulation results as a CSV file for further analysis.

📊 The Science: The ABCD Model

The model represents the catchment as two storage "buckets" (Soil and Aquifer) and uses 4 non-linear parameters to define behavior:

Parameter

Name

Description

High Value Meaning

a

Runoff Propensity

(0 - 1) Tendency for rain to run off immediately.

Urban/Degraded (Flashy floods)

b

Soil Capacity

(mm) The size of the soil moisture "bucket".

Forest (Deep, spongy soil)

c

Recharge Split

(0 - 1) Portion of water entering the aquifer.

High Infiltration (Healthy recharge)

d

Discharge Rate

(0 - 1) How fast the aquifer releases water.

Fast Recession (River dries quickly)

🛠️ Installation & Usage

Clone the repository:

git clone [https://github.com/YOUR_USERNAME/catchment-lab.git](https://github.com/YOUR_USERNAME/catchment-lab.git)
cd catchment-lab


Install dependencies:

pip install -r requirements.txt


Run the App:

streamlit run catchment_app.py


📍 Key Locations Monitored

Densu Basin: Critical water source for Accra (Weija Dam).

Pra Basin: Major river affected by Galamsey (illegal mining).

White Volta: Transboundary river influencing Akosombo Dam inflows.

Oti River: Key tributary in the Eastern corridor.

📄 License

Open Source for Academic and Research use.
