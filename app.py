import streamlit as st
import pandas as pd
import os
import subprocess
import logging
from datetime import datetime, timedelta
import calendar

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# File paths and GitHub configuration
DATA_FILE = "tracker_data.xlsx"
HISTORY_FILE = "progress_history.xlsx"
GITHUB_REPO = "parameshwarareddy1/habit-tracker-api"
BRANCH = "main"

# Initialize session state
def initialize_session_state():
    """Initialize session state for data and history DataFrames."""
    if 'data' not in st.session_state:
        try:
            st.session_state.data = pd.read_excel(DATA_FILE) if os.path.exists(DATA_FILE) else pd.DataFrame(
                columns=["GoalID", "GoalName", "Frequency", "Progress", "DateAdded", "Week"]
            )
            logger.info(f"Loaded tracker_data.xlsx: {st.session_state.data.shape[0]} rows")
        except Exception as e:
            logger.error(f"Error loading {DATA_FILE}: {e}")
            st.error(f"Error loading tracker data: {e}")
            st.session_state.data = pd.DataFrame(
                columns=["GoalID", "GoalName", "Frequency", "Progress", "DateAdded", "Week"]
            )
            # Create default row if file is empty or missing
            if st.session_state.data.empty:
                default_goal = pd.DataFrame([{
                    "GoalID": "G1",
                    "GoalName": "Read",
                    "Frequency": "Daily",
                    "Progress": 1.0,
                    "DateAdded": datetime.now().date(),
                    "Week": datetime.now().date().isocalendar()[1]
                }])
                st.session_state.data = pd.concat([st.session_state.data, default_goal], ignore_index=True)
                logger.info("Created default goal: Read")
    if 'history' not in st.session_state:
        try:
            st.session_state.history = pd.read_excel(HISTORY_FILE) if os.path.exists(HISTORY_FILE) else pd.DataFrame(
                columns=["GoalID", "GoalName", "Date", "Progress", "Percentage", "Change"]
            )
            logger.info(f"Loaded progress_history.xlsx: {st.session_state.history.shape[0]} rows")
        except Exception as e:
            logger.error(f"Error loading {HISTORY_FILE}: {e}")
            st.error(f"Error loading history data: {e}")
            st.session_state.history = pd.DataFrame(
                columns=["GoalID", "GoalName", "Date", "Progress", "Percentage", "Change"]
            )
            # Create default history entry if empty
            if st.session_state.history.empty and not st.session_state.data.empty:
                default_history = pd.DataFrame([{
                    "GoalID": "G1",
                    "GoalName": "Read",
                    "Date": datetime.now().date(),
                    "Progress": 1.0,
                    "Percentage": 0,
                    "Change": 0
                }])
                st.session_state.history = pd.concat([st.session_state.history, default_history], ignore_index=True)
                logger.info("Created default history entry for Read")

# Save data to Excel and push to GitHub
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

# Commit and push changes to GitHub
def commit_and_push_to_github():
    """Commit and push changes to GitHub."""
    try:
        subprocess.run(["git", "add", DATA_FILE, HISTORY_FILE], check=True)
        commit_message = f"Update tracker data {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        logger.info(f"Committed changes: {commit_message}")
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

# Add new goal
def add_goal(goal_name, frequency):
    """Add a new goal to the tracker."""
    try:
        goal_id = f"G{len(st.session_state.data) + 1}"
        today = datetime.now().date()
        week = today.isocalendar()[1]
        new_goal = pd.DataFrame([{
            "GoalID": goal_id,
            "GoalName": goal_name,
            "Frequency": frequency,
            "Progress": 1.0,
            "DateAdded": today,
            "Week": week
        }])
        new_history = pd.DataFrame([{
            "GoalID": goal_id,
            "GoalName": goal_name,
            "Date": today,
            "Progress": 1.0,
            "Percentage": 0,
            "Change": 0
        }])
        st.session_state.data = pd.concat([st.session_state.data, new_goal], ignore_index=True)
        st.session_state.history = pd.concat([st.session_state.history, new_history], ignore_index=True)
        save_data()
        logger.info(f"Added goal: {goal_name}")
        st.success(f"Added Goal: {goal_name}")
    except Exception as e:
        logger.error(f"Error adding goal: {e}")
        st.error(f"Error adding goal: {e}")

# Update progress
def update_progress(goal_id, percentage):
    """Update progress for a goal."""
    try:
        today = datetime.now().date()
        goal = st.session_state.data[st.session_state.data["GoalID"] == goal_id]
        if goal.empty:
            logger.error(f"Goal not found: {goal_id}")
            st.error("Goal not found")
            return
        goal_name = goal["GoalName"].iloc[0]
        current_progress = goal["Progress"].iloc[0]
        change = percentage / 100
        new_progress = current_progress + change
        st.session_state.data.loc[st.session_state.data["GoalID"] == goal_id, "Progress"] = new_progress
        new_history = pd.DataFrame([{
            "GoalID": goal_id,
            "GoalName": goal_name,
            "Date": today,
            "Progress": new_progress,
            "Percentage": percentage,
            "Change": change
        }])
        st.session_state.history = pd.concat([st.session_state.history, new_history], ignore_index=True)
        save_data()
        logger.info(f"Updated progress for goal {goal_name}: {percentage}%")
        st.success("Progress updated!")
    except Exception as e:
        logger.error(f"Error updating progress: {e}")
        st.error(f"Error updating progress: {e}")

# Delete goal
def delete_goal(goal_id):
    """Delete a goal and its history."""
    try:
        goal_name = st.session_state.data[st.session_state.data["GoalID"] == goal_id]["GoalName"].iloc[0]
        st.session_state.data = st.session_state.data[st.session_state.data["GoalID"] != goal_id]
        st.session_state.history = st.session_state.history[st.session_state.history["GoalID"] != goal_id]
        save_data()
        logger.info(f"Deleted goal: {goal_name}")
        st.success(f"Goal '{goal_name}' deleted successfully!")
    except Exception as e:
        logger.error(f"Error deleting goal: {e}")
        st.error(f"Error deleting goal: {e}")

# Show calendar with emojis
def show_calendar(goal_id):
    """Display a calendar with emojis for a goal's progress."""
    try:
        goal_history = st.session_state.history[st.session_state.history["GoalID"] == goal_id]
        today = datetime.now().date()
        year, month = today.year, today.month
        cal = calendar.monthcalendar(year, month)
        calendar_html = "<div style='display: grid; grid-template-columns: repeat(7, 1fr); gap: 5px;'>"
        for week in cal:
            for day in week:
                emoji = ""
                if day != 0:
                    date = datetime(year, month, day).date()
                    if date <= today:
                        day_history = goal_history[goal_history["Date"] == str(date)]
                        if not day_history.empty:
                            progress = day_history["Progress"].iloc[-1]
                            emoji = "🚀" if progress >= 1.0 else "🟡" if progress >= 0.5 else "🔴"
                        else:
                            emoji = "⬜"
                calendar_html += f"<div style='padding: 10px; text-align: center; border: 1px solid #ccc;'>{str(day) + ' ' + emoji if day != 0 else ''}</div>"
        calendar_html += "</div>"
        st.markdown(calendar_html, unsafe_allow_html=True)
    except Exception as e:
        logger.error(f"Error displaying calendar: {e}")
        st.error(f"Error displaying calendar: {e}")

# Streamlit UI
st.title("Habit Tracker")

initialize_session_state()

# Your Goals section
st.header("Your Goals")
if st.session_state.data.empty:
    st.write("No goals yet. Add a new goal below!")
else:
    for _, row in st.session_state.data.iterrows():
        goal_id = row["GoalID"]
        st.subheader(row["GoalName"])
        st.write(f"Frequency: {row['Frequency']}")
        st.write(f"Progress: {row['Progress']:.3f}")
        last_7_days = st.session_state.history[
            (st.session_state.history["GoalID"] == goal_id) &
            (st.session_state.history["Date"] >= str(datetime.now().date() - timedelta(days=7)))
        ]
        emojis = "".join(
            "🚀" if row["Progress"] >= 1.0 else "🟡" if row["Progress"] >= 0.5 else "🔴"
            for _, row in last_7_days.sort_values("Date").iterrows()
        )
        st.write(f"Last 7 Days: {emojis if emojis else 'No progress yet'}")
        percentage = st.selectbox(f"Progress Today (%) for {row['GoalName']}", [0, 25, 50, 75, 100], key=f"progress_{goal_id}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"Update", key=f"update_{goal_id}"):
                update_progress(goal_id, percentage)
        with col2:
            if st.button(f"Delete Goal", key=f"delete_{goal_id}"):
                delete_goal(goal_id)
        with st.expander(f"Show Calendar for {row['GoalName']}"):
            show_calendar(goal_id)

# Add New Goal section
st.header("Add New Goal")
with st.form("add_goal_form"):
    goal_name = st.text_input("Goal Name")
    frequency = st.selectbox("Frequency", ["Daily", "Weekly", "Monthly"])
    submitted = st.form_submit_button("Add Goal")
    if submitted and goal_name:
        add_goal(goal_name, frequency)
