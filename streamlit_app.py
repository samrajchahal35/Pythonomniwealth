import base64
import requests
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# ==========================================
# 🔑 CREDENTIALS
# ==========================================
T212_API_KEY_ID = "44325952ZqvqzThpqXFkTOTzpZNXItUEtoCRx"
T212_SECRET_KEY = "IK_uSnsJpyQ1JiK2M4BSfuzejEq1Pu3xRItCXFkzqc4"

# ==========================================
# 🧠 SESSION STATE
# ==========================================
if "open_banking_balance" not in st.session_state:
    st.session_state.open_banking_balance = 0.0

if "manual_accounts" not in st.session_state:
    st.session_state.manual_accounts = []

# ==========================================
# 📡 TRADING 212 API (WITH CUSTOM USER-AGENT)
# ==========================================
def fetch_trading212_balance():
    if not T212_API_KEY_ID or not T212_SECRET_KEY:
        return 0.0, "Missing API Credentials"
    
    url = "https://live.trading212.com/api/v0/equity/account/summary"
    
    # Base64 Basic Auth string
    raw_creds = f"{T212_API_KEY_ID.strip()}:{T212_SECRET_KEY.strip()}"
    encoded_creds = base64.b64encode(raw_creds.encode('utf-8')).decode('utf-8')
    
    headers = {
        "Authorization": f"Basic {encoded_creds}",
        "User-Agent": "OmniWealth/1.0 (Mozilla/5.0)",
        "Content-Type": "application/json"
    }

    try:
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code == 200:
            total = float(res.json().get("total", 0.0))
            return total, "Connected"
        else:
            return 0.0, f"HTTP {res.status_code}"
    except Exception as e:
        return 0.0, f"Error: {str(e)}"

# ==========================================
# 🎨 STREAMLIT DASHBOARD
# ==========================================
st.set_page_config(page_title="OmniWealth Tracker", page_icon="💰", layout="wide")

st.title("💰 OmniWealth Net Worth Tracker")

t212_val, t212_msg = fetch_trading212_balance()
bank_val = st.session_state.open_banking_balance

manual_df = pd.DataFrame(st.session_state.manual_accounts)
manual_assets = manual_df[manual_df['type'] == 'Asset']['balance'].sum() if not manual_df.empty else 0.0
manual_liabilities = manual_df[manual_df['type'] == 'Liability']['balance'].sum() if not manual_df.empty else 0.0

total_assets = t212_val + bank_val + manual_assets
total_liabilities = manual_liabilities
net_worth = total_assets - total_liabilities

# METRICS DISPLAY
col1, col2, col3 = st.columns(3)
col1.metric("Net Worth", f"£{net_worth:,.2f}")
col2.metric("Total Assets", f"£{total_assets:,.2f}")
col3.metric("Total Liabilities", f"-£{total_liabilities:,.2f}")

st.markdown("---")

tab_overview, tab_manage, tab_banking = st.tabs(["📊 Overview", "✏️ Manage Accounts", "🏦 Open Banking"])

with tab_overview:
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.subheader("Asset Breakdown")
        labels = []
        values = []

        if t212_val > 0:
            labels.append("Trading 212")
            values.append(t212_val)
        if bank_val > 0:
            labels.append("Open Banking")
            values.append(bank_val)

        if not manual_df.empty:
            for _, row in manual_df[manual_df['type'] == 'Asset'].iterrows():
                labels.append(row['name'])
                values.append(row['balance'])

        if values:
            fig, ax = plt.subplots(figsize=(5, 3), facecolor="#0E1117")
            ax.pie(values, labels=labels, autopct='%1.1f%%', textprops={'color': 'w'}, colors=['#10B981', '#3B82F6', '#8B5CF6', '#F59E0B', '#EC4899'])
            ax.set_title("Asset Allocation", color="white")
            st.pyplot(fig)
        else:
            st.info("No active assets added yet.")

    with c2:
        st.subheader("Live Status")
        if t212_msg == "Connected":
            st.success(f"Trading 212 Balance: £{t212_val:,.2f} ({t212_msg})")
        else:
            st.error(f"Trading 212: £0.00 ({t212_msg})")
            
        st.info(f"Open Banking Balance: £{bank_val:,.2f}")
        
        if st.button("🔄 Refresh Data"):
            st.rerun()

with tab_manage:
    st.subheader("Add Account")
    m_col1, m_col2 = st.columns([1, 2])
    
    with m_col1:
        with st.form("manual_form", clear_on_submit=True):
            acc_name = st.text_input("Account Name", placeholder="e.g. Dodl LISA")
            acc_cat = st.selectbox("Category", ["ISA / LISA", "Pension", "Property", "Savings", "Crypto", "Loan / Debt", "Other"])
            acc_type = st.radio("Type", ["Asset", "Liability"], horizontal=True)
            acc_bal = st.number_input("Balance (£)", min_value=0.0, step=100.0)
            
            if st.form_submit_button("Save Account") and acc_name:
                new_id = len(st.session_state.manual_accounts) + 1
                st.session_state.manual_accounts.append({
                    'id': new_id, 'name': acc_name, 'category': acc_cat, 
                    'type': acc_type, 'balance': acc_bal
                })
                st.success(f"Saved {acc_name}")
                st.rerun()

    with m_col2:
        st.subheader("Existing Accounts")
        if not manual_df.empty:
            st.dataframe(manual_df[['id', 'name', 'category', 'type', 'balance']], use_container_width=True)
            
            del_id = st.selectbox("Select Account ID to Delete", manual_df['id'].tolist())
            if st.button("🗑️ Delete Selected Account"):
                st.session_state.manual_accounts = [a for a in st.session_state.manual_accounts if a['id'] != del_id]
                st.warning(f"Deleted Account ID {del_id}")
                st.rerun()
        else:
            st.info("No manual accounts stored.")

with tab_banking:
    st.subheader("Open Banking Balance Entry")
    new_bal = st.number_input("Enter Total Bank Balance (£)", min_value=0.0, value=st.session_state.open_banking_balance, step=50.0)
    if st.button("Save Open Banking Balance"):
        st.session_state.open_banking_balance = new_bal
        st.success(f"Updated Open Banking Balance to £{new_bal:,.2f}")
        st.rerun()
