import base64
import pandas as pd
import requests
import streamlit as st

# ==========================================
# 🔑 CREDENTIALS
# ==========================================
API_KEY_ID = "44325952ZfcWFQoiSdmGrgpQewEDYHvqwdSvt"
API_SECRET = "JOLbvgAdJqf-sfifvrly4dlAiGruqijFDff844nFYbU"

# Set to True ONLY if generated in Practice / Demo mode
IS_DEMO = False

# ==========================================
# 🧠 PERSISTENT SESSION STATE
# ==========================================
if "bank_balance" not in st.session_state:
    st.session_state.bank_balance = 0.0

if "manual_accounts" not in st.session_state:
    st.session_state.manual_accounts = []


# ==========================================
# 📡 TRADING 212 API CONNECTOR
# ==========================================
def fetch_trading212_balance():
    clean_id = API_KEY_ID.strip().replace("\n", "").replace("\r", "")
    clean_secret = API_SECRET.strip().replace("\n", "").replace("\r", "")

    if not clean_id or not clean_secret:
        return 0.0, "Missing Keys"

    domain = "demo.trading212.com" if IS_DEMO else "live.trading212.com"
    url = f"https://{domain}/api/v0/equity/account/summary"

    # Standard Trading 212 API Header: Basic Base64(KEY_ID:API_SECRET)
    raw_creds = f"{clean_id}:{clean_secret}"
    encoded_creds = base64.b64encode(raw_creds.encode("utf-8")).decode("utf-8")

    headers = {
        "Authorization": f"Basic {encoded_creds}",
        "User-Agent": "OmniWealth/1.0",
        "Accept": "application/json",
    }

    try:
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code == 200:
            data = res.json()
            val = data.get("totalValue", data.get("total", 0.0))
            return float(val), "Connected"
        else:
            return 0.0, f"HTTP {res.status_code}"
    except Exception as e:
        return 0.0, f"Error: {str(e)}"


# ==========================================
# 🎨 STREAMLIT DASHBOARD UI
# ==========================================
st.set_page_config(page_title="OmniWealth Tracker", page_icon="💰", layout="wide")

st.title("💰 OmniWealth Net Worth Tracker")

t212_val, t212_msg = fetch_trading212_balance()
bank_val = st.session_state.bank_balance

manual_df = pd.DataFrame(st.session_state.manual_accounts)
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

# METRICS
col1, col2, col3 = st.columns(3)
col1.metric("Net Worth", f"£{net_worth:,.2f}")
col2.metric("Total Assets", f"£{total_assets:,.2f}")
col3.metric("Total Liabilities", f"-£{total_liabilities:,.2f}")

st.markdown("---")

tab_overview, tab_manage, tab_banking = st.tabs(
    ["📊 Overview", "✏️ Manage Accounts", "🏦 Bank Accounts"]
)

with tab_overview:
    c1, c2 = st.columns([1, 1])

    with c1:
        st.subheader("Live Connections Status")
        if t212_msg == "Connected":
            st.success(f"Trading 212 Balance: £{t212_val:,.2f} ({t212_msg})")
        else:
            st.error(f"Trading 212: £0.00 ({t212_msg})")

        st.info(f"Bank Balance: £{bank_val:,.2f}")

        if st.button("🔄 Refresh Data"):
            st.rerun()

    with c2:
        st.subheader("Asset Breakdown")
        if total_assets > 0:
            chart_data = pd.DataFrame(
                {
                    "Account": (
                        (["Trading 212"] if t212_val > 0 else [])
                        + (["Bank Account"] if bank_val > 0 else [])
                        + (
                            manual_df[manual_df["type"] == "Asset"]["name"].tolist()
                            if not manual_df.empty
                            else []
                        )
                    ),
                    "Balance": (
                        ([t212_val] if t212_val > 0 else [])
                        + ([bank_val] if bank_val > 0 else [])
                        + (
                            manual_df[manual_df["type"] == "Asset"]["balance"].tolist()
                            if not manual_df.empty
                            else []
                        )
                    ),
                }
            )
            st.dataframe(chart_data, use_container_width=True)
        else:
            st.info("No active assets added yet.")

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
                st.session_state.manual_accounts.append(
                    {
                        "id": len(st.session_state.manual_accounts) + 1,
                        "name": acc_name,
                        "category": acc_cat,
                        "type": acc_type,
                        "balance": acc_bal,
                    }
                )
                st.success(f"Saved {acc_name}")
                st.rerun()

    with m_col2:
        st.subheader("Existing Accounts")
        if not manual_df.empty:
            st.dataframe(
                manual_df[["id", "name", "category", "type", "balance"]],
                use_container_width=True,
            )

            del_id = st.selectbox(
                "Select Account ID to Delete", manual_df["id"].tolist()
            )
            if st.button("🗑️ Delete Selected Account"):
                st.session_state.manual_accounts = [
                    a for a in st.session_state.manual_accounts if a["id"] != del_id
                ]
                st.warning(f"Deleted Account ID {del_id}")
                st.rerun()
        else:
            st.info("No manual accounts added.")

with tab_banking:
    st.subheader("Bank Balance Entry")
    new_bal = st.number_input(
        "Enter Total UK Bank Balance (£)",
        min_value=0.0,
        value=st.session_state.bank_balance,
        step=50.0,
    )
    if st.button("Save Bank Balance"):
        st.session_state.bank_balance = new_bal
        st.success(f"Updated Bank Balance to £{new_bal:,.2f}")
        st.rerun()
