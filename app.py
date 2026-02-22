import streamlit as st
import sqlite3
import hashlib
import joblib
import pandas as pd
import plotly.express as px
import datetime

# ================= CONFIG =================
st.set_page_config(page_title="EduPredict-X", layout="wide")

# ================= HEADER =================
st.markdown("""
<style>
.hero {
    padding: 25px;
    border-radius: 15px;
    background: linear-gradient(135deg, #1e1e2f, #2c2c54);
    margin-bottom: 25px;
}
.hero-title {
    font-size: 36px;
    font-weight: 800;
    color: white;
}
.hero-subtitle {
    font-size: 16px;
    color: #c7c7ff;
}
</style>

<div class="hero">
    <div class="hero-title">EduPredict-X</div>
    <div class="hero-subtitle">
        AI-Based Academic Risk Forecasting & Intervention Simulator
    </div>
</div>
""", unsafe_allow_html=True)

# ================= LOAD MODEL =================
model = joblib.load("model.pkl")
risk_map = {0: "High Risk", 1: "Medium Risk", 2: "Low Risk"}

# ================= DATABASE =================
conn = sqlite3.connect("database.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT,
password TEXT,
role TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS records(
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT,
subject TEXT,
reading INTEGER,
writing INTEGER,
risk TEXT,
prob REAL,
timestamp TEXT
)
""")
conn.commit()

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

# ================= SESSION =================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ================= AUTH MENU =================
menu = st.sidebar.selectbox(
    "Menu",
    ["Login", "Register"] if not st.session_state.logged_in else ["Dashboard"]
)

# ================= REGISTER =================
if menu == "Register":
    st.header("Register")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["Student", "Admin"])

    if st.button("Create Account"):
        c.execute("INSERT INTO users VALUES(NULL,?,?,?)",
                  (username, hash_password(password), role))
        conn.commit()
        st.success("Account Created Successfully")

# ================= LOGIN =================
if menu == "Login":
    st.header("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        c.execute("SELECT * FROM users WHERE username=? AND password=?",
                  (username, hash_password(password)))
        user = c.fetchone()

        if user:
            st.session_state.logged_in = True
            st.session_state.username = user[1]
            st.session_state.role = user[3]
            st.rerun()
        else:
            st.error("Invalid Credentials")

# ================= DASHBOARD =================
if st.session_state.logged_in:

    st.sidebar.success(f"{st.session_state.username} ({st.session_state.role})")

    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    # ==========================================================
    # ========================== STUDENT =======================
    # ==========================================================

    if st.session_state.role == "Student":

        page = st.sidebar.selectbox(
            "Student Dashboard",
            ["Risk Forecasting", "Personal Analytics", "Trend Over Time"]
        )

        # ================= RISK FORECASTING =================
        if page == "Risk Forecasting":

            subject = st.text_input("Course / Subject")
            reading = st.slider("Reading Score", 0, 100)
            writing = st.slider("Writing Score", 0, 100)

            if st.button("Predict Academic Risk"):

                df_input = pd.DataFrame([{
                    "reading score": reading,
                    "writing score": writing
                }])

                pred = model.predict(df_input)[0]
                prob = model.predict_proba(df_input).max()
                risk = risk_map[pred]

                # Save baseline
                st.session_state.base_reading = reading
                st.session_state.base_writing = writing
                st.session_state.base_prob = prob
                st.session_state.base_risk = risk

                timestamp = datetime.datetime.now().strftime("%Y-%m-%d")

                c.execute("""
                INSERT INTO records VALUES(NULL,?,?,?,?,?,?,?)
                """, (st.session_state.username,
                      subject, reading, writing,
                      risk, float(prob), timestamp))
                conn.commit()

                st.success(f"Predicted Risk Category: {risk}")
                st.metric("Risk Probability", round(prob,4))

                # ================= USER-FRIENDLY EXPLANATION =================
                st.subheader("What This Means")

                if prob > 0.9:
                    st.success("Your performance is highly stable. Risk of academic underperformance is extremely low.")
                elif prob > 0.7:
                    st.warning("Moderate stability detected. Some improvement could further reduce risk.")
                else:
                    st.error("High vulnerability detected. Targeted improvement is strongly recommended.")

                # ================= PERFORMANCE DIAGNOSTICS =================
                st.divider()
                st.subheader("Skill Analysis")

                optimal = 75
                read_gap = optimal - reading
                write_gap = optimal - writing

                col1, col2 = st.columns(2)
                col1.metric("Reading Gap (Target 75)", read_gap)
                col2.metric("Writing Gap (Target 75)", write_gap)

                if read_gap > write_gap:
                    st.info("Primary area to improve: Reading skills.")
                elif write_gap > read_gap:
                    st.info("Primary area to improve: Writing skills.")
                else:
                    st.info("Both skills are balanced.")

            # ================= SIMULATION =================
            if "base_reading" in st.session_state:

                st.divider()
                st.subheader("Improvement Simulation")

                improve_read = st.slider("Increase Reading Score By", 0, 20)
                improve_write = st.slider("Increase Writing Score By", 0, 20)

                if st.button("Run Simulation"):

                    new_read = st.session_state.base_reading + improve_read
                    new_write = st.session_state.base_writing + improve_write

                    df_sim = pd.DataFrame([{
                        "reading score": new_read,
                        "writing score": new_write
                    }])

                    new_pred = model.predict(df_sim)[0]
                    new_prob = model.predict_proba(df_sim).max()
                    new_risk = risk_map[new_pred]

                    st.success(f"New Risk Category: {new_risk}")
                    st.metric("Updated Probability", round(new_prob,4))

                    delta = new_prob - st.session_state.base_prob

                    st.subheader("Impact of Improvement")

                    st.metric("Probability Change", round(delta,4))

                    if abs(delta) < 0.01:
                        st.info("Your performance was already strong. Further improvement gives minimal change.")
                    elif delta < 0:
                        st.success("Improvement meaningfully reduced your academic risk.")
                    else:
                        st.warning("Improvement did not reduce risk significantly.")

                    # Visual Comparison
                    compare_df = pd.DataFrame({
                        "Scenario": ["Before", "After"],
                        "Probability": [
                            st.session_state.base_prob,
                            new_prob
                        ]
                    })

                    fig = px.bar(compare_df, x="Scenario", y="Probability",
                                 color="Scenario",
                                 title="Risk Probability Comparison")

                    st.plotly_chart(fig, width="stretch")

        # ================= PERSONAL ANALYTICS =================
        if page == "Personal Analytics":

            df = pd.read_sql_query(
                f"SELECT * FROM records WHERE username='{st.session_state.username}'",
                conn
            )

            if df.empty:
                st.info("No records found.")
            else:
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Subjects", len(df))
                col2.metric("Average Probability", round(df["prob"].mean(),4))
                col3.metric("High Risk %", round((df["risk"]=="High Risk").mean()*100,2))

                fig = px.bar(df, x="subject", y="prob", color="risk")
                st.plotly_chart(fig, width="stretch")

                st.download_button(
                    "Download CSV",
                    df.to_csv(index=False).encode(),
                    "my_data.csv"
                )

        # ================= TREND =================
        if page == "Trend Over Time":

            df = pd.read_sql_query(
                f"SELECT * FROM records WHERE username='{st.session_state.username}'",
                conn
            )

            if not df.empty:
                fig = px.line(df, x="timestamp", y="prob", markers=True)
                st.plotly_chart(fig, width="stretch")

    # ================= ADMIN =================
    if st.session_state.role == "Admin":

        st.header("Model Benchmarking")

        try:
            results = pd.read_csv("model_results.csv")
            st.dataframe(results)

            fig = px.bar(results, x="Model", y="Accuracy")
            st.plotly_chart(fig, width="stretch")

            best = results.sort_values("Accuracy", ascending=False).iloc[0]
            st.success(f"Best Model: {best['Model']}")

        except:
            st.warning("Run train_model.py first.")