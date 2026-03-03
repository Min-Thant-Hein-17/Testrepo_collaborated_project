import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
from stellar_logic import analyze_stellar_account

# 1. Page Configuration
st.set_page_config(page_title="NUGpay Pro Dashboard", layout="wide")

# 2. Session State Initialization
if 'stellar_data' not in st.session_state:
    st.session_state.stellar_data = None
if 'last_id' not in st.session_state:
    st.session_state.last_id = ""

# 3. Sidebar
st.sidebar.header("Configuration")
user_account_id = st.sidebar.text_input("Stellar Account ID", placeholder="GDMMKKNI...")
analysis_months = st.sidebar.slider("Timeframe (Months)", 1, 12, 1)

# Action Buttons
col_side1, col_side2 = st.sidebar.columns(2)
run_btn = col_side1.button("Analyze Account", use_container_width=True)
clear_btn = col_side2.button("Clear Cache", use_container_width=True)

if clear_btn:
    st.session_state.stellar_data = None
    st.rerun()

if run_btn and user_account_id:
    with st.spinner("Fetching Blockchain Data..."):
        data = analyze_stellar_account(user_account_id, months=analysis_months)
        if data:
            st.session_state.stellar_data = data
            st.session_state.last_id = user_account_id
        else:
            st.error("No DMMK or nUSDT transactions found.")

# 4. Main Dashboard Logic
st.title("NUGpay User Analytics")

if st.session_state.stellar_data:
    df = pd.DataFrame(st.session_state.stellar_data)

    # --- ADVANCED TIME FILTERS ---
    st.subheader("Interactive Filters")
    t1, t2, t3 = st.columns(3)
    
    with t1:
        months = ["All Months"] + sorted(df['month_name'].unique().tolist())
        sel_month = st.selectbox("Filter by Month", months)
    with t2:
        # Show weeks only for selected month
        temp_df = df if sel_month == "All Months" else df[df['month_name'] == sel_month]
        weeks = ["All Weeks"] + sorted(temp_df['week_num'].unique().tolist())
        sel_week = st.selectbox("Filter by Week", weeks)
    with t3:
        recency = st.radio("Quick Tracker", ["Full History", "Last 7 Days", "Last 24 Hours"], horizontal=True)

    # Apply Filters
    filtered_df = df.copy()
    if sel_month != "All Months":
        filtered_df = filtered_df[filtered_df['month_name'] == sel_month]
    if sel_week != "All Weeks":
        filtered_df = filtered_df[filtered_df['week_num'] == sel_week]
    
    now = datetime.now(timezone.utc)
    if recency == "Last 7 Days":
        filtered_df = filtered_df[filtered_df['timestamp'] >= (now - timedelta(days=7))]
    elif recency == "Last 24 Hours":
        filtered_df = filtered_df[filtered_df['timestamp'] >= (now - timedelta(hours=24))]

    # --- SORTING & ASSETS ---
    st.markdown("---")
    f1, f2, f3 = st.columns(3)
    with f1:
        asset_choice = st.multiselect("Active Assets", ["DMMK", "nUSDT"], default=["DMMK", "nUSDT"])
        filtered_df = filtered_df[filtered_df['asset'].isin(asset_choice)]
    with f2:
        sort_order = st.selectbox("Order by Amount", ["Newest First", "Most to Least", "Least to Most"])
    with f3:
        top_10 = st.checkbox("Show Top 10 Accounts Only")

    # Sorting
    if sort_order == "Newest First":
        filtered_df = filtered_df.sort_values("timestamp", ascending=False)
    elif sort_order == "Most to Least":
        filtered_df = filtered_df.sort_values("amount", ascending=False)
    else:
        filtered_df = filtered_df.sort_values("amount", ascending=True)

    if top_10:
        top_list = filtered_df.groupby('other_account')['amount'].sum().nlargest(10).index
        filtered_df = filtered_df[filtered_df['other_account'].isin(top_list)]

    # --- DISPLAY ---
    def format_val(row):
        return f"{row['amount']:,.4f}" if row['asset'] == "DMMK" else f"{row['amount']:,.7f}"
    
    filtered_df['formatted_amount'] = filtered_df.apply(format_val, axis=1)

    st.dataframe(
        filtered_df[["timestamp", "direction", "other_account", "formatted_amount", "asset"]],
        use_container_width=True,
        hide_index=True
    )

    st.download_button("Export CSV", filtered_df.to_csv(index=False).encode('utf-8'), "nugpay_report.csv")

else:
    st.info("Enter a Stellar Account ID in the sidebar to begin.")