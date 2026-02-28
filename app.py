import streamlit as st
import pandas as pd
import plotly.express as px
from stellar_logic import analyze_stellar_account

# 1. Page Configuration
st.set_page_config(
    page_title="NUGpay Analytics Dashboard",
    page_icon="💎",
    layout="wide"
)

# 2. Sidebar
st.sidebar.header("Configuration")
user_account_id = st.sidebar.text_input(
    "Stellar Account ID", 
    placeholder="GDMMKKNI...",
)

analysis_months = st.sidebar.slider(
    "Timeframe (Months)", 1, 12, 1
)

run_button = st.sidebar.button("Analyze Account", use_container_width=True)

# 3. Main Dashboard Logic
st.title("NUGpay User Analytics")
st.markdown("---")

if run_button and user_account_id:
    with st.spinner("Connecting to Stellar Horizon..."):
        results = analyze_stellar_account(user_account_id, months=analysis_months)

    if results:
        metadata = results['account_metadata']
        # Convert raw list to DataFrame
        df = pd.DataFrame(results['raw_transactions'])

        # --- DATA FIXES FOR VISUALIZATION ---
        # 1. Force Amount to be a float (solves empty graph issue)
        df["amount"] = pd.to_numeric(df["amount"], errors='coerce')
        # 2. Convert timestamp strings to actual datetime objects
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        # 3. Sort by time to ensure lines/bars flow correctly
        df = df.sort_values("timestamp")

        # --- ROW 1: Metric Cards ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Inflow", f"{metadata['total_in']} units")
        col2.metric("Total Outflow", f"{metadata['total_out']} units")
        col3.metric("Net Flow", f"{metadata['net_flow']} units")
        col4.metric("Total Transactions", metadata['tx_frequency'])

        # --- ROW 2: Graphs ---
        st.subheader("Financial Visualization")
        chart_col, pie_col = st.columns([2, 1])

        with chart_col:
            # Main Bar Chart
            fig = px.bar(
                df, 
                x="timestamp", 
                y="amount", 
                color="direction",
                title="Daily Transaction Volume",
                color_discrete_map={"INCOMING": "#2ecc71", "OUTGOING": "#e74c3c"},
                template="plotly_white",
                barmode="group"
            )
            # Add a trend line to see spending/receiving patterns
            fig.update_traces(marker_line_width=0)
            st.plotly_chart(fig, use_container_width=True)

        with pie_col:
            # Donut chart for composition
            fig_pie = px.pie(
                df, values='amount', names='direction', 
                hole=0.5, title="Volume Composition",
                color="direction",
                color_discrete_map={"INCOMING": "#2ecc71", "OUTGOING": "#e74c3c"}
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- ROW 3: Data Analysis Table ---
        st.subheader("Data Analysis Table (ML Ready)")
        
        # Adding a filter for the table
        filter_type = st.selectbox("Filter by Type", ["All"] + list(df['type'].unique()))
        
        display_df = df if filter_type == "All" else df[df['type'] == filter_type]
        
        st.dataframe(
            display_df[["timestamp", "direction", "amount", "asset", "counterparty", "type"]],
            use_container_width=True,
            hide_index=True
        )

        # Download Button
        csv = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Export Cleaned Data for ML Training",
            data=csv,
            file_name=f"stellar_ml_data_{user_account_id[:8]}.csv",
            mime='text/csv',
        )

    else:
        st.error("No data found. Check if the Account ID is correct.")

else:
    st.info("Enter a Stellar Public Key in the sidebar to start.")



