import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import os
import subprocess
import logging

# -------------------- Logging --------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -------------------- Config --------------------
DATA_FILE = "tracker_data.xlsx"
HISTORY_FILE = "progress_history.xlsx"
REPO_DIR = "."
BRANCH = "main"
GITHUB_REPO = "parameshwarareddy1/habit-tracker-api"

# -------------------- Data Loaders --------------------
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_excel(DATA_FILE, engine='openpyxl')
            df['DateAdded'] = pd.to_datetime(df['DateAdded']).dt.date
        except Exception as e:
            logger.error(f"Error reading {DATA_FILE}: {e}")
            st.error(f"Error reading {DATA_FILE}: {e}")
            df = pd.DataFrame(columns=["GoalID", "GoalName", "Frequency", "Progress", "DateAdded", "Week"])
    else:
        df = pd.DataFrame(columns=["GoalID", "GoalName", "Frequency", "Progress", "DateAdded", "Week"])
    return df

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            df = pd.read_excel(HISTORY_FILE, engine='openpyxl')
            df['Date'] = pd.to_datetime(df['Date']).dt.date
        except Exception as e:
            logger.error(f"Error reading {HISTORY_FILE}: {e}")
            st.error(f"Error reading {HISTORY_FILE}: {e}")
            df = pd.DataFrame(columns=["GoalID", "GoalName", "Date", "Progress", "Percentage", "Change"])
    else:
        df = pd.DataFrame(columns=["GoalID", "GoalName", "Date", "Progress", "Percentage", "Change"])
    return df

def save_data():
    st.session_state.data.to_excel(DATA_FILE, index=False, engine='openpyxl')
    st.session_state.history.to_excel(HISTORY_FILE, index=False, engine='openpyxl')
    commit_and_push_to_github()

def commit_and_push_to_github():
    try:
        os.chdir(REPO_DIR)
        subprocess.run(["git", "config", "user.name", "Streamlit Bot"], check=True)
        subprocess.run(["git", "config", "user.email", "bot@streamlit.app"], check=True)
        subprocess.run(["git", "add", DATA_FILE, HISTORY_FILE], check=True)
        commit_message = f"Update tracker data {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_message], check=False)
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            st.error("GitHub token not configured")
            return
        remote_url = f"https://{token}@github.com/{GITHUB_REPO}.git"
        subprocess.run(["git", "push", remote_url, BRANCH], check=False)
    except Exception as e:
        logger.error(f"Git error: {e}")

# -------------------- Goal Functions --------------------
def get_week_number(date):
    return date.isocalendar()[1]

def add_goal(name, freq):
    goal_id = f"G{len(st.session_state.data) + 1}"
    today = datetime.now().date()
    week = get_week_number(today)
    new_row = {"GoalID": goal_id, "GoalName": name, "Frequency": freq, "Progress": 1.0, "DateAdded": today, "Week": week}
    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
    save_data()
    st.success(f"Added Goal: {name}")
    st.rerun()

def update_progress(goal_id, goal_name, pct):
    today = datetime.now().date()
    start_date = st.session_state.data.loc[st.session_state.data["GoalID"] == goal_id, "DateAdded"].iloc[0]
    if today == start_date:
        st.error("Progress can be updated starting from Day 2 (not creation day).")
        return
    if not st.session_state.history[(st.session_state.history["GoalID"] == goal_id) & (st.session_state.history["Date"] == today)].empty:
        st.error("Progress already updated today.")
        return
    current_progress = st.session_state.data.loc[st.session_state.data["GoalID"] == goal_id, "Progress"].values[0]
    if pct == 100:
        new_progress = current_progress * 1.01
        change = 0.01
    elif pct == 50:
        new_progress = current_progress * 1.005
        change = 0.005
    else:
        new_progress = current_progress / 1.01
        change = -0.01
    st.session_state.data.loc[st.session_state.data["GoalID"] == goal_id, "Progress"] = new_progress
    row = {"GoalID": goal_id, "GoalName": goal_name, "Date": today, "Progress": new_progress, "Percentage": pct, "Change": change}
    st.session_state.history = pd.concat([st.session_state.history, pd.DataFrame([row])], ignore_index=True)
    save_data()
    st.success("Progress updated!")
    st.rerun()

def delete_goal(goal_id, goal_name):
    st.session_state.data = st.session_state.data[st.session_state.data["GoalID"] != goal_id]
    st.session_state.history = st.session_state.history[st.session_state.history["GoalID"] != goal_id]
    save_data()
    st.success(f"Goal '{goal_name}' deleted successfully!")
    st.rerun()

def calculate_potential_progress(start_date):
    today = datetime.now().date()
    days_since_start = (today - start_date).days
    potential = 1.0
    for _ in range(days_since_start):
        potential *= 1.01
    return potential

# -------------------- UI Components --------------------
def show_progress_info(gid, gname):
    df = st.session_state.history[st.session_state.history["GoalID"] == gid]
    start_date = st.session_state.data.loc[st.session_state.data["GoalID"] == gid, "DateAdded"].iloc[0]
    df = df[df["Date"] > start_date]
    success_days = (df["Percentage"] == 100).sum()
    failed_days = (df["Percentage"] == 0).sum()
    progress = df["Progress"].iloc[-1] if not df.empty else 1.0
    potential = calculate_potential_progress(start_date)

    st.markdown(f"""
        <div style='display: flex; flex-direction: column; gap: 15px;'>
            <div style='background: linear-gradient(45deg, #ff6b6b, #ff8e53); padding: 10px; border-radius: 8px; text-align:center; color:white; font-weight:bold;'>🎯 Potential Progress: {potential:.3f}</div>
            <div style='background: linear-gradient(45deg, #4facfe, #00f2fe); padding: 10px; border-radius: 8px; text-align:center; color:white; font-weight:bold;'>🔥 Actual Progress: {progress:.3f}</div>
            <div style='background: linear-gradient(45deg, #2ecc71, #27ae60); padding: 10px; border-radius: 8px; text-align:center; color:white; font-weight:bold;'>✅ Success Days: {success_days}</div>
            <div style='background: linear-gradient(45deg, #e84393, #a29bfe); padding: 10px; border-radius: 8px; text-align:center; color:white; font-weight:bold;'>❌ Failure Days: {failed_days}</div>
        </div>
    """, unsafe_allow_html=True)

def show_calendar(gid):
    today = datetime.now().date()
    start_date = st.session_state.data.loc[st.session_state.data["GoalID"] == gid, "DateAdded"].iloc[0]
    df = st.session_state.history[st.session_state.history["GoalID"] == gid]
    hist_by_date = {row["Date"]: row for row in df.to_dict('records')}
    year, month = today.year, today.month
    first_day = datetime(year, month, 1).date()
    last_day = (datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)) - timedelta(days=1)
    last_day = last_day.date()
    days = []
    for i in range(first_day.weekday()):
        days.append({"type": "pad"})
    for d in range(1, last_day.day + 1):
        ds = datetime(year, month, d).date()
        if ds > today:
            status = "future"
        elif ds == start_date:
            status = "start"
        elif ds in hist_by_date:
            pct = hist_by_date[ds]["Percentage"]
            status = "full" if pct == 100 else "half" if pct == 50 else "zero"
        else:
            status = "miss"
        emoji = {"start": "🚀", "full": "🟢", "half": "🟡", "zero": "🔴", "miss": "⬜", "future": ""}[status]
        days.append({"type": "day", "day": d, "emoji": emoji})
    calendar_html = f"""
        <h4>Calendar {year}-{month:02d}</h4>
        <div style='display:grid; grid-template-columns: repeat(7, 1fr); gap:5px;'>
            {''.join([
                f"<div style='padding:10px; text-align:center; border:1px solid #ccc;'>{str(day['day']) + ' ' + day['emoji'] if day['type']=='day' else ''}</div>"
                for day in days
            ])}
        </div>
    """
    st.markdown(calendar_html, unsafe_allow_html=True)

def show_summary_dashboard():
    total_goals = len(st.session_state.data)
    df = st.session_state.history
    total_success = (df["Percentage"] == 100).sum()
    total_failures = (df["Percentage"] == 0).sum()
    st.markdown(f"""
        <div style='display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 20px;'>
            <div style='background: linear-gradient(45deg, #ff6b6b, #ff8e53); padding: 20px; border-radius: 10px; text-align:center; color:white; font-weight:bold; font-size:18px;'>🏆 Total Goals: {total_goals}</div>
            <div style='background: linear-gradient(45deg, #2ecc71, #27ae60); padding: 20px; border-radius: 10px; text-align:center; color:white; font-weight:bold; font-size:18px;'>✅ Total Success: {total_success}</div>
            <div style='background: linear-gradient(45deg, #e84393, #a29bfe); padding: 20px; border-radius: 10px; text-align:center; color:white; font-weight:bold; font-size:18px;'>❌ Total Failures: {total_failures}</div>
        </div>
    """, unsafe_allow_html=True)

# -------------------- Streamlit UI --------------------
st.set_page_config(page_title="Goal Tracker", layout="wide")
st.title("🎯 Goal Tracker")

if "data" not in st.session_state:
    st.session_state.data = load_data()
if "history" not in st.session_state:
    st.session_state.history = load_history()

# Show Dashboard Summary
show_summary_dashboard()

# Show Goals
if not st.session_state.data.empty:
    st.subheader("📌 Your Goals")
    for _, row in st.session_state.data.iterrows():
        with st.expander(f"{row['GoalName']}"):
            show_progress_info(row["GoalID"], row["GoalName"])
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                pct = st.selectbox("Progress Today", [0, 50, 100], key=f"pct_{row['GoalID']}")
                if st.button("Update", key=f"btn_{row['GoalID']}"):
                    update_progress(row["GoalID"], row["GoalName"], pct)
            with col2:
                if st.button("Delete Goal", key=f"del_{row['GoalID']}"):
                    delete_goal(row["GoalID"], row["GoalName"])
            with col3:
                if st.button("Show Calendar", key=f"cal_{row['GoalID']}"):
                    show_calendar(row["GoalID"])

# Add New Goal
st.subheader("Add New Goal")
with st.form("add_goal_form", clear_on_submit=True):
    name = st.text_input("Goal Name")
    freq = st.selectbox("Frequency", ["Daily", "Weekly", "Monthly"])
    submitted = st.form_submit_button("Add Goal")
    if submitted and name:
        add_goal(name, freq)
