import streamlit as st
import pandas as pd
import numpy as np
import duckdb
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os

from settings import DATA_DIR

# Page configuration
st.set_page_config(
    page_title="AGIDash - AGI Perception Cascade Monitor",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title and description
st.title("🧠 AGIDash")
st.subheader("Bayesian early-warning dashboard for an AGI-perception cascade")

# Connect to DuckDB
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_data():
    """Load data from DuckDB"""
    db_path = DATA_DIR / "agidash.duckdb"
    if not os.path.exists(db_path):
        st.warning("Database not found. Please run data ingestion first.")
        return None, None
    
    con = duckdb.connect(str(db_path))
    
    # Get the indices data
    indices_df = pd.DataFrame(con.execute("""
        SELECT * FROM daily_index
        ORDER BY date DESC
        LIMIT 180
    """).fetchall())
    
    if not indices_df.empty:
        indices_df.columns = ['date', 'capability', 'attention', 'market', 'regulatory']
        indices_df['date'] = pd.to_datetime(indices_df['date'])
        indices_df = indices_df.sort_values('date')
    
    # Get the alerts data
    alerts_df = pd.DataFrame(con.execute("""
        SELECT * FROM alerts
        ORDER BY date DESC
        LIMIT 180
    """).fetchall())
    
    if not alerts_df.empty:
        alerts_df.columns = ['date', 'capability_prob', 'attention_prob', 'market_prob', 'regulatory_prob', 'alert']
        alerts_df['date'] = pd.to_datetime(alerts_df['date'])
        alerts_df = alerts_df.sort_values('date')
    
    con.close()
    return indices_df, alerts_df

# Load the data
indices_df, alerts_df = load_data()

if indices_df is not None and not indices_df.empty:
    # Status card
    status_container = st.container()
    
    # Check for any recent alerts
    recent_alert = False
    high_prob = False
    if alerts_df is not None and not alerts_df.empty:
        last_week = datetime.now() - timedelta(days=7)
        recent_alerts = alerts_df[alerts_df['date'] >= last_week]
        recent_alert = any(recent_alerts['alert'])
        
        # Check if any probability is above 0.3 (warning level)
        last_probs = alerts_df.iloc[-1][['capability_prob', 'attention_prob', 'market_prob', 'regulatory_prob']]
        high_prob = any(last_probs > 0.3)
    
    # Determine status
    if recent_alert:
        status_color = "red"
        status_text = "ALERT: Change point detected!"
    elif high_prob:
        status_color = "orange"
        status_text = "WARNING: Elevated change point probability"
    else:
        status_color = "green"
        status_text = "NORMAL: No significant change points"
    
    # Display status
    with status_container:
        st.markdown(f"""
        <div style="
            padding: 20px;
            border-radius: 10px;
            background-color: {status_color};
            color: white;
            text-align: center;
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 20px;
        ">
            {status_text}
        </div>
        """, unsafe_allow_html=True)
    
    # Create a 2x2 grid layout for our four indices
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)
    
    # Capability Index
    with col1:
        st.subheader("Capability Index")
        fig = px.line(indices_df, x='date', y='capability', 
                    title='AI Capability Progression',
                    labels={'capability': 'Z-Score', 'date': 'Date'})
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    # Attention Index
    with col2:
        st.subheader("Attention Index")
        fig = px.line(indices_df, x='date', y='attention', 
                    title='Public Attention to AI',
                    labels={'attention': 'Z-Score', 'date': 'Date'})
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    # Market Index
    with col3:
        st.subheader("Market Index")
        fig = px.line(indices_df, x='date', y='market', 
                    title='AI Markets',
                    labels={'market': 'Z-Score', 'date': 'Date'})
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    # Regulatory Index
    with col4:
        st.subheader("Regulatory Index")
        fig = px.line(indices_df, x='date', y='regulatory', 
                    title='Regulatory Activity',
                    labels={'regulatory': 'Z-Score', 'date': 'Date'})
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    # Change point probability heatmap
    if alerts_df is not None and not alerts_df.empty:
        st.subheader("Change Point Probability Heatmap")
        
        # Prepare data for heatmap
        heatmap_data = alerts_df[['date', 'capability_prob', 'attention_prob', 'market_prob', 'regulatory_prob']]
        heatmap_data = heatmap_data.set_index('date')
        
        # Create the heatmap
        fig = px.imshow(
            heatmap_data.T,
            labels=dict(x="Date", y="Index", color="Probability"),
            x=heatmap_data.index,
            y=['Capability', 'Attention', 'Market', 'Regulatory'],
            color_continuous_scale='Viridis'
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Display the latest probabilities
        st.subheader("Latest Change Point Probabilities")
        latest = alerts_df.iloc[-1]
        
        # Create a 1x4 grid for metrics
        m1, m2, m3, m4 = st.columns(4)
        
        with m1:
            color = "red" if latest['capability_prob'] >= 0.5 else "orange" if latest['capability_prob'] >= 0.3 else "green"
            st.metric("Capability", f"{latest['capability_prob']:.2f}", delta=None,
                    delta_color="normal")
        
        with m2:
            color = "red" if latest['attention_prob'] >= 0.5 else "orange" if latest['attention_prob'] >= 0.3 else "green"
            st.metric("Attention", f"{latest['attention_prob']:.2f}", delta=None,
                    delta_color="normal")
        
        with m3:
            color = "red" if latest['market_prob'] >= 0.5 else "orange" if latest['market_prob'] >= 0.3 else "green"
            st.metric("Market", f"{latest['market_prob']:.2f}", delta=None,
                    delta_color="normal")
        
        with m4:
            color = "red" if latest['regulatory_prob'] >= 0.5 else "orange" if latest['regulatory_prob'] >= 0.3 else "green"
            st.metric("Regulatory", f"{latest['regulatory_prob']:.2f}", delta=None,
                    delta_color="normal")
    
else:
    st.warning("No data available. Please run the data pipeline first.")
    st.info("To run the pipeline, execute the following in your terminal:")
    st.code("docker-compose up -d")
    st.info("Then, navigate to the Dagster UI at http://localhost:3000 and manually trigger a backfill.")
