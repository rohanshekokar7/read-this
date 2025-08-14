# file: hacathon_ai_ui_safe.py
# ------------------------------------------------------------
# Elyx Life – Member Journey Dashboard (AI-enhanced + Safe Column Handling)
# ------------------------------------------------------------
# ---------------- Dependency Check ----------------
import importlib.util
import sys

if importlib.util.find_spec("openpyxl") is None:
    import streamlit as st
    st.error("❌ Missing dependency: `openpyxl` is required to read Excel files.")
    st.markdown("**Install it using:**")
    st.code("pip install openpyxl", language="bash")
    st.stop()

import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime
import random

# ---------------- Mock AI WHY Generator ----------------
def ai_generate_rationale(tag, message, context=""):
    templates = {
        "medication": [
            "Based on your recent vitals and symptom trends, this medication was initiated to stabilize readings.",
            "Lab results indicate a need for intervention; hence this medicine is recommended."
        ],
        "plan_change": [
            "Feedback and adherence data suggested the need for a more adaptable plan.",
            "Observed barriers required tailoring the schedule to your lifestyle."
        ],
        "therapy": [
            "Therapy choice aligns with mobility goals and addresses identified pain points.",
            "Selected to target the root cause of recurring discomfort."
        ],
        "lifestyle": [
            "Optimized to boost daily energy and improve long-term cardiovascular health.",
            "Addresses stress patterns while supporting performance targets."
        ],
        "test_order": [
            "Diagnostic test ordered to confirm or rule out potential issues identified in prior screening.",
            "Necessary to validate suspected conditions before next intervention."
        ],
        "default": [
            "Decision guided by a holistic review of your data and health priorities.",
            "Action taken to maintain trajectory toward agreed health goals."
        ]
    }
    return random.choice(templates.get(tag.lower(), templates["default"]))

# ---------------- Utility Functions ----------------
def load_data(uploaded_file):
    if uploaded_file is None:
        df = pd.DataFrame([
            {"date": "2025-01-15 09:10", "sender": "Rohan Patel", "sender_type": "member",
             "tag": "general_query", "message": "BP monitor karna shuru karna hai."},
            {"date": "2025-01-15 11:40", "sender": "Ruby (Concierge)", "sender_type": "elyx",
             "tag": "plan_update", "message": "Baseline tests schedule ho rahe hain."},
            {"date": "2025-01-20 10:05", "sender": "Dr. Warren", "sender_type": "elyx",
             "tag": "medication", "message": "Blood pressure control ke liye Cozaar start karein."},
        ])
        return df, "Demo dataset"
    try:
        df = pd.read_excel(uploaded_file)
        return df, uploaded_file.name
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return pd.DataFrame(), None

def coerce_datetime(df):
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        df["date"] = pd.to_datetime("now")
    return df

def normalize_sender_type(sender):
    if not isinstance(sender, str):
        return "member"
    s = sender.lower()
    if any(k in s for k in ["coach", "nurse", "doctor", "concierge", "elyx", "dr", "team"]):
        return "elyx"
    return "member"

def apply_filters(df, date_range, sender_types, tags, text_query, case_sensitive=False):
    filtered = df.copy()
    if date_range and len(date_range) == 2:
        start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1]) + pd.Timedelta(days=1)
        filtered = filtered[(filtered["date"] >= start) & (filtered["date"] < end)]
    if sender_types:
        filtered = filtered[filtered["sender_type"].isin(sender_types)]
    if tags:
        filtered = filtered[filtered["tag"].astype(str).isin(tags)]
    if text_query:
        if case_sensitive:
            filtered = filtered[filtered["message"].astype(str).str.contains(text_query, na=False)]
        else:
            filtered = filtered[filtered["message"].astype(str).str.contains(text_query, case=False, na=False)]
    return filtered

# ---------------- UI Components ----------------
def draw_kpis(df):
    total_msgs = len(df)
    unique_tags = df["tag"].nunique()
    elyx_msgs = (df["sender_type"] == "elyx").sum()
    member_msgs = (df["sender_type"] == "member").sum()
    adherence_proxy = round((elyx_msgs / max(elyx_msgs + member_msgs, 1)) * 100, 1)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💬 Total Messages", total_msgs)
    c2.metric("🏷 Unique Tags", unique_tags)
    c3.metric("🤝 Elyx : Member", f"{elyx_msgs} : {member_msgs}")
    c4.metric("📈 Adherence (%)", adherence_proxy)

def draw_charts(df):
    if df.empty:
        st.info("No data for current filters.")
        return
    fig = px.scatter(
        df, x="date", y="sender", color="tag",
        hover_data=["message", "sender_type", "tag"],
        title="📅 Timeline of Interactions"
    )
    fig.update_traces(marker=dict(size=9))
    st.plotly_chart(fig, use_container_width=True)

    tag_counts = df["tag"].fillna("Unknown").value_counts().reset_index()
    tag_counts.columns = ["tag", "count"]
    bar = px.bar(tag_counts, x="tag", y="count", title="🏷 Messages per Tag")
    st.plotly_chart(bar, use_container_width=True)

    wk = df.set_index("date").resample("W")["message"].count().reset_index()
    wk.columns = ["week", "messages"]
    line = px.line(wk, x="week", y="messages", markers=True, title="📊 Weekly Volume")
    st.plotly_chart(line, use_container_width=True)

def daily_details(df):
    if df.empty:
        st.info("No data to show for daily details.")
        return
    sel_date = st.date_input("Select a date", df["date"].min().date())
    day_df = df[df["date"].dt.date == pd.to_datetime(sel_date).date()].sort_values("date")
    if day_df.empty:
        st.warning("No messages for this date.")
    else:
        for _, row in day_df.iterrows():
            st.markdown(f"**{row['sender']}** · _{row['tag']}_ · {row['date'].strftime('%Y-%m-%d %H:%M')}")
            st.write(row['message'])
            st.caption("🤖 " + ai_generate_rationale(row['tag'], row['message']))
            st.divider()

# ---------------- Main Layout ----------------
st.set_page_config(page_title="Elyx Member Journey", layout="wide")
st.markdown("<h1 style='color:#2E86C1;'>🏥 Elyx Life – AI-Enhanced Member Journey</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.header("📂 Load Dataset")
    uploaded = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])
    st.caption("Columns needed: date, sender, sender_type, tag, message")

    st.header("🔍 Filters")
    text_query = st.text_input("Search text")
    case_sensitive = st.checkbox("Case-sensitive search", value=False)

raw_df, file_name = load_data(uploaded)
df = coerce_datetime(raw_df)

# ✅ SAFE COLUMN HANDLING
required_cols = ["sender", "sender_type", "tag", "message"]
for col in required_cols:
    if col not in df.columns:
        if col == "sender_type":
            df[col] = "member"
        else:
            df[col] = None

df["sender_type"] = df["sender_type"].apply(normalize_sender_type)

with st.sidebar:
    if not df.empty:
        min_d, max_d = df["date"].min().date(), df["date"].max().date()
        date_range = st.date_input("Date range", (min_d, max_d))
        sender_types = st.multiselect("Sender types", df["sender_type"].unique(), default=list(df["sender_type"].unique()))
        tags_all = sorted(df["tag"].dropna().astype(str).unique())
        selected_tags = st.multiselect("Tags", tags_all, default=tags_all)
    else:
        date_range, sender_types, selected_tags = None, [], []

filtered_df = apply_filters(df, date_range, sender_types, selected_tags, text_query, case_sensitive)

st.subheader("📊 Key Metrics")
draw_kpis(filtered_df)

st.subheader("📈 Visual Analytics")
draw_charts(filtered_df)

st.subheader("🗓 Daily Conversation Details (AI WHY)")
daily_details(filtered_df)

if not filtered_df.empty:
    st.download_button(
        "💾 Download filtered data (CSV)",
        data=filtered_df.to_csv(index=False).encode("utf-8"),
        file_name="filtered_chat.csv",
        mime="text/csv"
    )
