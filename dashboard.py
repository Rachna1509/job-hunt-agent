from openai import OpenAI
import tempfile
import soundfile as sf
import streamlit as st
import pandas as pd
import subprocess
import os
import json
import re
import altair as alt

# --- INIT OPENAI CLIENT ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- PAGE CONFIG ---
st.set_page_config(page_title="Job Hunt Agent", page_icon="💼", layout="wide")

# --- SIDEBAR CONFIG ---
st.sidebar.header("🔍 Search Settings")

# Resume upload
uploaded_resume = st.sidebar.file_uploader("📄 Upload Resume (resume.txt)", type=["txt"])

# Job role and cities
selected_role = st.sidebar.text_input("Job Role", value="Product Manager")
selected_cities = st.sidebar.multiselect(
    "Choose Cities",
    options=["Los Angeles", "New York", "San Francisco", "Seattle", "Austin", "Remote"],
    default=["Los Angeles"]
)

# --- SIDEBAR INTERACTIONS ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/briefcase.png", width=60)
    st.title("🎯 Job Assistant")
    st.markdown("Talk or upload your request for personalized job search.")

    st.subheader("🎙️ Voice Command")
    audio_file = st.file_uploader("Upload WAV or M4A", type=["wav", "m4a"])

    fetch_jobs = st.button("🔎 Fetch Latest Jobs")
    score_filter = st.slider("🎯 Minimum Match %", 0, 100, 70)

# --- MAIN CONTENT ---
st.title("💼 Job Hunt Agent Dashboard")
st.markdown("Use the sidebar to record voice, fetch jobs and explore matches below:")

# --- FETCH JOBS ---
if fetch_jobs:
    if uploaded_resume is not None:
        resume_text = uploaded_resume.read().decode("utf-8")
        with open("resume.txt", "w") as f:
            f.write(resume_text)
    else:
        st.error("Please upload a resume.txt file to proceed.")
        st.stop()

    with st.spinner("📡 Fetching and scoring jobs..."):
        os.environ["JOB_ROLE"] = selected_role
        os.environ["JOB_CITIES"] = json.dumps(selected_cities)
        subprocess.run(["python3", "job_scraper.py"])
    st.success("✅ Done! CSV updated.")

# --- LOAD JOBS ---
if os.path.exists("jobs_scored.csv"):
    df = pd.read_csv("jobs_scored.csv")
    filtered_df = df[df["Match %"] >= score_filter]

    # Summary Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("🧮 Total Jobs", len(filtered_df))
    col2.metric("📊 Avg. Match %", f"{filtered_df['Match %'].mean():.1f}%" if not filtered_df.empty else "N/A")
    col3.metric("💼 Unique Companies", filtered_df['Company'].nunique() if not filtered_df.empty else 0)

    # Charts
    st.subheader("📈 Visual Insights")
    if not filtered_df.empty:
        if 'Source' in filtered_df.columns:
            source_chart = alt.Chart(filtered_df).mark_arc(innerRadius=30).encode(
                theta=alt.Theta(field="Source", type="nominal", aggregate="count"),
                color=alt.Color(field="Source", type="nominal"),
                tooltip=["Source", "Company"]
            ).properties(title="Jobs by Source")
            st.altair_chart(source_chart, use_container_width=True)

        if 'Location' in filtered_df.columns:
            loc_chart = alt.Chart(filtered_df).mark_bar().encode(
                x=alt.X("count():Q", title="Number of Jobs"),
                y=alt.Y("Location:N", sort='-x'),
                color="Location:N",
                tooltip=["Location", "Company"]
            ).properties(title="Jobs by Location", height=300)
            st.altair_chart(loc_chart, use_container_width=True)

    # Show jobs per city
    st.subheader("📊 Top Matching Jobs")
    for city in filtered_df["Location"].unique():
        st.markdown(f"### 🌆 Jobs in {city}")
        st.dataframe(filtered_df[filtered_df["Location"] == city], use_container_width=True)

    # Download
    st.download_button("⬇️ Download CSV", data=filtered_df.to_csv(index=False), file_name="jobs_filtered.csv")
else:
    st.info("No jobs found yet. Use the sidebar to fetch jobs.")

# --- AUDIO TRANSCRIPTION ---
if audio_file is not None:
    st.subheader("🗣️ Transcription Result")
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{audio_file.name.split('.')[-1]}") as tmp:
            tmp.write(audio_file.getbuffer())
            audio_path = tmp.name

        with open(audio_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=f,
                temperature=0
            )

        cmd = transcript.text.strip()
        st.success(f"👉 You said: **{cmd}**")

        # Parse: "Find jobs as Data Analyst in New York"
        role_match = re.search(r'(?:as|for)\s+([\w\s]+?)\s+(?:in|at)\s+([\w\s]+)', cmd.lower())
        if role_match:
            parsed_role = role_match.group(1).title().strip()
            parsed_city = role_match.group(2).title().strip()
        else:
            parsed_role = selected_role
            parsed_city = selected_cities[0]

        if uploaded_resume is not None:
            resume_text = uploaded_resume.read().decode("utf-8")
            with open("resume.txt", "w") as f:
                f.write(resume_text)
        else:
            st.error("Please upload a resume.txt file to proceed.")
            st.stop()

        os.environ["JOB_ROLE"] = parsed_role
        os.environ["JOB_CITIES"] = json.dumps([parsed_city])
        st.info(f"📡 Running job search for **{parsed_role}** in **{parsed_city}**...")
        subprocess.run(["python3", "job_scraper.py"])
        st.success("✅ Job search complete. Refresh sidebar to view updated data.")
    except Exception as e:
        st.error(f"❌ Error transcribing audio: {e}")
