import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Olist E-Commerce Analytics",
    page_icon="📦",
    layout="wide",
)

# ---------- Style ----------
st.markdown("""
<style>
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #EEF1F6;
        border-radius: 10px;
        padding: 14px 16px 10px 16px;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 12px;
        color: #6B7A99;
    }
    div[data-testid="stMetricValue"] {
        font-size: 24px;
        color: #0B1220;
    }
    h1, h2, h3 { color: #0B1220; }
    .insight-box {
        background: #F4F6FA;
        border-left: 3px solid #2F6FED;
        border-radius: 6px;
        padding: 10px 14px;
        font-size: 14px;
        color: #33415C;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

CHART_COLORS = ["#2F6FED", "#5B9BFF", "#F2A93B", "#0FAE7E", "#E85D5D", "#8B5CF6", "#22C1C3"]


@st.cache_data
def load_data():
    df = pd.read_parquet("data/olist_merged.parquet")
    df["order_purchase_timestamp"] = pd.to_datetime(df["order_purchase_timestamp"])
    return df


df = load_data()

# ---------- Sidebar filters ----------
st.sidebar.title("📦 Olist Analytics")
st.sidebar.caption("Brazilian e-commerce marketplace, 2016–2018")

years = sorted(df["order_year"].dropna().unique().tolist())
selected_years = st.sidebar.multiselect("Year", years, default=years)

states = sorted(df["customer_state"].dropna().unique().tolist())
selected_states = st.sidebar.multiselect("Customer state", states, default=[])

status_options = sorted(df["order_status"].dropna().unique().tolist())
selected_status = st.sidebar.multiselect("Order status", status_options, default=[])

st.sidebar.divider()
page = st.sidebar.radio("View", ["Executive overview", "Fulfillment & categories"])

# apply filters
filtered = df.copy()
if selected_years:
    filtered = filtered[filtered["order_year"].isin(selected_years)]
if selected_states:
    filtered = filtered[filtered["customer_state"].isin(selected_states)]
if selected_status:
    filtered = filtered[filtered["order_status"].isin(selected_status)]

if filtered.empty:
    st.warning("No data matches the current filters.")
    st.stop()

# ---------- Shared KPI calcs ----------
total_revenue = filtered["item_total"].sum()
total_orders = filtered["order_id"].nunique()
aov = total_revenue / total_orders if total_orders else 0
avg_review = filtered["review_score"].mean()
delivered = filtered.dropna(subset=["is_late"])
on_time_pct = (1 - delivered["is_late"].mean()) * 100 if len(delivered) else 0

# ============================================================
# PAGE 1 — EXECUTIVE OVERVIEW
# ============================================================
if page == "Executive overview":
    st.title("Executive overview")
    st.caption("Revenue, orders, and delivery performance across the marketplace")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total revenue", f"R$ {total_revenue/1_000_000:.2f}M")
    c2.metric("Total orders", f"{total_orders:,}")
    c3.metric("Avg order value", f"R$ {aov:.2f}")
    c4.metric("Avg review score", f"{avg_review:.2f} / 5")
    c5.metric("On-time delivery", f"{on_time_pct:.1f}%")

    st.divider()

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Monthly revenue trend")
        monthly = (
            filtered.groupby("order_month")["item_total"].sum()
            .reset_index()
            .sort_values("order_month")
        )
        fig = px.line(monthly, x="order_month", y="item_total", markers=True)
        fig.update_traces(line_color="#2F6FED", fill="tozeroy",
                           fillcolor="rgba(47,111,237,0.08)")
        fig.update_layout(
            height=340, margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis_title="", yaxis_title="Revenue (R$)",
            yaxis=dict(gridcolor="#EEF1F6"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Payment type mix")
        pay = filtered.drop_duplicates("order_id")["primary_payment_type"].value_counts().reset_index()
        pay.columns = ["payment_type", "count"]
        fig = px.pie(pay, names="payment_type", values="count", hole=0.65,
                     color_discrete_sequence=CHART_COLORS)
        fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10),
                           legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Revenue by state (top 10)")
        by_state = (
            filtered.groupby("customer_state")["item_total"].sum()
            .sort_values(ascending=False).head(10).reset_index()
        )
        fig = px.bar(by_state, x="item_total", y="customer_state", orientation="h",
                     color_discrete_sequence=["#2F6FED"])
        fig.update_layout(
            height=340, margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis_title="Revenue (R$)", yaxis_title="",
            yaxis=dict(categoryorder="total ascending"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Review score distribution")
        rev_dist = filtered.drop_duplicates("order_id")["review_score"].value_counts().sort_index().reset_index()
        rev_dist.columns = ["score", "count"]
        fig = px.bar(rev_dist, x="score", y="count", color_discrete_sequence=["#0FAE7E"])
        fig.update_layout(
            height=340, margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis_title="Review score", yaxis_title="Number of orders",
        )
        st.plotly_chart(fig, use_container_width=True)

    top_state = by_state.iloc[0]["customer_state"] if not by_state.empty else "N/A"
    top_state_share = by_state.iloc[0]["item_total"] / total_revenue * 100 if not by_state.empty else 0
    st.markdown(
        f"<div class='insight-box'>💡 <b>{top_state}</b> is the top revenue state, "
        f"contributing {top_state_share:.0f}% of total revenue in the current selection.</div>",
        unsafe_allow_html=True,
    )

# ============================================================
# PAGE 2 — FULFILLMENT & CATEGORIES
# ============================================================
else:
    st.title("Fulfillment & category performance")
    st.caption("Where orders drop off, and which categories drive revenue")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total orders", f"{total_orders:,}")
    c2.metric("Avg delivery time", f"{delivered['delivery_days'].mean():.1f} days" if len(delivered) else "n/a")
    c3.metric("Late deliveries", f"{delivered['is_late'].sum():,.0f}" if len(delivered) else "n/a")

    st.divider()

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("Order fulfillment funnel")
        orders_unique = filtered.drop_duplicates("order_id")
        total = len(orders_unique)
        approved = orders_unique["order_status"].isin(
            ["approved", "processing", "shipped", "delivered", "invoiced"]
        ).sum()
        shipped = orders_unique["order_status"].isin(["shipped", "delivered"]).sum()
        delivered_n = orders_unique["order_status"].eq("delivered").sum()

        funnel_df = pd.DataFrame({
            "stage": ["Purchased", "Approved", "Shipped", "Delivered"],
            "orders": [total, approved, shipped, delivered_n],
        })
        fig = go.Figure(go.Funnel(
            y=funnel_df["stage"], x=funnel_df["orders"],
            marker=dict(color=["#0B1220", "#1B3A78", "#2452A8", "#2F6FED"]),
            textinfo="value+percent initial",
        ))
        fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Top 10 categories by revenue")
        by_cat = (
            filtered.groupby("category_english")["item_total"].sum()
            .sort_values(ascending=False).head(10).reset_index()
        )
        fig = px.bar(by_cat, x="item_total", y="category_english", orientation="h",
                     color_discrete_sequence=["#2F6FED"])
        fig.update_layout(
            height=360, margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis_title="Revenue (R$)", yaxis_title="",
            yaxis=dict(categoryorder="total ascending"),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Average delivery days by state (top 10 by order volume)")
    top_states_by_vol = filtered["customer_state"].value_counts().head(10).index
    delivery_by_state = (
        delivered[delivered["customer_state"].isin(top_states_by_vol)]
        .groupby("customer_state")["delivery_days"].mean()
        .sort_values(ascending=False).reset_index()
    )
    fig = px.bar(delivery_by_state, x="customer_state", y="delivery_days",
                 color_discrete_sequence=["#F2A93B"])
    fig.update_layout(
        height=320, margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis_title="", yaxis_title="Avg delivery days",
    )
    st.plotly_chart(fig, use_container_width=True)

    slowest_state = delivery_by_state.iloc[0]["customer_state"] if not delivery_by_state.empty else "N/A"
    slowest_days = delivery_by_state.iloc[0]["delivery_days"] if not delivery_by_state.empty else 0
    st.markdown(
        f"<div class='insight-box'>💡 Among high-volume states, <b>{slowest_state}</b> has the "
        f"longest average delivery time at {slowest_days:.1f} days — a candidate for logistics review.</div>",
        unsafe_allow_html=True,
    )

st.sidebar.divider()
st.sidebar.caption("Data: Olist Brazilian E-Commerce Public Dataset (Kaggle)")
