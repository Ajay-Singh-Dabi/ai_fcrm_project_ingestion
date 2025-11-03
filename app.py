import streamlit as st
import pandas as pd
import os
from utils.pdf_reader import read_text_from_file
from utils.ai_extractor import extract_red_flags
from utils.coverage_mapper import assess_coverage
from utils.web_scraper import fetch_fatf_reports, download_and_extract_pdf_text

st.set_page_config(page_title="AI FCRM - TM Coverage (Ingestion)", layout="wide")

st.title("🧠 AI Powered FCRM - TM Coverage (Ingestion)")

st.sidebar.header("Data Ingestion")
source_type = st.sidebar.selectbox("Source", ["Upload local file", "Fetch from FATF website"])
use_gpt = st.sidebar.checkbox("Use OpenAI GPT extractor", value=True)
use_semantic = st.sidebar.checkbox("Use semantic matching (SBERT)", value=True)
st.sidebar.markdown("---")
st.sidebar.markdown("Ingested files are saved under `data/ingested/` for reuse.")

text = ""
selected_report = None

if source_type == "Upload local file":
    uploaded_file = st.sidebar.file_uploader("Upload AML Report (TXT or PDF)", type=["txt", "pdf"])
    if uploaded_file is not None:
        text = read_text_from_file(uploaded_file)
        filename = uploaded_file.name
        # save raw uploaded file to ingested for traceability
        save_path = os.path.join("data", "ingested", filename)
        with open(save_path, "wb") as f:
            try:
                uploaded_file.seek(0)
                f.write(uploaded_file.read())
            except Exception:
                # uploaded_file may be a file-like with .getvalue()
                f.write(uploaded_file.getvalue())
else:
    st.sidebar.markdown("Fetching latest PDF reports from FATF website (titles & links)")
    try:
        reports = fetch_fatf_reports(limit=10)
        titles = [r["title"] for r in reports]
        selected = st.sidebar.selectbox("Select FATF report", ["-- pick one --"] + titles)
        if selected and selected != "-- pick one --":
            idx = titles.index(selected)
            selected_report = reports[idx]
            st.sidebar.write(f"Selected: {selected_report['title']}")
            if st.sidebar.button("Load selected report"):
                st.sidebar.info("Downloading and extracting PDF text...")
                text = download_and_extract_pdf_text(selected_report["url"])
                # save to ingested with safe name
                safe_name = selected_report['title'].replace("/", "_").replace(" ", "_")[:120] + ".txt"
                with open(os.path.join("data", "ingested", safe_name), "w", encoding="utf-8") as f:
                    f.write(text or "")
    except Exception as e:
        st.sidebar.error(f"Failed to fetch reports: {e}")

if text:
    st.subheader("📘 Extracted Summary & Risks")
    with st.spinner("Extracting risks using AI/NLP..."):
        extraction = extract_red_flags(text, use_gpt=use_gpt)
    st.markdown("**Structured Output (JSON)**:")
    st.json(extraction.get("structured", {}))
    st.markdown("**Fallback/Heuristic Phrases:**")
    st.write(extraction.get("extracted_phrases", []))
    st.subheader("📊 Coverage Assessment")
    with st.spinner("Assessing coverage against TM models..."):
        coverage_results = assess_coverage(extraction.get("extracted_phrases", []), semantic=use_semantic)
    df = pd.DataFrame(coverage_results)
    st.dataframe(df)
    st.subheader("📈 Coverage Status Distribution")
    dist = df['coverage_status'].value_counts().reset_index()
    dist.columns = ['coverage_status', 'count']
    st.bar_chart(dist.set_index('coverage_status'))
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Download coverage report (CSV)", csv, "coverage_report.csv", "text/csv")
else:
    st.info("Upload a TXT/PDF file or fetch a FATF report from the sidebar to begin.")
