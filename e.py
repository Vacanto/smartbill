import os
import sqlite3

import joblib
import numpy as np
import pandas as pd
import streamlit as st

# ========= CONFIG =========
DB_PATH = r"C:\Users\ANTO CHARLES\models\users.db"
VOLTAGE_MODEL_PATH = r"C:\Users\ANTO CHARLES\models\fixed_voltage_model.pkl"
BILL_MODEL_PATH = r"C:\Users\ANTO CHARLES\models\fixed_bill_model.pkl"


# ========= DATABASE FUNCTIONS (SQLite) =========
def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_user_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def create_user(username: str, password: str):
    username = username.strip()
    if not username or not password:
        return False, "Username and password cannot be empty."

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password),
        )
        conn.commit()
        return True, "Signup successful. Please log in."
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    finally:
        conn.close()


def validate_user(username: str, password: str) -> bool:
    username = username.strip()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM users WHERE username = ? AND password = ?",
        (username, password),
    )
    row = cur.fetchone()
    conn.close()
    return row is not None


# ========= SESSION STATE =========
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "last_prediction" not in st.session_state:
    st.session_state.last_prediction = None


def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.last_prediction = None


# Initialize database
init_user_table()

# ========= SIDEBAR AUTH =========
st.sidebar.title("🔐 Authentication")
auth_choice = st.sidebar.radio("Select", ["Login", "Sign up"])

if not st.session_state.logged_in:
    st.title("👋 Welcome to SmartBill")
    st.markdown(
        "Predict your **voltage** and **monthly electricity bill** "
        "based on your home appliances and household details."
    )
    st.info("Please sign up or log in to continue.")

    if auth_choice == "Sign up":
        new_user = st.text_input("Choose a username")
        new_pass = st.text_input("Choose a password", type="password")
        if st.button("📝 Sign up"):
            ok, msg = create_user(new_user, new_pass)
            if ok:
                st.success(msg)
            else:
                st.error(msg)
    else:
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        if st.button("🚀 Login"):
            if validate_user(user, pwd):
                st.session_state.logged_in = True
                st.session_state.username = user.strip()
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password.")

    st.stop()


# ========= AFTER LOGIN =========
st.sidebar.success(f"✅ Logged in as: {st.session_state.username}")
if st.sidebar.button("🚪 Logout"):
    logout()
    st.rerun()


# ========= LOAD MODELS =========
@st.cache_resource(ttl=3600)
def load_models():
    model_voltage = joblib.load(VOLTAGE_MODEL_PATH)
    model_bill = joblib.load(BILL_MODEL_PATH)
    return model_voltage, model_bill


model_voltage, model_bill = load_models()


# ========= MAIN TITLE =========
st.title("🏠 SmartBill: Household Electricity Predictor")
st.markdown(
    "Estimate your **voltage** and **monthly electricity bill** "
    "using your exact appliances and home details."
)

# ========= PRESET SCENARIOS =========
st.subheader("🎛️ Quick Scenarios (Optional)")
scenario = st.selectbox(
    "Choose a preset (you can still edit values):",
    [
        "Custom (no preset)",
        "Basic Home (no AC/geyser)",
        "Middle-Class Home (1 AC, 1 geyser)",
        "Large Family (2 ACs, 1 geyser)",
    ],
)

# Default values
fans_default = 2
lights_default = 8
fridge_default = 1
tv_default = 1
ac_default = 0
water_heater_default = 0
washing_machine_default = 0
microwave_default = 0
family_default = 4
house_default = 1200
rooms_default = 3

if scenario == "Basic Home (no AC/geyser)":
    ac_default = 0
    water_heater_default = 0
elif scenario == "Middle-Class Home (1 AC, 1 geyser)":
    ac_default = 1
    water_heater_default = 1
    washing_machine_default = 1
    microwave_default = 1
    house_default = 1500
elif scenario == "Large Family (2 ACs, 1 geyser)":
    fans_default = 4
    lights_default = 14
    ac_default = 2
    water_heater_default = 1
    washing_machine_default = 1
    microwave_default = 1
    family_default = 6
    house_default = 2200
    rooms_default = 5

st.markdown("---")

# ========= APPLIANCE INPUTS =========
st.subheader("📺 Basic Appliances")
col1, col2 = st.columns(2)
with col1:
    fans = st.number_input("Fans", 0, 10, fans_default, help="Ceiling / table fans")
    lights = st.number_input("Lights", 0, 30, lights_default, help="LED / CFL bulbs")
with col2:
    fridge = st.number_input("Fridges", 0, 3, fridge_default, help="Refrigerators")
    tv = st.number_input("TVs", 0, 3, tv_default, help="LED / LCD TVs")

st.subheader("🔥 Heavy Appliances")
col3, col4 = st.columns(2)
with col3:
    ac = st.number_input("ACs", 0, 3, ac_default, help="Split / Window AC units")
    water_heater = st.number_input(
        "Water Heaters / Geysers", 0, 2, water_heater_default
    )
with col4:
    washing_machine = st.number_input(
        "Washing Machines", 0, 2, washing_machine_default
    )
    microwave = st.number_input("Microwaves", 0, 2, microwave_default)

# ========= HOUSEHOLD INPUTS =========
st.subheader("🏘️ Household Details")
col5, col6, col7 = st.columns(3)
with col5:
    num_family_members = st.number_input("Family Members", 1, 15, family_default)
with col6:
    house_size = st.number_input("House Size (sqft)", 200, 6000, house_default)
with col7:
    num_rooms = st.number_input("Number of Rooms", 1, 12, rooms_default)

st.markdown("---")

# ========= PREDICTION =========
if st.button("🔮 Predict Voltage & Bill", type="primary"):
    # Build a DataFrame with the SAME feature names as training
    data = {
        "fans": [fans],
        "lights": [lights],
        "fridge": [fridge],
        "tv": [tv],
        "ac": [ac],
        "water_heater": [water_heater],
        "washing_machine": [washing_machine],
        "microwave": [microwave],
        "num_family_members": [num_family_members],
        "house_size": [house_size],
        "num_rooms": [num_rooms],
    }
    features_df = pd.DataFrame(data)

    predicted_voltage = model_voltage.predict(features_df)[0]
    predicted_bill = model_bill.predict(features_df)[0]

    st.session_state.last_prediction = {
        "voltage": float(predicted_voltage),
        "bill": float(predicted_bill),
    }

    colA, colB = st.columns(2)
    with colA:
        st.metric("⚡ Predicted Voltage", f"{predicted_voltage:.1f} V", "±5 V")
    with colB:
        st.metric("💰 Monthly Electricity Bill", f"₹{predicted_bill:.0f}")

    st.subheader("📊 Estimated Usage")
    kwh_estimate = predicted_bill / 7  # assuming ₹7 per kWh
    st.info(
        f"**Estimated usage:** ~{kwh_estimate:.0f} kWh/month\n\n"
        "• Basic homes (no AC/geyser) usually fall in **₹250–₹1200** range.\n"
        "• Homes with AC / geyser can go **₹2500+** depending on usage."
    )

    st.success("Prediction generated successfully!")
    st.balloons()

# ========= SIDEBAR SUMMARY =========
st.sidebar.markdown("---")
st.sidebar.subheader("📌 Current Inputs")
st.sidebar.write(f"Fans: {fans}, Lights: {lights}")
st.sidebar.write(f"Fridges: {fridge}, TVs: {tv}")
st.sidebar.write(f"ACs: {ac}, Geysers: {water_heater}")
st.sidebar.write(f"WM: {washing_machine}, Microwaves: {microwave}")
st.sidebar.write(f"Family: {num_family_members}")
st.sidebar.write(f"Size: {house_size} sqft, Rooms: {num_rooms}")

if st.session_state.last_prediction:
    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 Last Prediction")
    st.sidebar.write(
        f"Voltage: {st.session_state.last_prediction['voltage']:.1f} V"
    )
    st.sidebar.write(f"Bill: ₹{st.session_state.last_prediction['bill']:.0f}")

st.markdown("---")
st.caption("🤖 SmartBill • Powered by Random Forest on 10,000+ synthetic households")
