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
    """Load tracker_data.xlsx or create an empty DataFrame."""
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_excel(DATA_FILE, engine='openpyxl')
            df['DateAdded'] = pd.to_datetime(df['DateAdded']).dt.date
            logger.info(f"Loaded {DATA_FILE}: {df.shape[0]} rows")
        except Exception as e:
            logger.error(f"Error reading {DATA_FILE}: {e}")
            st.error(f"Error reading {DATA_FILE}: {e}")
            df = pd.DataFrame(columns=["GoalID", "GoalName", "Frequency", "Progress", "DateAdded", "Week"])
    else:
        df = pd.DataFrame(columns=["GoalID", "GoalName", "Frequency", "Progress", "DateAdded", "Week"])
        # Create default goal if empty
        today = datetime.now().date()
        default_goal = pd.DataFrame([{
            "GoalID": "G1",
            "GoalName": "Read",
            "Frequency": "Daily",
            "Progress": 1.0,
            "DateAdded": today,
            "Week": today.isocalendar()[1]
        }])
        df = pd.concat([df, default_goal], ignore_index=True)
        logger.info("Created default goal: Read")
    return df

def load_history():
    """Load progress_history.xlsx or create an empty DataFrame."""
    if os.path.exists(HISTORY_FILE):
        try:
            df = pd.read_excel(HISTORY_FILE, engine='openpyxl')
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            logger.info(f"Loaded {HISTORY_FILE}: {df.shape[0]} rows")
        except Exception as e:
            logger.error(f"Error reading {HISTORY_FILE}: {e}")
            st.error(f"Error reading {HISTORY_FILE}: {e}")
            df = pd.DataFrame(columns=["GoalID", "GoalName", "Date", "Progress", "Percentage", "Change"])
    else:
        df = pd.DataFrame(columns=["GoalID", "GoalName", "Date", "Progress", "Percentage", "Change"])
        # Create default history entry if empty and data exists
        if not st.session_state.data.empty:
            default_history = pd.DataFrame([{
                "GoalID": "G1",
                "GoalName": "Read",
                "Date": datetime.now().date(),
                "Progress": 1.0,
                "Percentage": 0,
                "Change": 0
            }])
            df = pd.concat([df, default_history], ignore_index=True)
            logger.info("Created default history entry for Read")
    return df

def save_data():
    """Save DataFrames to Excel and push to GitHub."""
    try:
        logger.info(f"Saving data: {st.session_state.data.to_dict()}")
        logger.info(f"Saving history: {st.session_state.history.to_dict()}")
        st.session_state.data.to_excel(DATA_FILE, index=False, engine='openpyxl')
        st.session_state.history.to_excel(HISTORY_FILE, index=False, engine='openpyxl')
        logger.info(f"Saved {DATA_FILE} and {HISTORY_FILE}")
        commit_and_push_to_github()
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        st.error(f"Error saving data: {e}")
        raise

def commit_and_push_to_github():
    """Commit and push changes to GitHub."""
    try:
        os.chdir(REPO_DIR)
        subprocess.run(["git", "config", "user.name", "Streamlit Bot"], check=True)
        subprocess.run(["git", "config", "user.email", "bot@streamlit.app"], check=True)
        subprocess.run(["git", "add", DATA_FILE, HISTORY_FILE], check=True)
        commit_message = f"Update tracker data {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        result = subprocess.run(["git", "commit", "-m", commit_message], check=False, capture_output=True, text=True)
        logger.info(f"Commit result: {result.stdout}")
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            logger.error("GITHUB_TOKEN not found")
            st.error("GitHub token not configured")
            return
        remote_url = f"https://{token}@github.com/{GITHUB_REPO}.git"
        result = subprocess.run(["git", "push", remote_url, BRANCH], check=True, capture_output=True, text=True)
        logger.info(f"Pushed changes to GitHub branch {BRANCH}: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Git error: {e}, stderr: {e.stderr}")
        st.error(f"Git error: {e.stderr}")
    except Exception as e:
        logger.error(f"Unexpected error in Git push: {e}")
        st.error(f"Unexpected error in Git push: {e}")

# -------------------- Goal Functions --------------------
def get_week_number(date):
    """Get ISO week number for a date."""
    return date.isocalendar()[1]

def add_goal(name, freq):
    """Add a new goal to the tracker."""
    try:
        goal_id = f"G{len(st.session_state.data) + 1}"
        today = datetime.now().date()
        week = get_week_number(today)
        new_row = {"GoalID": goal_id, "GoalName": name, "Frequency": freq, "Progress": 1.0, "DateAdded": today, "Week": week}
        st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
        new_history = {"GoalID": goal_id, "GoalName": name, "Date": today, "Progress": 1.0, "Percentage": 0, "Change": 0}
        st.session_state.history = pd.concat([st.session_state.history, pd.DataFrame([new_history])], ignore_index=True)
        save_data()
        logger.info(f"Added goal: {name}")
        st.success(f"Added Goal: {name}")
        st.rerun()
    except Exception as e:
        logger.error(f"Error adding goal: {e}")
        st.error(f"Error adding goal: {e}")

def update_progress(goal_id, goal_name, pct):
    """Update progress for a goal."""
    try:
        today = datetime.now().date()
        start_date = st.session_state.data.loc[st.session_state.data["GoalID"] == goal_id, "DateAdded"].iloc[0]
        if today == start_date:
            logger.warning(f"Cannot update progress on creation day for goal {goal_name}")
            st.error("Progress can be updated starting from Day 2 (not creation day).")
            return
        if not st.session_state.history[(st.session_state.history["GoalID"] == goal_id) & (st.session_state.history["Date"] == today)].empty:
            logger.warning(f"Progress already updated today for goal {goal_name}")
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
        logger.info(f"Updated progress for goal {goal_name}: {pct}%")
        st.success("Progress updated!")
        st.rerun()
    except Exception as e:
        logger.error(f"Error updating progress: {e}")
        st.error(f"Error updating progress: {e}")

def auto_update_failures():
    """Automatically mark missed days as failures (0% progress)."""
    try:
        today = datetime.now().date()
        for _, row in st.session_state.data.iterrows():
            goal_id = row["GoalID"]
            goal_name = row["GoalName"]
            start_date = row["DateAdded"]
            if start_date >= today:
                continue  # Skip goals created today
            days_since_start = (today - start_date).days
            for day_offset in range(1, days_since_start + 1):
                check_date = start_date + timedelta(days=day_offset)
                if check_date > today:
                    break  # Skip future dates
                if check_date == today and not st.session_state.history[
                    (st.session_state.history["GoalID"] == goal_id) & 
                    (st.session_state.history["Date"] == check_date)
                ].empty:
                    continue  # Skip if today’s progress was manually updated
                if st.session_state.history[
                    (st.session_state.history["GoalID"] == goal_id) & 
                    (st.session_state.history["Date"] == check_date)
                ].empty:
                    current_progress = st.session_state.data.loc[
                        st.session_state.data["GoalID"] == goal_id, "Progress"
                    ].values[0]
                    new_progress = current_progress / 1.01
                    row = {
                        "GoalID": goal_id,
                        "GoalName": goal_name,
                        "Date": check_date,
                        "Progress": new_progress,
                        "Percentage": 0,
                        "Change": -0.01
                    }
                    st.session_state.data.loc[
                        st.session_state.data["GoalID"] == goal_id, "Progress"
                    ] = new_progress
                    st.session_state.history = pd.concat(
                        [st.session_state.history, pd.DataFrame([row])], ignore_index=True
                    )
                    logger.info(f"Auto-marked failure for {goal_name} on {check_date}")
        save_data()
    except Exception as e:
        logger.error(f"Error in auto_update_failures: {e}")
        st.error(f"Error in auto_update_failures: {e}")

def delete_goal(goal_id, goal_name):
    """Delete a goal and its history."""
    try:
        st.session_state.data = st.session_state.data[st.session_state.data["GoalID"] != goal_id]
        st.session_state.history = st.session_state.history[st.session_state.history["GoalID"] != goal_id]
        save_data()
        logger.info(f"Deleted goal: {goal_name}")
        st.success(f"Goal '{goal_name}' deleted successfully!")
        st.rerun()
    except Exception as e:
        logger.error(f"Error deleting goal: {e}")
        st.error(f"Error deleting goal: {e}")

def calculate_potential_progress(start_date):
    """Calculate potential progress if 100% every day."""
    today = datetime.now().date()
    days_since_start = (today - start_date).days
    potential = 1.0
    for _ in range(days_since_start):
        potential *= 1.01
    return potential

# -------------------- UI Components --------------------
def show_progress_info(gid, gname):
    """Display progress information for a goal."""
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

def show_summary_dashboard():
    """Display summary dashboard of total goals, successes, and failures."""
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

# Initialize session state
if "data" not in st.session_state:
    st.session_state.data = load_data()
if "history" not in st.session_state:
    st.session_state.history = load_history()

# Auto-update failures for missed days
auto_update_failures()

# Show Dashboard Summary
show_summary_dashboard()

# Show Goals
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

# Add New Goal
st.subheader("Add New Goal")
with st.form("add_goal_form", clear_on_submit=True):
    name = st.text_input("Goal Name")
    freq = st.selectbox("Frequency", ["Daily", "Weekly", "Monthly"])
    submitted = st.form_submit_button("Add Goal")
    if submitted and name:
        add_goal(name, freq)