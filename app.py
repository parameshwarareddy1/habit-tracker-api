import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import os
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# File paths and settings
DATA_FILE = "tracker_data.xlsx"
HISTORY_FILE = "progress_history.xlsx"
REPO_DIR = "."
BRANCH = "main"
GITHUB_REPO = "parameshwarareddy1/habit-tracker-api"

# =====================
# Load or Initialize Data
# =====================
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_excel(DATA_FILE, engine='openpyxl')
            df['DateAdded'] = pd.to_datetime(df['DateAdded']).dt.date
            logger.info(f"Loaded {DATA_FILE} successfully")
        except Exception as e:
            logger.error(f"Error reading {DATA_FILE}: {e}")
            st.error(f"Error reading {DATA_FILE}: {e}")
            df = pd.DataFrame(columns=["GoalID", "GoalName", "Frequency", "Progress", "DateAdded", "Week"])
    else:
        logger.warning(f"{DATA_FILE} not found, initializing empty DataFrame")
        df = pd.DataFrame(columns=["GoalID", "GoalName", "Frequency", "Progress", "DateAdded", "Week"])
    return df

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            df = pd.read_excel(HISTORY_FILE, engine='openpyxl')
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            logger.info(f"Loaded {HISTORY_FILE} successfully")
        except Exception as e:
            logger.error(f"Error reading {HISTORY_FILE}: {e}")
            st.error(f"Error reading {HISTORY_FILE}: {e}")
            df = pd.DataFrame(columns=["GoalID", "GoalName", "Date", "Progress", "Percentage", "Change"])
    else:
        logger.warning(f"{HISTORY_FILE} not found, initializing empty DataFrame")
        df = pd.DataFrame(columns=["GoalID", "GoalName", "Date", "Progress", "Percentage", "Change"])
    return df

def save_data():
    try:
        st.session_state.data.to_excel(DATA_FILE, index=False, engine='openpyxl')
        st.session_state.history.to_excel(HISTORY_FILE, index=False, engine='openpyxl')
        logger.info(f"Saved {DATA_FILE} and {HISTORY_FILE}")
        commit_and_push_to_github()
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        st.error(f"Error saving data: {e}")
        raise

def commit_and_push_to_github():
    try:
        os.chdir(REPO_DIR)
        subprocess.run(["git", "config", "user.name", "Streamlit Bot"], check=True)
        subprocess.run(["git", "config", "user.email", "bot@streamlit.app"], check=True)
        subprocess.run(["git", "add", DATA_FILE, HISTORY_FILE], check=True)
        commit_message = f"Update tracker data {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        result = subprocess.run(["git", "commit", "-m", commit_message], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"Committed changes: {commit_message}")
        else:
            logger.warning(f"Nothing to commit: {result.stderr}")
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            logger.error("GITHUB_TOKEN not found")
            st.error("GitHub token not configured")
            return
        remote_url = f"https://{token}@github.com/{GITHUB_REPO}.git"
        subprocess.run(["git", "push", remote_url, BRANCH], check=True)
        logger.info(f"Pushed changes to GitHub branch {BRANCH}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Git error: {e.stderr}")
        st.error(f"Git error: {e.stderr}")

# =====================
# Goal Functions
# =====================
def get_week_number(date):
    return date.isocalendar()[1]

def add_goal(name, freq):
    goal_id = f"G{len(st.session_state.data) + 1}"
    today = datetime.now().date()
    week = get_week_number(today)
    new_row = {
        "GoalID": goal_id,
        "GoalName": name,
        "Frequency": freq,
        "Progress": 1.0,
        "DateAdded": today,
        "Week": week
    }
    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
    save_data()
    logger.info(f"Added goal: {name}, Frequency: {freq}")
    st.success(f"Added Goal: {name}")
    st.rerun()

def update_progress(goal_id, goal_name, pct):
    today = datetime.now().date()
    start_date = st.session_state.data.loc[st.session_state.data["GoalID"] == goal_id, "DateAdded"].values[0]

    # Don't allow updates on the first day
    if today == start_date:
        st.error("Progress can be updated starting from tomorrow (Day 2).")
        return

    # Check if progress is already updated today
    if not st.session_state.history[
        (st.session_state.history["GoalID"] == goal_id) &
        (st.session_state.history["Date"] == today)
    ].empty:
        st.error("Progress for this goal has already been updated today.")
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
    row = {
        "GoalID": goal_id,
        "GoalName": goal_name,
        "Date": today,
        "Progress": new_progress,
        "Percentage": pct,
        "Change": change
    }
    st.session_state.history = pd.concat([st.session_state.history, pd.DataFrame([row])], ignore_index=True)
    save_data()
    logger.info(f"Updated progress for goal {goal_name}: Percentage={pct}, New Progress={new_progress}")
    st.success("Progress updated!")
    st.rerun()

def delete_goal(goal_id, goal_name):
    st.session_state.data = st.session_state.data[st.session_state.data["GoalID"] != goal_id]
    st.session_state.history = st.session_state.history[st.session_state.history["GoalID"] != goal_id]
    save_data()
    logger.info(f"Deleted goal: {goal_name}")
    st.success(f"Goal '{goal_name}' deleted successfully!")
    st.rerun()

def calculate_potential_progress(start_date):
    today = datetime.now().date()
    days_since_start = (today - start_date).days
    potential_progress = 1.0
    for _ in range(days_since_start):
        potential_progress *= 1.01
    return potential_progress

def show_progress_info(gid, gname):
    df = st.session_state.history[st.session_state.history["GoalID"] == gid]
    if df.empty:
        return
    start_date = st.session_state.data[st.session_state.data["GoalID"] == gid]["DateAdded"].iloc[0]
    df = df[df["Date"] > start_date]  # Skip creation day
    success_days = (df["Percentage"] == 100).sum()
    failed_days = (df["Percentage"] == 0).sum()
    progress = df["Progress"].iloc[-1] if not df.empty else 1.0
    potential_progress = calculate_potential_progress(start_date)
    st.markdown(f"""
        <div style='display: flex; flex-direction: column; gap: 15px; margin-top: 10px;'>
            <div style='background: linear-gradient(45deg, #ff6b6b, #ff8e53); color: white; font-size: 18px; padding: 15px 20px; border-radius: 12px; font-weight: bold;'>
                🚀 Potential Progress: {potential_progress:.3f}
            </div>
            <div style='background: linear-gradient(45deg, #4facfe, #00f2fe); color: white; font-size: 18px; padding: 15px 20px; border-radius: 12px; font-weight: bold;'>
                🔥 Actual Progress: {progress:.3f}
            </div>
            <div style='background: linear-gradient(45deg, #2ecc71, #27ae60); color: white; font-size: 18px; padding: 15px 20px; border-radius: 12px; font-weight: bold;'>
                ✅ Success Days: {success_days}
            </div>
            <div style='background: linear-gradient(45deg, #e84393, #a29bfe); color: white; font-size: 18px; padding: 15px 20px; border-radius: 12px; font-weight: bold;'>
                ❌ Failures: {failed_days}
            </div>
        </div>
    """, unsafe_allow_html=True)

# =====================
# Streamlit UI
# =====================
st.set_page_config(page_title="Goal Tracker", layout="wide")
st.title("🎯 Goal Tracker")

if "data" not in st.session_state:
    st.session_state.data = load_data()
if "history" not in st.session_state:
    st.session_state.history = load_history()

if not st.session_state.data.empty:
    st.subheader("📌 Your Goals")
    for _, row in st.session_state.data.iterrows():
        with st.expander(f"{row['GoalName']}"):
            show_progress_info(row["GoalID"], row["GoalName"])
            col1, col2 = st.columns([1, 1])
            with col1:
                pct = st.selectbox("Progress Today", [0, 50, 100], key=f"pct_{row['GoalID']}")
                if st.button("Update", key=f"btn_{row['GoalID']}"):
                    update_progress(row["GoalID"], row["GoalName"], pct)
            with col2:
                if st.button("Delete Goal", key=f"del_{row['GoalID']}"):
                    delete_goal(row["GoalID"], row["GoalName"])

# Add new goal
st.subheader("Add New Goal")
with st.form("add_goal_form", clear_on_submit=True):
    name = st.text_input("Goal Name")
    freq = st.selectbox("Frequency", ["Daily", "Weekly", "Monthly"])
    submitted = st.form_submit_button("Add Goal")
    if submitted and name:
        add_goal(name, freq)
