import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Analytics Dashboard", layout="wide")

st.title("📊 FCRM Analytics & Coverage Insights")

# Load processed data
DATA_PATH = os.path.join("data", "processed", "coverage_report.csv")

if os.path.exists(DATA_PATH):
    df = pd.read_csv(DATA_PATH)
    st.success("Loaded coverage data successfully.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Coverage Distribution")
        fig1 = px.bar(df["coverage_status"].value_counts().reset_index(),
                      x="index", y="coverage_status",
                      labels={"index": "Coverage Status", "coverage_status": "Count"},
                      color="index")
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        st.subheader("💡 Risk Category Spread")
        if "risk_category" in df.columns:
            fig2 = px.pie(df, names="risk_category", title="Risk Category Distribution")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No risk_category column found in data.")

    st.subheader("🧩 Heatmap - TM Model Coverage vs Risks")
    if "risk" in df.columns and "tm_model" in df.columns:
        pivot = df.pivot_table(index="tm_model", columns="risk", values="coverage_status", aggfunc="count", fill_value=0)
        fig3 = px.imshow(pivot, text_auto=True, aspect="auto", color_continuous_scale="Blues")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.warning("Heatmap cannot be generated — missing risk or tm_model columns.")
    
    st.subheader("📥 Download Processed Data")
    st.download_button("Download Processed CSV", df.to_csv(index=False), "coverage_report.csv", "text/csv")
else:
    st.warning("No processed coverage report found. Please run ingestion first.")
