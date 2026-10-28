import io
import json
import os
from typing import Any

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(
    page_title="Itsybitsy Enterprise Dashboard",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULT_API_URL = os.getenv("ITSYBITSY_API_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT = 25


def request_json(base_url: str, path: str, params: dict | None = None) -> Any:
    response = requests.get(
        f"{base_url.rstrip('/')}/{path.lstrip('/')}",
        params=params,
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json() if response.content else None


def post_json(base_url: str, path: str, params: dict | None = None, json_body: dict | None = None) -> Any:
    response = requests.post(
        f"{base_url.rstrip('/')}/{path.lstrip('/')}",
        params=params,
        json=json_body,
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json() if response.content else None


def records_from(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("items", "data", "products", "results", "records", "jobs", "history", "price_alerts"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def getv(row: dict, *keys: str, default: Any = None) -> Any:
    for key in keys:
        if row.get(key) is not None:
            return row[key]
    return default


@st.cache_data(ttl=30, show_spinner=False)
def load_endpoint(base_url: str, path: str) -> tuple[Any, str | None]:
    try:
        return request_json(base_url, path), None
    except Exception as exc:
        return None, str(exc)


def norm_products(products: list[dict]) -> pd.DataFrame:
    if not products:
        return pd.DataFrame()
    df = pd.json_normalize(products)
    rename = {
        "product_id": "Product ID", "ProductID": "Product ID", "id": "ID",
        "source_product_id": "Source Product ID", "SourceProductID": "Source Product ID",
        "upc": "UPC", "UPC": "UPC", "product_name": "Product Name",
        "ProductName": "Product Name", "name": "Name", "brand": "Brand",
        "Brand": "Brand", "category": "Category", "Category": "Category",
        "pack_size": "Pack Size", "PackSize": "Pack Size", "sku": "SKU",
        "regular_price": "Regular Price", "promotional_price": "Promotional Price",
        "price": "Price", "currency": "Currency", "availability": "Availability",
        "availability_label": "Availability", "availability_status": "Availability",
        "product_url": "Product URL", "url": "Product URL",
        "created_at": "Created At", "updated_at": "Updated At",
    }
    return df.rename(columns={k: v for k, v in rename.items() if k in df.columns})


st.title("🛍️ Itsybitsy Enterprise Product Platform")
st.caption("AI-Powered Scraping, Market Analytics, Price History & Real-Time Alerts")

with st.sidebar:
    st.header("⚙️ Settings & Connection")
    api_base = st.text_input("FastAPI Base URL", value=DEFAULT_API_URL).strip().rstrip("/")
    admin_key = st.text_input("Master API Token", value="itsybitsy_secret_token_2026", type="password")

    if st.button("🔄 Refresh Data Cache", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    page = st.radio(
        "Navigation Menu",
        [
            "📊 Executive Overview",
            "🔍 Products & Excel Export",
            "📈 Price Drop & History Tracker",
            "🤖 Smart Insights & Deals",
            "⚡ Scraper Control Center",
            "🔐 Multi-User API Keys",
            "🛠️ API Health & Docs"
        ],
    )
    st.divider()
    st.caption("Powered by FastAPI + MS SQL Server + Streamlit")

# Shared data loader
products_payload, products_error = load_endpoint(api_base, "/products")
products = records_from(products_payload)
df = norm_products(products)

# =====================================================================
# 1. EXECUTIVE OVERVIEW
# =====================================================================
if page == "📊 Executive Overview":
    st.subheader("📊 Executive Overview & Live Metrics")

    # Fetch insights from backend
    insights_data, insights_err = load_endpoint(api_base, "/analytics/insights")
    kpis = insights_data.get("kpis", {}) if insights_data else {}

    c1, c2, c3, c4 = st.columns(4)
    total_prod = kpis.get("total_products", len(products))
    avg_price = kpis.get("avg_promotional_price", 0) or kpis.get("avg_regular_price", 0)
    in_stock = kpis.get("in_stock_count", 0)
    out_stock = kpis.get("out_of_stock_count", 0)

    c1.metric("📦 Total Tracked Products", f"{total_prod:,}")
    c2.metric("🏷️ Avg Product Price", f"₹{avg_price:,.2f}")
    c3.metric("✅ In Stock", f"{in_stock:,}")
    c4.metric("⚠️ Out of Stock", f"{out_stock:,}", delta=f"-{out_stock}" if out_stock else None)

    st.markdown("---")

    if not df.empty:
        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("##### 🏷️ Category Distribution")
            if "Category" in df.columns:
                cat_counts = df["Category"].fillna("Other").value_counts().head(8).reset_index()
                cat_counts.columns = ["Category", "Count"]
                fig_cat = px.pie(cat_counts, names="Category", values="Count", hole=0.4, title="Top Categories")
                st.plotly_chart(fig_cat, use_container_width=True)

        with col_right:
            st.markdown("##### 📦 Availability Status")
            if "Availability" in df.columns:
                avail_counts = df["Availability"].fillna("Unknown").value_counts().reset_index()
                avail_counts.columns = ["Availability", "Count"]
                fig_avail = px.bar(avail_counts, x="Availability", y="Count", color="Availability", title="Stock Ratio")
                st.plotly_chart(fig_avail, use_container_width=True)

        st.subheader("🔥 Recently Updated Products")
        st.dataframe(df.head(10), use_container_width=True, hide_index=True)


# =====================================================================
# 2. PRODUCTS & EXCEL EXPORT (Feature #2)
# =====================================================================
elif page == "🔍 Products & Excel Export":
    st.subheader("🔍 Products Explorer & Multi-Format Export")
    if products_error:
        st.error(f"Could not load products: {products_error}")
    elif df.empty:
        st.info("No products found in the database.")
    else:
        # Search Box
        search = st.text_input("🔎 Search product name, SKU, Brand, or Category")
        filtered = df.copy()

        searchable = [c for c in filtered.columns if c.lower() in {
            "product name", "name", "source product id", "sku", "brand", "upc", "category"
        }]
        if search and searchable:
            mask = filtered[searchable].fillna("").astype(str).apply(
                lambda col: col.str.contains(search, case=False, regex=False)
            ).any(axis=1)
            filtered = filtered[mask]

        f1, f2, f3 = st.columns(3)
        if "Brand" in filtered.columns:
            brands = sorted(filtered["Brand"].dropna().astype(str).unique().tolist())
            selected_brands = f1.multiselect("Brand Filter", brands)
            if selected_brands:
                filtered = filtered[filtered["Brand"].astype(str).isin(selected_brands)]

        if "Category" in filtered.columns:
            categories = sorted(filtered["Category"].dropna().astype(str).unique().tolist())
            selected_categories = f2.multiselect("Category Filter", categories)
            if selected_categories:
                filtered = filtered[filtered["Category"].astype(str).isin(selected_categories)]

        if "Availability" in filtered.columns:
            availabilities = sorted(filtered["Availability"].dropna().astype(str).unique().tolist())
            selected_avail = f3.multiselect("Stock Status", availabilities)
            if selected_avail:
                filtered = filtered[filtered["Availability"].astype(str).isin(selected_avail)]

        st.markdown(f"**Found `{len(filtered):,}` matching products**")
        st.dataframe(filtered, use_container_width=True, hide_index=True)

        # Multi-Format Export Buttons (Excel + CSV)
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                "📥 Download as CSV",
                data=filtered.to_csv(index=False).encode("utf-8-sig"),
                file_name="itsybitsy_catalog.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_dl2:
            # Excel Buffer
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                filtered.to_excel(writer, index=False, sheet_name='Products')
            excel_data = excel_buffer.getvalue()

            st.download_button(
                "📗 Download as Excel (.xlsx)",
                data=excel_data,
                file_name="itsybitsy_catalog.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )


# =====================================================================
# 3. PRICE DROP & HISTORY TRACKER (Feature #1)
# =====================================================================
elif page == "📈 Price Drop & History Tracker":
    st.subheader("📈 Real-Time Price Changes & Stock Shift History")

    tab1, tab2 = st.tabs(["⚡ Recent Price Alerts", "🔍 Single Product History"])

    with tab1:
        st.markdown("##### 🚨 Recent Price Drops & Audit Trail")
        alerts_payload, alerts_err = load_endpoint(api_base, "/products/recent-price-drops?limit=50")
        alerts = records_from(alerts_payload)
        if alerts:
            alerts_df = pd.DataFrame(alerts)
            st.dataframe(alerts_df, use_container_width=True, hide_index=True)
        else:
            st.info("No price drop changes logged yet. As the scraper runs and detects price differences, they will be logged here.")

    with tab2:
        if not products:
            st.info("No products available.")
        else:
            product_dict = {
                f"{p.get('product_name', 'Product')} (ID: {p.get('product_id', p.get('ProductID'))})": p.get('product_id', p.get('ProductID'))
                for p in products if p.get('product_id') or p.get('ProductID')
            }
            selected_label = st.selectbox("Select a Product to view Price History", list(product_dict.keys()))
            pid = product_dict[selected_label]

            if st.button("Fetch Historical Log", use_container_width=True):
                hist_payload, hist_err = load_endpoint(api_base, f"/products/{pid}/history")
                if hist_err:
                    st.error(f"Error fetching history: {hist_err}")
                else:
                    hist_items = hist_payload.get("history", [])
                    if hist_items:
                        st.success(f"Found {len(hist_items)} historical event(s) for this item.")
                        st.json(hist_items)
                    else:
                        st.info("This product has not experienced price/stock modifications since its initial scraping.")


# =====================================================================
# 4. SMART INSIGHTS & TOP DEALS (Feature #4 & #5)
# =====================================================================
elif page == "🤖 Smart Insights & Deals":
    st.subheader("🤖 Smart Product Insights & High Discount Deals")
    insights_data, insights_err = load_endpoint(api_base, "/analytics/insights")

    if insights_err:
        st.error(f"Error calculating insights: {insights_err}")
    elif insights_data:
        deals = insights_data.get("top_deals", [])
        if deals:
            st.markdown("### 🔥 Top Discounted Deals Today")
            st.caption("Automatically detected by comparing regular price vs promotional price")
            deals_df = pd.DataFrame(deals)
            st.dataframe(deals_df, use_container_width=True, hide_index=True)

            # Bar chart of top deals
            fig_deals = px.bar(
                deals_df,
                x="product_name",
                y="discount_percentage",
                color="discount_percentage",
                title="Top Discount % by Product",
                labels={"product_name": "Product", "discount_percentage": "Discount (%)"}
            )
            st.plotly_chart(fig_deals, use_container_width=True)
        else:
            st.info("No promotional discount differences recorded in the current dataset.")


# =====================================================================
# 5. SCRAPER CONTROL CENTER (Feature #3)
# =====================================================================
elif page == "⚡ Scraper Control Center":
    st.subheader("⚡ Automated Scraper Control & Job Scheduling")
    st.markdown("Run collection jobs directly from this dashboard without opening a terminal command prompt.")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("##### 🚀 On-Demand Scraper Trigger")
        max_items = st.slider("Max products to scrape in this run", min_value=1, max_value=20, value=5)
        if st.button("▶️ Launch Background Scraper Now", type="primary", use_container_width=True):
            try:
                res = post_json(api_base, f"/scraper/trigger?max_products={max_items}")
                st.success(f"🎉 {res.get('message')} (Process PID: {res.get('pid')})")
            except Exception as e:
                st.error(f"Failed to trigger scraper: {e}")

    with col2:
        st.markdown("##### ⏱️ Cron Schedule Info")
        st.info("Daily automatic collection job is registered to run through `daily_mdf_job.py`. You can also trigger it anytime on the left.")

    st.markdown("---")
    st.markdown("##### 📋 Recent Scraping Jobs Log")
    jobs_payload, jobs_err = load_endpoint(api_base, "/collection-jobs")
    jobs = records_from(jobs_payload)
    if jobs:
        jobs_df = pd.DataFrame(jobs)
        st.dataframe(jobs_df, use_container_width=True, hide_index=True)
    else:
        st.info("No jobs recorded or `/collection-jobs` endpoint response is pending.")


# =====================================================================
# 6. MULTI-USER API KEYS (Feature #6)
# =====================================================================
elif page == "🔐 Multi-User API Keys":
    st.subheader("🔐 Multi-Tenant API Key Management")
    st.markdown("Generate and manage secured API keys for different clients, third-party partners, or mobile apps.")

    with st.expander("➕ Generate New Client API Key", expanded=True):
        client_name = st.text_input("Client / Partner Name", placeholder="e.g. Acme Corp / Mobile App")
        role = st.selectbox("Role", ["client", "partner", "analyst"])
        if st.button("Generate API Key", type="primary"):
            if not client_name:
                st.warning("Please provide a client name.")
            else:
                try:
                    res = post_json(
                        api_base,
                        f"/admin/api-keys?admin_token={admin_key}",
                        json_body={"client_name": client_name, "role": role}
                    )
                    st.success(f"🎉 New API Key Generated: `{res.get('api_key')}`")
                    st.json(res)
                except Exception as e:
                    st.error(f"Error creating API Key: {e}")

    st.markdown("##### 📋 Active Client Keys")
    try:
        keys_payload = request_json(api_base, f"/admin/api-keys?admin_token={admin_key}")
        if keys_payload and "keys" in keys_payload:
            keys_df = pd.DataFrame(keys_payload["keys"])
            st.dataframe(keys_df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.warning(f"Could not load API keys: {e}")


# =====================================================================
# 7. API HEALTH & DOCS
# =====================================================================
elif page == "🛠️ API Health & Docs":
    st.subheader("🛠️ API Health & Swagger Documentation")
    st.write(f"**FastAPI Host:** `{api_base}`")

    health_payload, health_error = load_endpoint(api_base, "/health/db")
    if health_error:
        st.error(f"Database Health Check Failed: {health_error}")
    else:
        st.success("Database Connection: OK")
        st.json(health_payload)

    st.link_button("📖 Open Interactive Swagger API Docs (/docs)", f"{api_base}/docs", use_container_width=True)
