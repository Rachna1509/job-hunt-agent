from openai import OpenAI
import tempfile
import streamlit as st
import pandas as pd
import subprocess
import os, json, re
import altair as alt
import plotly.graph_objects as go
import base64

# ---------------------------
# INIT
# ---------------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
st.set_page_config(page_title="Rachna's AI Assisted Job Hunt Agent", page_icon="💼", layout="wide")

# ---------------------------
# THEME + STYLE
# ---------------------------
if "theme_choice" not in st.session_state:
    st.session_state["theme_choice"] = "Dark"

theme_choice = st.sidebar.radio(
    "Theme Mode",
    ["Light", "Dark"],
    index=1 if st.session_state["theme_choice"] == "Dark" else 0,
    horizontal=True
)
st.session_state["theme_choice"] = theme_choice

# --- LIGHT THEME (Pastel Dashboard) ---
light_theme = """
<style>
section[data-testid="stSidebar"] {
    background: #f7f8fb !important;
    border-right: 1px solid #d9dee8;
}
.block-container {
    background-color: #000000 !important;
    padding-top: 0rem !important;
    padding-bottom: 2rem !important;
}
body, [class^="st"], [class*="st"] {
    font-family: 'Poppins', sans-serif !important;
    color: #334155 !important;
}
.main-header {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1.8rem;
    margin-top: 2.2rem;
    margin-bottom: 2rem;
}
.main-header img {
    border-radius: 50%;
    width: 120px;
    height: 120px;
    object-fit: cover;
    border: 3px solid #4f46e5;
    box-shadow: 0 0 25px rgba(79, 70, 229, 0.2);
}
.main-header-text h1 {
    color: #1e293b;
    font-weight: 700;
    font-size: 1.9rem;
}
.main-header-text p {
    color: #64748b;
    font-size: 0.9rem;
}
.sidebar-card {
    background: #000000;
    padding: 1rem;
    border-radius: 1rem;
    margin-bottom: 1rem;
    border: 1px solid #e2e8f0;
    box-shadow: 0 2px 6px rgba(0,0,0,0.05);
}
section[data-testid="stSidebar"] button {
    background: linear-gradient(90deg, #6366f1, #a5b4fc);
    color: #000000 !important;
    font-weight: 600;
    border-radius: 0.5rem;
    box-shadow: 0 2px 8px rgba(79,70,229,0.3);
    transition: all 0.2s ease-in-out;
}
section[data-testid="stSidebar"] button:hover {
    transform: scale(1.05);
    box-shadow: 0 0 20px rgba(99,102,241,0.4);
}
h2, h3, h4 {
    color: #334155 !important;
    text-align: center;
}
header, [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stSidebarCollapseButton"],
div[data-testid="stSidebarNav"] > div:nth-child(1) {
    display: none !important;
}
</style>
"""

# --- DARK THEME (Your Original Neon) ---
dark_theme = """
<style>
section[data-testid="stSidebar"] {
    background-color: #0b0f19 !important;
    padding: 1rem;
    border-right: 1px solid #1a1f2e;
}
.block-container {
    background-color: #0b0f19 !important;
    padding-top: 0rem !important;
    padding-bottom: 2rem !important;
}
body, [class^="st"], [class*="st"] {
    font-family: 'Poppins', sans-serif !important;
}
.main-header {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1.8rem;
    margin-top: 2.2rem;
    margin-bottom: 2rem;
}
.main-header img {
    border-radius: 50%;
    width: 120px;
    height: 120px;
    object-fit: cover;
    border: 3px solid #4dd4ac;
    box-shadow: 0 0 25px rgba(0, 255, 198, 0.6);
}
.main-header-text {
    text-align: center;
}
.main-header-text h1 {
    color: #4dd4ac;
    font-weight: 700;
    font-size: 1.9rem;
    margin-bottom: 0.2rem;
    text-shadow: 0 0 20px rgba(0, 255, 198, 0.6);
}
.main-header-text p {
    color: #d0d7e2;
    font-size: 0.9rem;
    margin-top: 0.1rem;
}
.sidebar-card {
    background: linear-gradient(135deg, #111827, #0b0f19);
    padding: 1rem;
    border-radius: 1rem;
    margin-bottom: 1rem;
    box-shadow: 0 0 12px rgba(0,255,198,0.2);
}
section[data-testid="stSidebar"] button {
    background: linear-gradient(90deg, #4dd4ac, #00cc99);
    color: #0b0f19 !important;
    font-weight: 600;
    border-radius: 0.5rem;
    box-shadow: 0 0 15px rgba(0,255,198,0.6);
    transition: all 0.2s ease-in-out;
}
section[data-testid="stSidebar"] button:hover {
    transform: scale(1.05);
    box-shadow: 0 0 25px rgba(0,255,198,0.8);
}
h2, h3, h4 {
    color: #4dd4ac !important;
    text-align: center;
    text-shadow: 0 0 12px rgba(0,255,198,0.6);
}
header, [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stSidebarCollapseButton"],
div[data-testid="stSidebarNav"] > div:nth-child(1) {
    display: none !important;
}
</style>
"""

# Apply theme based on choice
if theme_choice == "Light":
    st.markdown(light_theme, unsafe_allow_html=True)
else:
    st.markdown(dark_theme, unsafe_allow_html=True)

# Remove Streamlit’s sidebar toggle/header
st.markdown("""
<style>
[data-testid="stSidebarCollapseButton"],
div[data-testid="stSidebarNav"] > div:nth-child(1),
header[tabindex="0"] {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------
# SIDEBAR
# ---------------------------
with st.sidebar.container():
    try:
        st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
        uploaded_resume = st.file_uploader("📄 Upload Resume (TXT)", type=["txt"], key="resume_upload")
        if uploaded_resume:
            resume_text = uploaded_resume.getvalue().decode("utf-8")
            st.session_state["resume_text"] = resume_text
            st.success("Resume uploaded ✅")
        elif "resume_text" in st.session_state:
            resume_text = st.session_state["resume_text"]
        else:
            resume_text = None
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
        selected_role = st.text_input("Job Role", value="Product Manager")
        selected_cities = st.multiselect(
            "Choose Cities",
            options=[
                "Los Angeles", "New York", "San Jose", "San Francisco",
                "Seattle", "Austin", "Denver", "Texas", "Remote"
            ],
            default=["Los Angeles"]
        )
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
        st.subheader("🧑‍💻 Job Assistant")
        fetch_jobs = st.button("🔎 Fetch Latest Jobs")
        score_filter = st.slider("🎯 Minimum Match %", 0, 100, 70)
        st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"⚠️ Sidebar crashed: {e}")

# ---------------------------
# HEADER
# ---------------------------
if os.path.exists("profile.jpg"):
    with open("profile.jpg", "rb") as img_file:
        encoded_img = base64.b64encode(img_file.read()).decode()
    img_html = f'<img src="data:image/jpeg;base64,{encoded_img}" alt="Profile Picture">'
else:
    img_html = '<div style="width:120px;height:120px;border-radius:50%;border:3px solid #4dd4ac;box-shadow:0 0 25px rgba(0,255,198,0.6);background:#0b0f19;display:flex;align-items:center;justify-content:center;color:#4dd4ac;">No<br>Image</div>'

st.markdown(f"""
<div class="main-header">
    {img_html}
    <div class="main-header-text">
        <h1>Rachna's AI Assisted Job Hunt Agent</h1>
        <p>Easily track, analyze, and explore job opportunities tailored to your profile.</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------
# FETCH JOBS
# ---------------------------
if fetch_jobs:
    if not uploaded_resume:
        st.error("❌ Please upload your resume to fetching jobs.")
    else:
        with st.spinner("📱 Fetching and scoring jobs..."):
            os.environ["JOB_ROLE"] = selected_role
            os.environ["JOB_CITIES"] = json.dumps(selected_cities)
            subprocess.run(["python3", "job_scraper.py"])
        st.success("✅ Done! CSV updated.")

# ---------------------------
# LOAD JOB DATA
# ---------------------------
if os.path.exists("jobs_scored.csv"):
    df = pd.read_csv("jobs_scored.csv")
    filtered_df = df[df["Match %"] >= score_filter]

    col1, col2, col3 = st.columns(3)
    if not filtered_df.empty:
        total_jobs = int(len(filtered_df))
        avg_match = float(round(filtered_df["Match %"].mean(), 1))
        unique_companies = int(filtered_df["Company"].nunique())

        fig1 = go.Figure(go.Indicator(mode="gauge+number", value=total_jobs,
            title={"text": "Total Jobs"},
            gauge={"axis": {"range": [0, max(10, min(100, total_jobs+5))]},
                   "bar": {"color": "#4dd4ac"}}))
        col1.plotly_chart(fig1, use_container_width=True)

        fig2 = go.Figure(go.Indicator(mode="gauge+number+delta", value=avg_match,
            delta={"reference": 50},
            title={"text": "Avg. Match %"},
            gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#00e6a8"}}))
        col2.plotly_chart(fig2, use_container_width=True)

        fig3 = go.Figure(go.Indicator(mode="gauge+number", value=unique_companies,
            title={"text": "Unique Companies"},
            gauge={"axis": {"range": [0, max(5, min(50, unique_companies+2))]},
                   "bar": {"color": "#4dd4ac"}}))
        col3.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No jobs meet the current Match% filter.")

    st.subheader("📊 Job Distributions")
    if not filtered_df.empty:
        col1, col2 = st.columns(2)

        with col1:
            if "Source" in filtered_df.columns:
                source_counts = filtered_df.groupby("Source").size().reset_index(name="Count")
                source_chart = (
                    alt.Chart(source_counts)
                    .mark_arc(innerRadius=50)
                    .encode(
                        theta=alt.Theta(field="Count", type="quantitative"),
                        color=alt.Color(field="Source", type="nominal", scale=alt.Scale(scheme="tealblues")),
                        tooltip=["Source", "Count"]
                    )
                    .properties(title="Jobs by Source")
                )
                st.altair_chart(source_chart, use_container_width=True)

        with col2:
            if "Location" in filtered_df.columns:
                loc_chart = (
                    alt.Chart(filtered_df)
                    .mark_bar()
                    .encode(
                        x=alt.X(
                            "count():Q",
                            title="Number of Jobs",
                            axis=alt.Axis(format=".0f", tickMinStep=1)
                        ),
                        y=alt.Y("Location:N", sort='-x'),
                        color="Location:N",
                        tooltip=["Location", "count()"]
                    )
                    .properties(title="Jobs by Location", height=300)
                )
                st.altair_chart(loc_chart, use_container_width=True)  # ✅ inside the if block

        st.subheader("📋 Recommended Jobs")  # ✅ same indentation level
        if not filtered_df.empty:
            for city in filtered_df["Location"].unique():
                st.markdown(f"### 🏦 Jobs in {city}")
                city_df = filtered_df[filtered_df["Location"] == city].copy()
                city_df.reset_index(drop=True, inplace=True)
                city_df.index = city_df.index + 1
                st.dataframe(city_df, use_container_width=True)

            st.download_button("⬇️ Download CSV", data=filtered_df.to_csv(index=False), file_name="jobs_filtered.csv")
else:
    st.info("No jobs found yet. Use the sidebar to fetch jobs.")

# ---------------------------
# COVER LETTER GENERATOR
# ---------------------------
st.markdown('<div class="sidebar-card">', unsafe_allow_html=True)
st.subheader("📩 Generate Cover Letter")

job_desc = st.text_area(
    "Paste Job Description or select one from fetched results:",
    placeholder="Paste a job description here to generate a tailored cover letter...",
    height=150
)

if uploaded_resume:
    resume_text = uploaded_resume.read().decode("utf-8")

if st.button("📨 Create Cover Letter"):
    if not job_desc:
        st.warning("Please paste a job description first.")
    elif not resume_text:
        st.warning("Please upload your resume first.")
    else:
        with st.spinner("Crafting your personalized cover letter..."):
            prompt = f"""
            You are a professional career writer.
            Write a compelling, concise cover letter for the following job.
            Use the applicant's resume and the job description below.
            Make it confident, clear, and under 250 words.

            === Resume ===
            {resume_text}

            === Job Description ===
            {job_desc}

            Format it properly with greetings, body, and closing.
            """
            response = client.responses.create(model="gpt-4o-mini", input=prompt)

        st.markdown("### 📝 Your AI-Generated Cover Letter")
        st.success(response.output_text)
        st.download_button("⬇️ Download Cover Letter", data=response.output_text, file_name="Cover_Letter.txt")

st.markdown('</div>', unsafe_allow_html=True)

