# file: hacathon_ai_ui_safe.py
# ------------------------------------------------------------
# Elyx Life – Member Journey Dashboard
# (AI-enhanced + Safe Column Handling + Health Reports + Persona Profile
#  + Dynamic Episodes + Demo Generator + Safe PDF Export + Safe Forecast)
# ------------------------------------------------------------

# ---------------- Streamlit must be configured FIRST ----------------
import importlib.util

import streamlit as st
st.set_page_config(page_title="Elyx Member Journey", layout="wide")

# ---------------- Dependency guards (nice UI if missing) ------------
_missing_msgs = []

def _has(pkg: str) -> bool:
    return importlib.util.find_spec(pkg) is not None

NEED_OPENPYXL = not _has("openpyxl")
HAVE_REPORTLAB = _has("reportlab")
HAVE_SKLEARN = _has("sklearn")

if NEED_OPENPYXL:
    _missing_msgs.append(
        "❌ Missing dependency: **openpyxl** is required to read Excel files.\n"
        "Install with: `pip install openpyxl`"
    )

if not HAVE_REPORTLAB:
    _missing_msgs.append(
        "ℹ️ PDF export uses **reportlab**. It’s optional. "
        "Install with: `pip install reportlab`"
    )

if not HAVE_SKLEARN:
    _missing_msgs.append(
        "ℹ️ Forecasting uses **scikit-learn** if available. "
        "Without it, a NumPy fallback is used. "
        "Install with: `pip install scikit-learn`"
    )

if _missing_msgs:
    with st.sidebar:
        st.markdown("### Environment checks")
        for m in _missing_msgs:
            st.info(m)

# ---------------- Imports (core) ------------------------------------
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, time
import numpy as np
import random

# reportlab (optional)
if HAVE_REPORTLAB:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    import io

# sklearn (optional)
if HAVE_SKLEARN:
    from sklearn.linear_model import LinearRegression

# ---------------- Custom Styling ------------------------------------
st.markdown(
    """
    <style>
    .block-container {padding-top:2rem; padding-bottom:2rem;}
    h1, h2, h3 {color:#2E86C1;}
    .stMetric {background:#fff; border-radius:12px;
               box-shadow: 0px 2px 6px rgba(0,0,0,0.1); padding:10px;}
    </style>
    """, unsafe_allow_html=True
)

# ---------------- Simple Login --------------------------------------
def login():
    st.title("🔐 Elyx Life – Secure Login")

    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")

            if submit:
                if username == "rohan" and password == "elyx123":   # demo credentials
                    st.session_state["authenticated"] = True
                    st.success("✅ Login successful!")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")

    return st.session_state["authenticated"]

# Force login before dashboard
if not login():
    st.stop()

# ---------------- Persona-aware AI WHY Generator ---------------------
def ai_generate_rationale(tag, message, context=""):
    tag = str(tag).lower()
    ctx = (context or "") + " " + (message or "")
    ctx_low = ctx.lower()

    if tag == "medication":
        if "blood pressure" in ctx_low or "bp" in ctx_low or "hypertension" in ctx_low:
            return "Medication prescribed due to consistently elevated BP, considering Rohan's family history of heart disease."
        return "Medication started to reduce cardiovascular risk in line with Rohan’s long-term goals."
    if tag in ("plan_update", "plan_change"):
        if "travel" in ctx_low or "flight" in ctx_low or "jet lag" in ctx_low:
            return "Plan adjusted to accommodate frequent international travel and jet-lag management."
        return "Plan updated due to observed adherence challenges and work schedule constraints."
    if tag == "therapy":
        return "Therapy chosen to improve mobility and manage stress from high-pressure sales role."
    if tag == "lifestyle":
        if "sleep" in ctx_low:
            return "Lifestyle change focused on sleep hygiene to support recovery and HRV."
        return "Lifestyle recommendation to improve stress resilience and cardiovascular fitness."
    if tag == "test_order":
        return "Quarterly diagnostics scheduled to track lipids, ApoB, and BP as part of proactive risk management."
    if tag == "general_query" and any(w in ctx_low for w in ["frustrated", "slow", "confused", "delay"]):
        return "Member feedback flagged; team coordinating clearer, proactive communication and consolidated updates."
    return "Decision based on Rohan’s goals, current biomarkers, and persona context."

# ---------------- Persona State Inference ----------------------------
PERSONA_CONTEXT = {
    "stress": "High stress job, frequent travel, family history of heart disease",
    "goals": ["reduce heart risk", "improve cognition", "balance career and family"]
}

def infer_persona_state(message, tag):
    """Infer before/after emotional state based on tag + message content + persona."""
    msg = str(message).lower()
    before, after = "Neutral", "Engaged"
    conf = 0.8

    if any(w in msg for w in ["frustrated", "delay", "slow", "confused"]):
        before, after = "Frustrated", "Reassured after Elyx response"
        conf = 0.9
    elif tag == "medication":
        before, after = "Anxious about risk", "Confident risk managed"
    elif tag in ["plan_update", "plan_change"]:
        before, after = "Uncertain about schedule", "Motivated after plan adaptation"
    elif tag == "therapy":
        before, after = "Experiencing pain/stiffness", "Hopeful with therapy start"
    elif tag == "lifestyle":
        before, after = "Stressed with habits", "Engaged in new routines"

    return {"before": before, "after": after, "confidence": conf}

# ---------------- Utility Functions ---------------------------------
def load_data(uploaded_file):
    """Load Excel or return tiny demo if nothing uploaded."""
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

    if NEED_OPENPYXL:
        st.error("`openpyxl` is required to read Excel files. Please install it: `pip install openpyxl`.")
        return pd.DataFrame(), None

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
    if any(k in s for k in ["coach", "nurse", "doctor", "concierge", "elyx", "dr", "team", "physio", "diet"]):
        return "elyx"
    return "member"

def apply_filters(df, date_range, sender_types, tags, text_query, case_sensitive=False):
    filtered = df.copy()
    if date_range and len(date_range) == 2:
        start = pd.to_datetime(date_range[0])
        end = pd.to_datetime(date_range[1]) + pd.Timedelta(days=1)
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

# ---------------- PDF Export (safe) ----------------------------------
def export_pdf(profile_text, episodes, persona_timeline, forecast_data):
    if not HAVE_REPORTLAB:
        st.warning("PDF export is unavailable because `reportlab` is not installed.")
        return None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("Elyx Life – Member Report", styles['Title']))
    elements.append(Spacer(1, 12))

    # Profile
    elements.append(Paragraph("👤 Member Profile", styles['Heading2']))
    elements.append(Paragraph(profile_text, styles['Normal']))
    elements.append(Spacer(1, 12))

    # Episodes
    elements.append(Paragraph("📌 Detected Episodes", styles['Heading2']))
    if episodes:
        for ep in episodes:
            elements.append(Paragraph(f"<b>{ep['title']}</b>", styles['Heading3']))
            elements.append(Paragraph(f"Trigger: {ep['trigger']}", styles['Normal']))
            elements.append(Paragraph(f"Outcome: {ep['outcome']}", styles['Normal']))
            elements.append(Spacer(1, 6))
    else:
        elements.append(Paragraph("No episodes detected.", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Persona timeline
    elements.append(Paragraph("🧠 Persona State Evolution", styles['Heading2']))
    if persona_timeline is not None and not persona_timeline.empty:
        data = [persona_timeline.columns.tolist()] + persona_timeline.astype(str).values.tolist()
        table = Table(data, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightblue),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("No persona data available.", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Forecast
    elements.append(Paragraph("📊 Adherence Forecast", styles['Heading2']))
    if forecast_data is not None and not forecast_data.empty:
        data = [forecast_data.columns.tolist()] + forecast_data.astype(str).values.tolist()
        table = Table(data, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgreen),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("No forecast available.", styles['Normal']))

    # Build PDF
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

# ---------------- Real Adherence placeholders (optional) -------------
ADHERENCE_TASK_TAGS = {"plan_update", "lifestyle", "therapy"}

def _member_follow_up_exists(df, start_ts, end_ts):
    return False  # placeholder logic

def compute_real_adherence(df):
    return None  # placeholder logic

# ---------------- Profile Section -----------------------------------
def show_profile():
    st.subheader("👤 Member Profile: Rohan Patel")
    st.markdown("""
- **Age:** 46 (Born 12 March 1979)  
- **Primary Residence:** Singapore  
- **Travel Hubs:** UK, US, South Korea, Jakarta  
- **Occupation:** Regional Head of Sales (FinTech; high stress; frequent travel)  
- **Chronic Risk:** Family history of heart disease (cholesterol, blood pressure)  
- **Goals:**  
  - Reduce risk of heart disease by **Dec 2026**  
  - Enhance cognitive function by **Jun 2026**  
  - Annual full-body screenings (from **Nov 2025**)  
- **Wearables:** Garmin watch for runs; considering Oura Ring  
- **Motivations:** Long-term health to balance career & family (2 young kids)  
    """)

# ---------------- Health Report Generator + Plots --------------------
def generate_health_data():
    dates = pd.date_range("2025-01-01", periods=32, freq="W")  # ~8 months
    np.random.seed(42)
    systolic = np.clip(np.random.normal(135, 6, len(dates)) - np.linspace(0, 8, len(dates)), 120, 145)
    diastolic = np.clip(np.random.normal(88, 4, len(dates)) - np.linspace(0, 5, len(dates)), 70, 95)
    cholesterol = np.clip(np.random.normal(210, 15, len(dates)) - np.linspace(0, 30, len(dates)), 160, 240)
    hdl = np.clip(np.random.normal(45, 4, len(dates)) + np.linspace(0, 8, len(dates)), 40, 70)
    ldl = np.clip(cholesterol - hdl - np.random.normal(30, 5, len(dates)), 80, 160)
    hrv = np.clip(np.random.normal(38, 6, len(dates)) + np.linspace(0, 12, len(dates)), 25, 70)
    vo2 = np.clip(np.random.normal(40, 2, len(dates)) + np.linspace(0, 5, len(dates)), 35, 55)

    df = pd.DataFrame({
        "Date": dates,
        "Systolic BP": systolic.round(1),
        "Diastolic BP": diastolic.round(1),
        "Total Cholesterol": cholesterol.round(1),
        "HDL": hdl.round(1),
        "LDL": ldl.round(1),
        "HRV (ms)": hrv.round(1),
        "VO2 Max": vo2.round(1),
    })
    return df

def plot_health_reports(df):
    st.subheader("🫀 Health Metrics Over Time")
    fig1 = px.line(df, x="Date", y=["Systolic BP", "Diastolic BP"], title="Blood Pressure Trend")
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.line(df, x="Date", y=["Total Cholesterol", "HDL", "LDL"], title="Cholesterol Panel")
    st.plotly_chart(fig2, use_container_width=True)

    fig3 = px.line(df, x="Date", y="HRV (ms)", title="Heart Rate Variability (Stress Marker)")
    st.plotly_chart(fig3, use_container_width=True)

    fig4 = px.line(df, x="Date", y="VO2 Max", title="VO₂ Max (Fitness)")
    st.plotly_chart(fig4, use_container_width=True)

# ---------------- Demo Conversation Generator (8 months) -------------
def _rand_dt(day, start_hour=7, end_hour=22):
    """Random datetime on a given day between start and end hour."""
    hour = random.randint(start_hour, end_hour)
    minute = random.randint(0, 59)
    return datetime.combine(day, time(hour=hour, minute=minute))

def generate_demo_conversations():
    """
    Generate ~8 months of WhatsApp-style conversations following hackathon constraints:
    - ~5 member-initiated chats per week
    - Diagnostics every 3 months
    - Exercise updates every 2 weeks
    - 1 travel week every 4 weeks (plan adjustments)
    - ~50% adherence implied via some plan changes / feedback
    """
    random.seed(7)
    start = datetime(2025, 1, 1)
    end = start + timedelta(weeks=32)

    msgs = []

    # Travel weeks: every 4 weeks starting week 3
    travel_weeks = set()
    for w in range(3, 33, 4):
        week_start = start + timedelta(weeks=w)
        travel_weeks.add(week_start.date())

    # Diagnostics every 12 weeks (approx 3 months)
    diagnostics_weeks = {(start + timedelta(weeks=i)).date() for i in [0, 12, 24, 32]}

    # Exercise updates every 2 weeks
    exercise_weeks = {(start + timedelta(weeks=i)).date() for i in range(0, 33, 2)}

    # Helper: add message
    def add_msg(dt, sender, sender_type, tag, text):
        msgs.append({"date": dt, "sender": sender, "sender_type": sender_type, "tag": tag, "message": text})

    # Iterate by week
    week_starts = pd.date_range(start, end, freq="W-MON")
    for ws in week_starts:
        # Member ~5 queries this week
        for _ in range(random.randint(4, 6)):
            day = ws + timedelta(days=random.randint(0, 6))
            dt = _rand_dt(day)
            text = random.choice([
                "BP readings higher this morning after poor sleep.",
                "Can we tweak run schedule this week?",
                "Travel coming up — need a portable routine.",
                "Feeling stressed after long calls; advice?",
                "Confused about supplement timing.",
                "Gym access limited; alternative plan?",
                "Any updates on my test results?"
            ])
            tag = "general_query"
            add_msg(dt, "Rohan Patel", "member", tag, text)

        # Exercise updates biweekly
        if ws.date() in exercise_weeks:
            dt = _rand_dt(ws + timedelta(days=1))
            add_msg(dt, "Carla (Coach)", "elyx", "lifestyle",
                    "Biweekly exercise plan updated to include zone-2 runs and mobility.")

        # Travel week adjustments
        if ws.date() in travel_weeks:
            dt = _rand_dt(ws + timedelta(days=2))
            add_msg(dt, "Ruby (Concierge)", "elyx", "plan_update",
                    "Travel noted. Adjusting workout and meal plans for hotel stays and flights.")
            dt2 = _rand_dt(ws + timedelta(days=3))
            add_msg(dt2, "Rohan Patel", "member", "general_query",
                    "Jet lag expected. How to manage sleep and BP during flights?")

        # Diagnostics every 12 weeks
        if ws.date() in diagnostics_weeks:
            dt = _rand_dt(ws + timedelta(days=0))
            add_msg(dt, "Ruby (Concierge)", "elyx", "test_order",
                    "Quarterly diagnostics scheduled: lipids, ApoB, fasting glucose, kidney panel.")

        # Occasional medication or therapy episodes
        if random.random() < 0.15:
            dt = _rand_dt(ws + timedelta(days=random.randint(0, 6)))
            add_msg(dt, "Dr. Warren", "elyx", "medication",
                    "Blood pressure control ke liye Cozaar 25 mg start karein. Review in 2 weeks.")

        if random.random() < 0.12:
            dt = _rand_dt(ws + timedelta(days=random.randint(0, 6)))
            add_msg(dt, "Rachel (Physio)", "elyx", "therapy",
                    "Hip mobility and posture therapy scheduled. Aim to reduce back stiffness from travel.")

        # Dissatisfaction / feedback sometimes (~10%)
        if random.random() < 0.10:
            dt = _rand_dt(ws + timedelta(days=random.randint(0, 6)))
            add_msg(dt, "Rohan Patel", "member", "general_query",
                    random.choice([
                        "Feeling frustrated with slow updates.",
                        "Bit confused about who to contact for reports.",
                        "Delay in getting test results—please prioritize."
                    ]))

    df = pd.DataFrame(msgs).sort_values("date").reset_index(drop=True)
    return df

# ---------------- UI Components -------------------------------------
def draw_kpis(df):
    total_msgs = len(df)
    unique_tags = df["tag"].nunique() if not df.empty else 0
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
            st.caption("🤖 " + ai_generate_rationale(row['tag'], row['message'], row['message']))
            st.divider()

# ---------------- Dynamic Episodes ----------------------------------
def extract_episodes(df):
    if df.empty:
        return []

    df = df.sort_values("date").reset_index(drop=True)

    episodes = []
    used_ranges = []

    # Simple keyword rules for dissatisfaction
    dissatisfaction_keywords = ["frustrated", "slow", "confused", "delay", "delays"]

    for _, row in df.iterrows():
        tag = str(row["tag"]).lower()
        msg = str(row.get("message", "")).lower()

        is_trigger = (
            tag in ["medication", "test_order", "plan_update", "plan_change", "therapy", "lifestyle"]
            or any(k in msg for k in dissatisfaction_keywords)
        )
        if not is_trigger:
            continue

        # Episode window: [-1 day, +3 days] around trigger
        start_ts = row["date"] - pd.Timedelta(days=1)
        end_ts = row["date"] + pd.Timedelta(days=3)

        # Skip if overlaps a prior episode heavily
        overlap = any((start_ts <= r[1]) and (end_ts >= r[0]) for r in used_ranges)
        if overlap:
            continue

        episode_df = df[(df["date"] >= start_ts) & (df["date"] <= end_ts)]

        # Determine title + persona states
        if tag == "medication":
            title = f"Medication Episode ({row['date'].date()})"
        elif tag in ["plan_update", "plan_change"]:
            title = f"Plan Update Episode ({row['date'].date()})"
        elif tag == "test_order":
            title = f"Diagnostic Test Episode ({row['date'].date()})"
        elif tag in ["therapy", "lifestyle"]:
            title = f"Lifestyle/Therapy Episode ({row['date'].date()})"
        else:
            title = f"Episode ({row['date'].date()})"

        persona_state = infer_persona_state(row.get("message", ""), tag)
        before, after = persona_state["before"], persona_state["after"]

        # Metrics
        member_msgs = episode_df[episode_df["sender_type"] == "member"]
        elyx_msgs = episode_df[episode_df["sender_type"] == "elyx"]

        response_time = "N/A"
        if not member_msgs.empty and not elyx_msgs.empty:
            response_time = str(elyx_msgs["date"].iloc[0] - member_msgs["date"].iloc[0])

        resolution_time = str(episode_df["date"].max() - episode_df["date"].min())
        episodes.append({
            "title": title,
            "trigger": f"{row['sender_type'].capitalize()} ({row['sender']})",
            "friction": ["Detected from chat context (refine by adding keywords or NER if needed)"],
            "outcome": ai_generate_rationale(tag, row.get("message", ""), row.get("message", "")),
            "before": before,
            "after": after,
            "metrics": {
                "Response Time": response_time,
                "Time to Resolution": resolution_time
            },
            "persona_conf": persona_state["confidence"]
        })

        used_ranges.append((start_ts, end_ts))

    return episodes

def show_episodes_dynamic(df):
    episodes = extract_episodes(df)
    if not episodes:
        st.info("No episodes detected from current filters.")
        return

    for ep in episodes:
        with st.expander(ep["title"], expanded=False):
            st.markdown(f"**🔔 Triggered by:** {ep['trigger']}")
            st.markdown("**⚠️ Friction Points:**")
            for f in ep["friction"]:
                st.write("- " + f)
            st.markdown(f"**✅ Final Outcome:** {ep['outcome']}")
            st.markdown("**🧠 Persona State:**")
            st.write(f"- **Before:** {ep['before']}")
            st.write(f"- **After:** {ep['after']}")
            st.write(f"- **Confidence:** {ep.get('persona_conf', '0.80')}")
            st.markdown("**📊 Metrics:**")
            for k, v in ep["metrics"].items():
                st.write(f"- {k}: {v}")
            st.divider()

# ---------------- Sidebar + Data load --------------------------------
st.markdown("<h1 style='color:#2E86C1;'>🏥 Elyx Life – AI-Enhanced Member Journey</h1>", unsafe_allow_html=True)

st.sidebar.title("Navigation")
st.sidebar.markdown("**Welcome to the Elyx Life dashboard!**")
st.sidebar.markdown("Explore member journeys, health reports, and AI-driven insights.")

with st.sidebar:
    st.header("📂 Load Dataset")
    uploaded = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])
    st.caption("Columns needed: date, sender, sender_type, tag, message")

    st.markdown("---")
    st.header("🧪 Demo Data")
    if st.button("Generate Demo Journey (8 months)"):
        demo_df = generate_demo_conversations()
        st.session_state["demo_df"] = demo_df
        st.success("✅ Demo dataset generated — scroll down to see analytics.")

    st.header("🔍 Filters")
    text_query = st.text_input("Search text")
    case_sensitive = st.checkbox("Case-sensitive search", value=False)

# Load uploaded OR session demo OR tiny default
if "demo_df" in st.session_state:
    raw_df, file_name = st.session_state["demo_df"].copy(), "Generated Demo Journey"
else:
    raw_df, file_name = load_data(uploaded)

df = coerce_datetime(raw_df)

# ✅ SAFE COLUMN HANDLING
required_cols = ["sender", "sender_type", "tag", "message"]
for col in required_cols:
    if col not in df.columns:
        df[col] = "member" if col == "sender_type" else None

df["sender_type"] = df["sender_type"].apply(normalize_sender_type)

with st.sidebar:
    if not df.empty:
        min_d, max_d = df["date"].min().date(), df["date"].max().date()
        date_range = st.date_input("Date range", (min_d, max_d))
        sender_types = st.multiselect("Sender types", sorted(df["sender_type"].unique().tolist()),
                                      default=sorted(df["sender_type"].unique().tolist()))
        tags_all = sorted(df["tag"].dropna().astype(str).unique())
        selected_tags = st.multiselect("Tags", tags_all, default=tags_all)
    else:
        date_range, sender_types, selected_tags = None, [], []

filtered_df = apply_filters(df, date_range, sender_types, selected_tags, text_query, case_sensitive)

# ---------------- Team Metrics Dashboard -----------------------------
st.subheader("⏱ Team Metrics Dashboard")
def draw_team_metrics(df_in):
    if df_in.empty:
        st.info("No data for team metrics.")
        return

    time_map = {
        "concierge": 10, "coach": 10, "diet": 10,
        "physio": 20, "doctor": 30, "dr": 30,
        "director": 15
    }

    df_in = df_in.copy()
    df_in["minutes"] = df_in.apply(
        lambda r: next((v for k, v in time_map.items()
                        if isinstance(r["sender"], str) and k in r["sender"].lower()), 5),
        axis=1
    )

    team_time = df_in.groupby("sender")["minutes"].sum().reset_index().sort_values("minutes", ascending=False)
    fig = px.bar(team_time, x="sender", y="minutes", title="⏱ Expert Time Allocation (mins)", text="minutes")
    st.plotly_chart(fig, use_container_width=True)

draw_team_metrics(filtered_df)

# ---------------- Adherence Tracker ---------------------------------
st.subheader("📈 Adherence Tracker")
def draw_adherence_tracker(df_in):
    if df_in.empty:
        st.info("No data for adherence tracker.")
        return

    wk = df_in.set_index("date").resample("W")["sender_type"].value_counts().unstack().fillna(0)
    wk["adherence"] = wk.get("elyx", 0) / (wk.get("elyx", 0) + wk.get("member", 0)).replace(0, 1) * 100
    wk = wk.reset_index()

    fig = px.line(wk, x="date", y="adherence", markers=True, title="📈 Plan Adherence Over Time")
    fig.update_traces(line=dict(width=3), marker=dict(size=10))

    # Color threshold bands
    fig.add_hrect(y0=70, y1=100, fillcolor="green", opacity=0.1, line_width=0)
    fig.add_hrect(y0=40, y1=70, fillcolor="yellow", opacity=0.1, line_width=0)
    fig.add_hrect(y0=0, y1=40, fillcolor="red", opacity=0.1, line_width=0)

    st.plotly_chart(fig, use_container_width=True)

draw_adherence_tracker(filtered_df)

# ---------------- Download filtered CSV ------------------------------
if not filtered_df.empty:
    st.download_button(
        "💾 Download filtered data (CSV)",
        data=filtered_df.to_csv(index=False).encode("utf-8"),
        file_name="filtered_chat.csv",
        mime="text/csv"
    )

# ---------------- Persona Evolution Timeline ------------------------
def plot_persona_timeline(df_in):
    episodes = extract_episodes(df_in)
    if not episodes:
        st.info("No persona states to show.")
        return
    timeline = pd.DataFrame([{
        "Date": ep["title"].split("(")[-1].strip(")"),
        "Before State": ep["before"],
        "After State": ep["after"],
        "Confidence": ep.get("persona_conf", 0.8)
    } for ep in episodes])
    st.subheader("🧠 Persona State Evolution")
    st.table(timeline)

# ---------------- Predictive Adherence Forecast ---------------------
def forecast_adherence(df_in):
    if df_in.empty:
        st.info("No data available for forecasting.")
        return

    wk = df_in.set_index("date").resample("W")["sender_type"].value_counts().unstack().fillna(0)
    wk["adherence"] = wk.get("elyx", 0) / (wk.get("elyx", 0) + wk.get("member", 0)).replace(0, 1) * 100
    wk = wk.reset_index()

    if len(wk) < 4:
        st.info("Not enough weeks of data for forecasting.")
        return

    X_idx = np.arange(len(wk)).reshape(-1, 1)
    y = wk["adherence"].values

    if HAVE_SKLEARN:
        model = LinearRegression().fit(X_idx, y)
        future_idx = np.arange(len(wk), len(wk) + 4).reshape(-1, 1)  # next 4 weeks
        preds = model.predict(future_idx)
    else:
        # Simple NumPy linear fit fallback
        x = np.arange(len(wk))
        m, b = np.polyfit(x, y, 1)
        future_x = np.arange(len(wk), len(wk) + 4)
        preds = m * future_x + b

    st.subheader("📊 Adherence Forecast (Next Month)")
    forecast_df = pd.DataFrame({
        "Week": list(range(len(wk))) + list(range(len(wk), len(wk) + 4)),
        "Adherence": list(y) + list(preds)
    })
    st.line_chart(forecast_df.set_index("Week"))

# ---------------- WhatsApp-style Chat UI -----------------------------
def show_chat_ui(df_in):
    st.subheader("💬 Conversation Viewer")
    if df_in.empty:
        st.info("No conversations available.")
        return

    for _, row in df_in.iterrows():
        if row["sender_type"] == "member":
            st.chat_message("user").write(row["message"])
        else:
            st.chat_message("assistant").write(f"**{row['sender']}**: {row['message']}")

# ---------------- Main Content: advanced features --------------------
st.markdown("---")
st.header("🚀 Advanced AI Features")

plot_persona_timeline(filtered_df)
forecast_adherence(filtered_df)
show_chat_ui(filtered_df)

# ---------------- Episodes (expanders) -------------------------------
st.subheader("🧩 Episodes")
show_episodes_dynamic(filtered_df)

# ---------------- Health Reports demo (optional nice section) --------
st.markdown("---")
st.header("🫀 Health Reports (demo data)")
health_df = generate_health_data()
plot_health_reports(health_df)

# ---------------- PDF Export Button (safe) ---------------------------
episodes = extract_episodes(filtered_df)
persona_df = pd.DataFrame([{
    "Date": ep["title"].split("(")[-1].strip(")"),
    "Before": ep["before"],
    "After": ep["after"],
    "Confidence": ep.get("persona_conf", 0.8)
} for ep in episodes]) if episodes else pd.DataFrame()

wk_pdf = filtered_df.set_index("date").resample("W")["sender_type"].value_counts().unstack().fillna(0) \
    if not filtered_df.empty else pd.DataFrame()
if not wk_pdf.empty:
    wk_pdf["adherence"] = wk_pdf.get("elyx", 0) / (wk_pdf.get("elyx", 0) + wk_pdf.get("member", 0)).replace(0, 1) * 100
    wk_pdf = wk_pdf.reset_index()
    forecast_df_for_pdf = wk_pdf[["date", "adherence"]].rename(columns={"date": "Week", "adherence": "Adherence"})
else:
    forecast_df_for_pdf = pd.DataFrame()

profile_text = """
Age: 46 (Born 12 March 1979)<br/>
Residence: Singapore<br/>
Occupation: Regional Head of Sales (FinTech)<br/>
Chronic Risk: Family history of heart disease<br/>
Goals: Reduce heart risk, improve cognition, balance career and family
"""

if HAVE_REPORTLAB:
    pdf_bytes = export_pdf(profile_text, episodes, persona_df, forecast_df_for_pdf)
    if pdf_bytes:
        st.download_button(
            "📄 Download Member Report (PDF)",
            data=pdf_bytes,
            file_name="elyx_member_report.pdf",
            mime="application/pdf"
        )
else:
    st.info("📄 PDF export disabled. Install reportlab: `pip install reportlab`")
 