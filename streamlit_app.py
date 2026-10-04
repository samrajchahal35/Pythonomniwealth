import base64
import datetime
import sqlite3
import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st

# ==========================================
# 🔑 YOUR CREDENTIALS
# ==========================================
T212_API_KEY_ID = "44325952ZqvqzThpqXFkTOTzpZNXItUEtoCRx"
T212_SECRET_KEY = "IK_uSnsJpyQ1JiK2M4BSfuzejEq1Pu3xRItCXFkzqc4"

# Optional: Add GoCardless Secret ID & Key from bankaccountdata.gocardless.com
GOCARDLESS_SECRET_ID = ""
GOCARDLESS_SECRET_KEY = ""

DB_FILE = "omniwealth.db"


# ==========================================
# 🗄️ DATABASE SETUP
# ==========================================
def init_db():
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute("""
        CREATE TABLE IF NOT EXISTS manual_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            type TEXT NOT NULL,
            balance REAL NOT NULL,
            last_updated TEXT NOT NULL
        )
    """)
  c.execute("""
        CREATE TABLE IF NOT EXISTS api_balances (
            key_name TEXT PRIMARY KEY,
            balance REAL NOT NULL
        )
    """)
  conn.commit()
  conn.close()


init_db()


# ==========================================
# 📡 TRADING 212 API (PROPER BASIC AUTH)
# ==========================================
def fetch_trading212_balance():
  if not T212_API_KEY_ID or not T212_SECRET_KEY:
    return 0.0, "Missing API Key or Secret"

  url = "https://live.trading212.com/api/v0/equity/account/summary"

  # Base64 Encode API_KEY_ID:SECRET_KEY
  credentials = f"{T212_API_KEY_ID.strip()}:{T212_SECRET_KEY.strip()}"
  encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode(
      "utf-8"
  )

  headers = {
      "Authorization": f"Basic {encoded_credentials}",
      "Content-Type": "application/json",
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
# 🛠️ DATABASE HELPERS
# ==========================================
def get_manual_accounts():
  conn = sqlite3.connect(DB_FILE)
  df = pd.read_sql_query("SELECT * FROM manual_accounts", conn)
  conn.close()
  return df


def save_manual_account(name, category, acc_type, balance):
  now = datetime.date.today().strftime("%Y-%m-%d")
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute(
      "INSERT INTO manual_accounts (name, category, type, balance, last_updated)"
      " VALUES (?, ?, ?, ?, ?)",
      (name, category, acc_type, balance, now),
  )
  conn.commit()
  conn.close()


def delete_manual_account(acc_id):
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute("DELETE FROM manual_accounts WHERE id=?", (acc_id,))
  conn.commit()
  conn.close()


def get_bank_balance():
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute(
      "SELECT balance FROM api_balances WHERE key_name='open_banking'"
  )
  row = c.fetchone()
  conn.close()
  return row[0] if row else 0.0


def set_bank_balance(bal):
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute(
      "INSERT OR REPLACE INTO api_balances (key_name, balance) VALUES"
      " ('open_banking', ?)",
      (bal,),
  )
  conn.commit()
  conn.close()


# ==========================================
# 🎨 DASHBOARD UI
# ==========================================
st.set_page_config(
    page_title="OmniWealth Tracker", page_icon="💰", layout="wide"
)

st.title("💰 OmniWealth Net Worth Tracker")

t212_val, t212_msg = fetch_trading212_balance()
bank_val = get_bank_balance()

manual_df = get_manual_accounts()
manual_assets = (
    manual_df[manual_df["type"] == "Asset"]["balance"].sum()
    if not manual_df.empty
    else 0.0
)
manual_liabilities = (
    manual_df[manual_df["type"] == "Liability"]["balance"].sum()
    if not manual_df.empty
    else 0.0
)

total_assets = t212_val + bank_val + manual_assets
total_liabilities = manual_liabilities
net_worth = total_assets - total_liabilities

# TOP METRICS
col1, col2, col3 = st.columns(3)
col1.metric("Net Worth", f"£{net_worth:,.2f}")
col2.metric("Total Assets", f"£{total_assets:,.2f}")
col3.metric("Total Liabilities", f"-£{total_liabilities:,.2f}")

st.markdown("---")

tab_overview, tab_manage, tab_banking = st.tabs(
    ["📊 Overview", "✏️ Manage Manual Accounts", "🏦 Open Banking"]
)

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
      for _, row in manual_df[manual_df["type"] == "Asset"].iterrows():
        labels.append(row["name"])
        values.append(row["balance"])

    if values:
      fig, ax = plt.subplots(figsize=(5, 3), facecolor="#0E1117")
      ax.pie(
          values,
          labels=labels,
          autopct="%1.1f%%",
          textprops={"color": "w"},
          colors=["#10B981", "#3B82F6", "#8B5CF6", "#F59E0B", "#EC4899"],
      )
      ax.set_title("Asset Allocation", color="white")
      st.pyplot(fig)
    else:
      st.info("No active assets to display.")

  with c2:
    st.subheader("Live Connections")
    if t212_msg == "Connected":
      st.success(f"Trading 212 Balance: £{t212_val:,.2f} ({t212_msg})")
    else:
      st.error(f"Trading 212: £0.00 ({t212_msg})")

    st.info(f"Open Banking Balance: £{bank_val:,.2f}")

    if st.button("🔄 Refresh Data"):
      st.rerun()

with tab_manage:
  st.subheader("Add Manual Account")
  m_col1, m_col2 = st.columns([1, 2])

  with m_col1:
    with st.form("manual_form", clear_on_submit=True):
      acc_name = st.text_input("Account Name", placeholder="e.g. Dodl LISA")
      acc_cat = st.selectbox(
          "Category",
          [
              "ISA / LISA",
              "Pension",
              "Property",
              "Savings",
              "Crypto",
              "Loan / Debt",
              "Other",
          ],
      )
      acc_type = st.radio("Type", ["Asset", "Liability"], horizontal=True)
      acc_bal = st.number_input("Balance (£)", min_value=0.0, step=100.0)

      if st.form_submit_button("Save Account") and acc_name:
        save_manual_account(acc_name, acc_cat, acc_type, acc_bal)
        st.success(f"Saved {acc_name}")
        st.rerun()

  with m_col2:
    st.subheader("Existing Accounts")
    if not manual_df.empty:
      st.dataframe(
          manual_df[
              ["id", "name", "category", "type", "balance", "last_updated"]
          ],
          use_container_width=True,
      )

      del_id = st.selectbox(
          "Select Account ID to Delete", manual_df["id"].tolist()
      )
      if st.button("🗑️ Delete Selected Account"):
        delete_manual_account(del_id)
        st.warning(f"Deleted Account ID {del_id}")
        st.rerun()
    else:
      st.info("No manual accounts stored.")

with tab_banking:
  st.subheader("Open Banking Balance")
  override_val = st.number_input(
      "Enter Total Bank Balance (£)", min_value=0.0, value=bank_val, step=50.0
  )
  if st.button("Save Open Banking Balance"):
    set_bank_balance(override_val)
    st.success(f"Updated Open Banking Balance to £{override_val:,.2f}")
    st.rerun()
