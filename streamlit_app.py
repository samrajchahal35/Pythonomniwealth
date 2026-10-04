import sqlite3
import requests
import datetime
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# ==========================================
# 🔑 CREDENTIALS & CONFIGURATION
# ==========================================
T212_API_KEY_ID = "44325952ZqvqzThpqXFkTOTzpZNXItUEtoCRx"
T212_SECRET_KEY = "IK_uSnsJpyQ1JiK2M4BSfuzejEq1Pu3xRItCXFkzqc4"

PLAID_CLIENT_ID = "6ac26ec74b48b1000df508bd"
PLAID_SECRET = "a9a14167cb418c333b0a0a5ca3102b"
PLAID_ENV = "development"
PLAID_ACCESS_TOKENS = []

DB_FILE = "omniwealth.db"

# ==========================================
# 🗄️ DATABASE SETUP
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS manual_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            type TEXT NOT NULL,
            balance REAL NOT NULL,
            last_updated TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            net_worth REAL NOT NULL,
            total_assets REAL NOT NULL,
            total_liabilities REAL NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 📡 LIVE API CONNECTORS
# ==========================================
def fetch_trading212_balance():
    if not T212_API_KEY_ID or not T212_SECRET_KEY:
        return 0.0, "API credentials missing"
    
    url = "https://live.trading212.com/api/v0/equity/account/summary"
    try:
        response = requests.get(
            url, 
            auth=(T212_API_KEY_ID.strip(), T212_SECRET_KEY.strip()), 
            headers={"Content-Type": "application/json"},
            timeout=8
        )
        if response.status_code == 200:
            return float(response.json().get("total", 0.0)), "OK"
        else:
            return 0.0, f"HTTP {response.status_code}"
    except Exception as e:
        return 0.0, str(e)

def fetch_plaid_balances():
    if not PLAID_CLIENT_ID or not PLAID_SECRET or not PLAID_ACCESS_TOKENS:
        return 0.0, "No active Plaid tokens"

    url = f"https://{PLAID_ENV}.plaid.com/accounts/balance/get"
    total_bank_balance = 0.0

    for token in PLAID_ACCESS_TOKENS:
        payload = {
            "client_id": PLAID_CLIENT_ID,
            "secret": PLAID_SECRET,
            "access_token": token
        }
        try:
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                for acc in res.json().get("accounts", []):
                    total_bank_balance += float(acc.get("balances", {}).get("current", 0.0))
        except Exception:
            pass

    return total_bank_balance, "OK"

# ==========================================
# 🛠️ DATABASE HELPERS
# ==========================================
def get_manual_accounts():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM manual_accounts", conn)
    conn.close()
    return df

def save_manual_account(name, category, acc_type, balance, acc_id=None):
    now = datetime.date.today().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if acc_id:
        c.execute("UPDATE manual_accounts SET name=?, category=?, type=?, balance=?, last_updated=? WHERE id=?",
                  (name, category, acc_type, balance, now, acc_id))
    else:
        c.execute("INSERT INTO manual_accounts (name, category, type, balance, last_updated) VALUES (?, ?, ?, ?, ?)",
                  (name, category, acc_type, balance, now))
    conn.commit()
    conn.close()

def delete_manual_account(acc_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM manual_accounts WHERE id=?", (acc_id,))
    conn.commit()
    conn.close()

# ==========================================
# 🎨 STREAMLIT WEB GUI
# ==========================================
st.set_page_config(page_title="OmniWealth Tracker", page_icon="💰", layout="wide")

st.title("💰 OmniWealth Net Worth Tracker")
st.caption("Pure Python Web Dashboard with Direct Trading 212 API")

# --- FETCH LIVE BALANCES ---
t212_val, t212_msg = fetch_trading212_balance()
plaid_val, _ = fetch_plaid_balances()

manual_df = get_manual_accounts()
manual_assets = manual_df[manual_df['type'] == 'Asset']['balance'].sum() if not manual_df.empty else 0.0
manual_liabilities = manual_df[manual_df['type'] == 'Liability']['balance'].sum() if not manual_df.empty else 0.0

total_assets = t212_val + plaid_val + manual_assets
total_liabilities = manual_liabilities
net_worth = total_assets - total_liabilities

# --- TOP METRICS ---
col1, col2, col3 = st.columns(3)
col1.metric("Net Worth", f"£{net_worth:,.2f}")
col2.metric("Total Assets", f"£{total_assets:,.2f}")
col3.metric("Total Liabilities", f"-£{total_liabilities:,.2f}")

st.markdown("---")

# --- TABS ---
tab_overview, tab_manage = st.tabs(["📊 Overview & Breakdown", "✏️ Manage Accounts"])

with tab_overview:
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.subheader("Asset Breakdown")
        labels = []
        values = []

        if t212_val > 0:
            labels.append("Trading 212")
            values.append(t212_val)
        if plaid_val > 0:
            labels.append("Open Banking")
            values.append(plaid_val)

        if not manual_df.empty:
            for _, row in manual_df[manual_df['type'] == 'Asset'].iterrows():
                labels.append(row['name'])
                values.append(row['balance'])

        if values:
            fig, ax = plt.subplots(figsize=(5, 3), facecolor="#0E1117")
            ax.pie(values, labels=labels, autopct='%1.1f%%', textprops={'color': 'w'})
            ax.set_title("Asset Allocation", color="white")
            st.pyplot(fig)
        else:
            st.info("No active assets to display.")

    with c2:
        st.subheader("Live Status")
        st.success(f"Trading 212 Balance: £{t212_val:,.2f} ({t212_msg})")
        st.info(f"Open Banking Balance: £{plaid_val:,.2f}")
        if st.button("🔄 Refresh APIs"):
            st.rerun()

with tab_manage:
    st.subheader("Add or Edit Manual Account")
    
    m_col1, m_col2 = st.columns([1, 2])
    
    with m_col1:
        with st.form("manual_form", clear_on_submit=True):
            acc_name = st.text_input("Account Name", placeholder="e.g. Dodl LISA")
            acc_cat = st.selectbox("Category", ["ISA / LISA", "Pension", "Property", "Savings", "Crypto", "Loan / Debt", "Other"])
            acc_type = st.radio("Type", ["Asset", "Liability"], horizontal=True)
            acc_bal = st.number_input("Balance (£)", min_value=0.0, step=100.0)
            
            submit = st.form_submit_button("Save Account")
            if submit and acc_name:
                save_manual_account(acc_name, acc_cat, acc_type, acc_bal)
                st.success(f"Saved {acc_name}")
                st.rerun()

    with m_col2:
        st.subheader("Existing Accounts")
        if not manual_df.empty:
            st.dataframe(manual_df[['id', 'name', 'category', 'type', 'balance', 'last_updated']], use_container_width=True)
            
            del_id = st.selectbox("Select Account ID to Delete", manual_df['id'].tolist())
            if st.button("🗑️ Delete Selected Account"):
                delete_manual_account(del_id)
                st.warning(f"Deleted Account ID {del_id}")
                st.rerun()
        else:
            st.info("No manual accounts stored.")
                         
