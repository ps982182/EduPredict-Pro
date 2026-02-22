import streamlit as st
import sqlite3
import hashlib
import joblib
import pandas as pd
import plotly.express as px
import datetime
import numpy as np

# ================= PAGE CONFIG =================
st.set_page_config(page_title="EduPredict Pro", layout="wide")

# ================= PREMIUM HERO =================
st.markdown("""
<style>
.hero {
    padding: 35px;
    border-radius: 20px;
    background: linear-gradient(135deg, #1e1e2f, #2c2c54);
    box-shadow: 0px 8px 30px rgba(0,0,0,0.4);
    margin-bottom: 30px;
}
.hero-title {
    font-size: 42px;
    font-weight: 800;
    color: white;
}
.hero-subtitle {
    font-size: 18px;
    color: #c7c7ff;
    margin-top: 8px;
}
</style>

<div class="hero">
    <div class="hero-title">EduPredict Pro</div>
    <div class="hero-subtitle">
        AI-Based Academic Risk Monitoring & Multi-User Analytics System
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
CREATE TABLE IF NOT EXISTS subjects(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    subject TEXT,
    reading INTEGER,
    writing INTEGER,
    risk TEXT,
    probability REAL,
    timestamp TEXT
)
""")

conn.commit()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ================= AUTH MENU =================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

menu = st.sidebar.selectbox("Menu", ["Login", "Register"] if not st.session_state.logged_in else ["Dashboard"])

# ================= REGISTER =================
if menu == "Register":
    st.header("Create Account")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["Student", "Teacher", "Admin"])

    if st.button("Register"):
        c.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)",
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

    st.sidebar.success(f"Welcome {st.session_state.username} ({st.session_state.role})")

    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    # ================= STUDENT =================
    if st.session_state.role == "Student":

        page = st.sidebar.selectbox(
            "Student Dashboard",
            ["Add Subject", "My Analytics", "Trend Over Time", "Upload CSV"]
        )

        # -------- ADD SUBJECT --------
        if page == "Add Subject":

            subject = st.text_input("Subject Name")
            reading = st.slider("Reading Score", 0, 100)
            writing = st.slider("Writing Score", 0, 100)

            if st.button("Predict"):

                df_input = pd.DataFrame([{
                    "gender": 0,
                    "race/ethnicity": 0,
                    "parental level of education": 0,
                    "lunch": 0,
                    "test preparation course": 0,
                    "reading score": reading,
                    "writing score": writing
                }])

                prediction = model.predict(df_input)[0]
                probability = model.predict_proba(df_input).max()
                risk_label = risk_map[prediction]
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d")

                c.execute("""
                INSERT INTO subjects(username,subject,reading,writing,
                risk,probability,timestamp)
                VALUES(?,?,?,?,?,?,?)
                """, (st.session_state.username, subject,
                      reading, writing, risk_label,
                      float(probability), timestamp))

                conn.commit()

                st.success(f"{subject} → {risk_label}")
                st.progress(float(probability))

                # ===== AI RECOMMENDATION ENGINE =====
                st.subheader("AI Recommendation")

                if risk_label == "High Risk":
                    st.error("High Academic Risk Detected")
                    st.write("• Increase study hours to 3–4 per day")
                    st.write("• Focus on weakest concepts first")
                    st.write("• Solve 2 mock tests weekly")
                    st.write("• Seek teacher mentoring")

                elif risk_label == "Medium Risk":
                    st.warning("Moderate Risk – Improvement Needed")
                    st.write("• Structured weekly revision")
                    st.write("• Improve weak areas")
                    st.write("• Regular practice tests")

                else:
                    st.success("Low Risk – Excellent Performance")
                    st.write("• Maintain consistency")
                    st.write("• Practice advanced questions")

        # -------- MY ANALYTICS --------
        if page == "My Analytics":

            df = pd.read_sql_query(
                f"SELECT * FROM subjects WHERE username='{st.session_state.username}'",
                conn
            )

            if df.empty:
                st.info("No records found.")
            else:

                col1, col2, col3 = st.columns(3)
                col1.metric("Total Subjects", len(df))
                col2.metric("Average Probability", round(df["probability"].mean(), 2))
                col3.metric("High Risk %", round((df["risk"]=="High Risk").mean()*100,2))

                fig = px.bar(df, x="subject", y="probability", color="risk",
                             title="Subject Risk Probability")
                st.plotly_chart(fig, use_container_width=True)

                st.divider()

                # Download Full CSV
                st.download_button(
                    "Download Full Data (CSV)",
                    df.to_csv(index=False).encode(),
                    "my_performance.csv",
                    "text/csv"
                )

                # Download Summary CSV
                summary = pd.DataFrame({
                    "Total Subjects":[len(df)],
                    "Average Probability":[round(df["probability"].mean(),2)],
                    "High Risk %":[round((df["risk"]=="High Risk").mean()*100,2)]
                })

                st.download_button(
                    "Download Summary Report (CSV)",
                    summary.to_csv(index=False).encode(),
                    "summary_report.csv",
                    "text/csv"
                )

        # -------- TREND --------
        if page == "Trend Over Time":

            df = pd.read_sql_query(
                f"SELECT * FROM subjects WHERE username='{st.session_state.username}'",
                conn
            )

            if not df.empty:
                fig = px.line(df, x="timestamp", y="probability",
                              markers=True,
                              title="Risk Trend Over Time")
                st.plotly_chart(fig, use_container_width=True)

        # -------- BULK CSV --------
        if page == "Upload CSV":

            uploaded = st.file_uploader("Upload CSV with columns: subject,reading,writing")

            if uploaded:
                df_upload = pd.read_csv(uploaded)
                results = []

                for _, row in df_upload.iterrows():
                    df_input = pd.DataFrame([{
                        "gender": 0,
                        "race/ethnicity": 0,
                        "parental level of education": 0,
                        "lunch": 0,
                        "test preparation course": 0,
                        "reading score": row["reading"],
                        "writing score": row["writing"]
                    }])

                    prediction = model.predict(df_input)[0]
                    probability = model.predict_proba(df_input).max()

                    results.append({
                        "subject": row["subject"],
                        "risk": risk_map[prediction],
                        "probability": probability
                    })

                st.dataframe(pd.DataFrame(results))

    # ================= TEACHER =================
    if st.session_state.role == "Teacher":

        df = pd.read_sql_query("SELECT * FROM subjects", conn)

        if not df.empty:
            st.metric("Total Records", len(df))
            st.metric("High Risk %",
                      round((df["risk"]=="High Risk").mean()*100,2))

            fig = px.histogram(df, x="risk", color="risk",
                               title="Class Risk Distribution")
            st.plotly_chart(fig, use_container_width=True)

    # ================= ADMIN =================
    if st.session_state.role == "Admin":

        df = pd.read_sql_query("SELECT * FROM subjects", conn)

        st.metric("Total Predictions", len(df))

        if not df.empty:
            fig = px.pie(df, names="risk",
                         title="Global Risk Distribution")
            st.plotly_chart(fig, use_container_width=True)