import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from datetime import datetime


# --- 1. MOCK ABDM INTEGRATION ---
# In a real hackathon, you'd call the ABDM Sandbox API here.
def verify_abha_donor(abha_id):
    """Simulates ABHA ID verification through ABDM Gateway"""
    donors = pd.read_csv('donor_registry.csv')
    donor = donors[donors['abha_id'] == abha_id]
    if not donor.empty:
        return True, donor.iloc[0]['name']
    return False, None


# --- 2. THE PREDICTIVE ENGINE (Scikit-Learn) ---
def train_shortage_model():
    """
    Trains a simple model to predict 'Shortage Risk' (1 or 0)
    Features: [Current_Stock, Pincode_Demand_Index, Weather_Risk_Index]
    """
    # Dummy Training Data: [Stock, Demand, Weather(0-1)] -> Shortage(1)
    # Weather 1.0 = Monsoon/Heavy Rain (High Accident Risk)
    X = np.array([
        [20, 5, 0.1], [5, 15, 0.9], [2, 10, 0.8], [50, 2, 0.1],
        [8, 12, 0.7], [30, 5, 0.2], [1, 20, 0.9], [15, 5, 0.1]
    ])
    y = np.array([0, 1, 1, 0, 1, 0, 1, 0])  # 1 = Shortage Likely

    model = RandomForestClassifier(n_estimators=10)
    model.fit(X, y)
    return model


# --- 3. THE "BLOOD-LINK" EXECUTION ---
def run_blood_link_system():
    print("🩸 Initializing Blood-Link: Decentralized Emergency Grid...")

    # Load Inventory
    inventory = pd.read_csv('inventory.csv')
    model = train_shortage_model()

    # Simulate a scenario for Pincode 560001
    # Inputs: Current Stock: 8 units, Demand Index: 14, Weather: 0.8 (Rainy)
    current_data = np.array([[8, 14, 0.8]])
    prediction = model.predict(current_data)

    if prediction[0] == 1:
        print("\n⚠️  SYSTEM ALERT: High probability of shortage in Pincode 560001 within 48h.")
        print("🔍 Searching for Micro-Donors in proximity...")

        # Filter local donors from CSV
        donors = pd.read_csv('donor_registry.csv')
        local_donors = donors[donors['pincode'] == 560001]

        for _, donor in local_donors.iterrows():
            # Mock ABDM verification before sending alert
            is_valid, name = verify_abha_donor(donor['abha_id'])
            if is_valid:
                print(f"✅ Alert sent to Verified Donor {name} (ABHA: {donor['abha_id']})")
    else:
        print("\n✅ Inventory Stable for Pincode 560001.")


if __name__ == "__main__":
    run_blood_link_system()