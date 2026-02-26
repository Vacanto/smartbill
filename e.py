import os
import sqlite3
import joblib
import numpy as np
import pandas as pd
import streamlit as st

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="SmartBill",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
    <style>
        .stButton>button {
            width: 100%;
            height: 3em;
            font-size: 18px;
            border-radius: 10px;
        }
        .stTextInput>div>div>input {
            border-radius: 8px;
        }
    </style>
""", unsafe_allow_html=True)

# ================= CONFIG =================
DB_PATH = "users.db"
VOLTAGE_MODEL_PATH = "models/fixed_voltage_model.pkl"
BILL_MODEL_PATH = "models/fixed_bill_model.pkl"

# ================= DATABASE =================
def get_connection():
    return sqlite3.connect(DB_PATH)


def init_user_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def create_user(username, password):
    if not username or not password:
        return False, "Username and password cannot be empty."

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username.strip(), password)
        )
        conn.commit()
        return True, "Signup successful! Please login."
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    finally:
        conn.close()


def validate_user(username, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM users WHERE username=? AND password=?",
        (username.strip(), password)
    )
    result = cur.fetchone()
    conn.close()
    return result is not None


init_user_table()

# ================= SESSION =================
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


# ================= AUTH =================
st.sidebar.title("🔐 Authentication")

auth_mode = st.sidebar.radio("Select", ["Login", "Sign up"])

if not st.session_state.logged_in:

    st.title("⚡ Welcome to SmartBill")
    st.info("Please login or create an account to continue.")

    if auth_mode == "Sign up":
        new_user = st.text_input("Create Username")
        new_pass = st.text_input("Create Password", type="password")

        if st.button("Sign up"):
            ok, msg = create_user(new_user, new_pass)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    else:
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")

        if st.button("Login"):
            if validate_user(user, pwd):
                st.session_state.logged_in = True
                st.session_state.username = user
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials")

    st.stop()

# ================= AFTER LOGIN =================
st.sidebar.success(f"Logged in as {st.session_state.username}")

if st.sidebar.button("Logout"):
    logout()
    st.rerun()

# ================= LOAD MODELS =================
@st.cache_resource
def load_models():
    model_voltage = joblib.load(VOLTAGE_MODEL_PATH)
    model_bill = joblib.load(BILL_MODEL_PATH)
    return model_voltage, model_bill


model_voltage, model_bill = load_models()

# ================= MAIN APP =================
st.title("🏠 SmartBill Electricity Predictor")

st.subheader("🔌 Appliances")

col1, col2 = st.columns(2)

with col1:
    fans = st.number_input("Fans", 0, 10, 2)
    lights = st.number_input("Lights", 0, 30, 8)
    fridge = st.number_input("Fridges", 0, 3, 1)
    tv = st.number_input("TVs", 0, 3, 1)

with col2:
    ac = st.number_input("ACs", 0, 3, 0)
    water_heater = st.number_input("Geysers", 0, 2, 0)
    washing_machine = st.number_input("Washing Machines", 0, 2, 0)
    microwave = st.number_input("Microwaves", 0, 2, 0)

st.subheader("🏠 Household Details")

col3, col4, col5 = st.columns(3)

with col3:
    family = st.number_input("Family Members", 1, 15, 4)

with col4:
    house_size = st.number_input("House Size (sqft)", 200, 6000, 1200)

with col5:
    rooms = st.number_input("Rooms", 1, 12, 3)

# ================= PREDICTION =================
if st.button("⚡ Predict Electricity Bill", type="primary"):

    data = pd.DataFrame({
        "fans": [fans],
        "lights": [lights],
        "fridge": [fridge],
        "tv": [tv],
        "ac": [ac],
        "water_heater": [water_heater],
        "washing_machine": [washing_machine],
        "microwave": [microwave],
        "num_family_members": [family],
        "house_size": [house_size],
        "num_rooms": [rooms],
    })

    voltage = model_voltage.predict(data)[0]
    bill = model_bill.predict(data)[0]

    st.session_state.last_prediction = {
        "voltage": float(voltage),
        "bill": float(bill),
    }

    # 🎈 Celebration
    st.balloons()
    st.success("Prediction generated successfully!")

    colA, colB = st.columns(2)

    with colA:
        st.metric("⚡ Predicted Voltage", f"{voltage:.1f} V")

    with colB:
        st.metric("💰 Estimated Monthly Bill", f"₹{bill:.0f}")

    kwh = bill / 7
    st.info(f"📊 Estimated Usage: {kwh:.0f} kWh/month")

    if bill > 3000:
        st.warning("⚠ High electricity usage detected!")
    else:
        st.success("✅ Electricity usage within normal range.")

# ================= SIDEBAR SUMMARY =================
if st.session_state.last_prediction:
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Last Prediction")
    st.sidebar.write(
        f"Voltage: {st.session_state.last_prediction['voltage']:.1f} V"
    )
    st.sidebar.write(
        f"Bill: ₹{st.session_state.last_prediction['bill']:.0f}"
    )

st.markdown("---")
st.caption("SmartBill • ML Powered Electricity Forecasting System")