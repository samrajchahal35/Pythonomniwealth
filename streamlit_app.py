import pandas as pd
import requests
import streamlit as st
import base64


# ==========================================
# 🔑 TRADING 212 CREDENTIALS
# ==========================================
# Put your Trading 212 API key and secret here.
T212_API_KEY_ID = "44325952ZfcWFQoiSdmGrgpQewEDYhvqwdSvt"
T212_SECRET_KEY = "JOLbvgAdJqf-sfifvrly4dIAiGruqijFDff844nFYbU"


# ==========================================
# 🧠 SESSION STATE
# ==========================================
if "bank_balance" not in st.session_state:
    st.session_state.bank_balance = 0.0

if "manual_accounts" not in st.session_state:
    st.session_state.manual_accounts = []


# ==========================================
# 📡 TRADING 212 API CONNECTOR
# ==========================================
def fetch_trading212_balance():

    url = "https://live.trading212.com/api/v0/equity/account/summary"

    try:
        # ------------------------------------------
        # Build HTTP Basic Authentication manually
        # ------------------------------------------
        credentials = f"{T212_API_KEY_ID.strip()}:{T212_SECRET_KEY.strip()}"

        encoded_credentials = base64.b64encode(
            credentials.encode("utf-8")
        ).decode("utf-8")

        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Accept": "application/json",
        }

        # ------------------------------------------
        # Make request
        # ------------------------------------------
        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )

        # ------------------------------------------
        # Successful connection
        # ------------------------------------------
        if response.status_code == 200:

            data = response.json()

            # Trading 212 account summary uses totalValue
            if "totalValue" in data:
                value = float(data["totalValue"])

                return value, "Connected"

            # If T212 changes the response structure
            return 0.0, f"Connected but totalValue missing: {data}"

        # ------------------------------------------
        # Authentication failure
        # ------------------------------------------
        elif response.status_code == 401:
            return (
                0.0,
                f"HTTP 401 Unauthorized: {response.text}"
            )

        # ------------------------------------------
        # Other HTTP error
        # ------------------------------------------
        else:
            return (
                0.0,
                f"HTTP {response.status_code}: {response.text}"
            )

    except requests.exceptions.Timeout:
        return 0.0, "Request timed out"

    except requests.exceptions.ConnectionError as e:
        return 0.0, f"Connection error: {str(e)}"

    except Exception as e:
        return 0.0, f"Error: {repr(e)}"


# ==========================================
# 🎨 STREAMLIT CONFIG
# ==========================================
st.set_page_config(
    page_title="OmniWealth Tracker",
    page_icon="💰",
    layout="wide"
)


# ==========================================
# 💰 TITLE
# ==========================================
st.title("💰 OmniWealth Net Worth Tracker")


# ==========================================
# 📡 FETCH LIVE DATA
# ==========================================
t212_val, t212_msg = fetch_trading212_balance()

bank_val = st.session_state.bank_balance


# ==========================================
# 📊 MANUAL ACCOUNTS
# ==========================================
manual_df = pd.DataFrame(st.session_state.manual_accounts)


if not manual_df.empty:

    manual_assets = manual_df[
        manual_df["type"] == "Asset"
    ]["balance"].sum()

    manual_liabilities = manual_df[
        manual_df["type"] == "Liability"
    ]["balance"].sum()

else:

    manual_assets = 0.0
    manual_liabilities = 0.0


# ==========================================
# 💷 TOTALS
# ==========================================
total_assets = (
    t212_val
    + bank_val
    + manual_assets
)

total_liabilities = manual_liabilities

net_worth = (
    total_assets
    - total_liabilities
)


# ==========================================
# 📈 TOP METRICS
# ==========================================
col1, col2, col3 = st.columns(3)

col1.metric(
    "Net Worth",
    f"£{net_worth:,.2f}"
)

col2.metric(
    "Total Assets",
    f"£{total_assets:,.2f}"
)

col3.metric(
    "Total Liabilities",
    f"-£{total_liabilities:,.2f}"
)


st.markdown("---")


# ==========================================
# 📑 TABS
# ==========================================
tab_overview, tab_manage, tab_banking = st.tabs(
    [
        "📊 Overview",
        "✏️ Manage Accounts",
        "🏦 Bank Accounts"
    ]
)


# ==========================================
# 📊 OVERVIEW TAB
# ==========================================
with tab_overview:

    c1, c2 = st.columns([1, 1])


    # ------------------------------------------
    # LIVE CONNECTION STATUS
    # ------------------------------------------
    with c1:

        st.subheader("Live Connections Status")

        if t212_msg == "Connected":

            st.success(
                f"Trading 212 Balance: £{t212_val:,.2f}"
            )

        else:

            st.error(
                f"Trading 212: £0.00 ({t212_msg})"
            )


        st.info(
            f"Bank Balance: £{bank_val:,.2f}"
        )


        # --------------------------------------
        # Refresh button
        # --------------------------------------
        if st.button(
            "🔄 Refresh Data",
            key="refresh_data"
        ):

            st.rerun()


    # ------------------------------------------
    # ASSET BREAKDOWN
    # ------------------------------------------
    with c2:

        st.subheader("Asset Breakdown")


        if total_assets > 0:

            accounts = []
            balances = []


            if t212_val > 0:

                accounts.append("Trading 212")
                balances.append(t212_val)


            if bank_val > 0:

                accounts.append("Bank Account")
                balances.append(bank_val)


            if not manual_df.empty:

                asset_accounts = manual_df[
                    manual_df["type"] == "Asset"
                ]

                for _, row in asset_accounts.iterrows():

                    accounts.append(row["name"])
                    balances.append(row["balance"])


            chart_data = pd.DataFrame(
                {
                    "Account": accounts,
                    "Balance": balances
                }
            )


            st.dataframe(
                chart_data,
                use_container_width=True,
                hide_index=True
            )


        else:

            st.info(
                "No active assets added yet."
            )


# ==========================================
# ✏️ MANAGE ACCOUNTS TAB
# ==========================================
with tab_manage:

    st.subheader("Add Manual Account")


    m_col1, m_col2 = st.columns([1, 2])


    # ------------------------------------------
    # ADD ACCOUNT
    # ------------------------------------------
    with m_col1:

        with st.form(
            "manual_form",
            clear_on_submit=True
        ):

            acc_name = st.text_input(
                "Account Name",
                placeholder="e.g. Dodl LISA"
            )


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
                ]
            )


            acc_type = st.radio(
                "Type",
                [
                    "Asset",
                    "Liability"
                ],
                horizontal=True
            )


            acc_bal = st.number_input(
                "Balance (£)",
                min_value=0.0,
                step=100.0
            )


            submitted = st.form_submit_button(
                "Save Account"
            )


            if submitted and acc_name:

                st.session_state.manual_accounts.append(
                    {
                        "id": len(
                            st.session_state.manual_accounts
                        ) + 1,

                        "name": acc_name,

                        "category": acc_cat,

                        "type": acc_type,

                        "balance": acc_bal,
                    }
                )

                st.success(
                    f"Saved {acc_name}"
                )

                st.rerun()


    # ------------------------------------------
    # EXISTING ACCOUNTS
    # ------------------------------------------
    with m_col2:

        st.subheader("Existing Accounts")


        if not manual_df.empty:

            st.dataframe(
                manual_df[
                    [
                        "id",
                        "name",
                        "category",
                        "type",
                        "balance"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )


            del_id = st.selectbox(
                "Select Account ID to Delete",
                manual_df["id"].tolist()
            )


            if st.button(
                "🗑️ Delete Selected Account"
            ):

                st.session_state.manual_accounts = [
                    account
                    for account
                    in st.session_state.manual_accounts
                    if account["id"] != del_id
                ]


                st.warning(
                    f"Deleted Account ID {del_id}"
                )


                st.rerun()


        else:

            st.info(
                "No manual accounts added."
            )


# ==========================================
# 🏦 BANKING TAB
# ==========================================
with tab_banking:

    st.subheader("Bank Balance Entry")


    new_bal = st.number_input(
        "Enter Total UK Bank Balance (£)",
        min_value=0.0,
        value=st.session_state.bank_balance,
        step=50.0
    )


    if st.button(
        "Save Bank Balance",
        key="save_bank_balance"
    ):

        st.session_state.bank_balance = new_bal

        st.success(
            f"Updated Bank Balance to £{new_bal:,.2f}"
        )

        st.rerun()
