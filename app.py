import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import os
from openpyxl import load_workbook
import calendar
from dateutil.relativedelta import relativedelta

# File paths
DATA_FILE = "tracker_data.xlsx"
HISTORY_FILE = "progress_history.xlsx"
PASSWORD = "param123"

# Load or initialize data
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_excel(DATA_FILE, engine='openpyxl')
            df['DateAdded'] = pd.to_datetime(df['DateAdded']).dt.date
        except Exception as e:
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
            st.error(f"Error reading {HISTORY_FILE}: {e}")
            df = pd.DataFrame(columns=["GoalID", "GoalName", "Date", "Progress", "Percentage", "Change"])
    else:
        df = pd.DataFrame(columns=["GoalID", "GoalName", "Date", "Progress", "Percentage", "Change"])
    return df

def save_data():
    # Save data to temporary Excel files without password
    temp_data_file = "temp_tracker_data.xlsx"
    temp_history_file = "temp_progress_history.xlsx"
    
    st.session_state.data.to_excel(temp_data_file, index=False, engine='openpyxl')
    st.session_state.history.to_excel(temp_history_file, index=False, engine='openpyxl')

    # Load workbooks with openpyxl to set password
    data_wb = load_workbook(temp_data_file)
    history_wb = load_workbook(temp_history_file)

    # Set password protection
    data_wb.security.set_workbook_password(PASSWORD)
    history_wb.security.set_workbook_password(PASSWORD)

    # Save the password-protected files
    data_wb.save(DATA_FILE)
    history_wb.save(HISTORY_FILE)

    # Remove temporary files
    if os.path.exists(temp_data_file):
        os.remove(temp_data_file)
    if os.path.exists(temp_history_file):
        os.remove(temp_history_file)

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
    hist_row = {
        "GoalID": goal_id,
        "GoalName": name,
        "Date": today,
        "Progress": 1.0,
        "Percentage": 0,
        "Change": 0
    }
    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
    st.session_state.history = pd.concat([st.session_state.history, pd.DataFrame([hist_row])], ignore_index=True)
    save_data()

def update_progress(goal_id, goal_name, pct):
    today = datetime.now().date()
    current_week = get_week_number(today)
    
    # Get the goal's frequency
    frequency = st.session_state.data.loc[st.session_state.data["GoalID"] == goal_id, "Frequency"].values[0]
    
    # Check if an update is allowed
    if frequency == "Weekly":
        # Check if there's already an update in the current week
        history_weeks = st.session_state.history[
            (st.session_state.history["GoalID"] == goal_id) & 
            (st.session_state.history["Date"].apply(get_week_number) == current_week)
        ]
        if not history_weeks.empty:
            st.error(f"Progress for this weekly goal has already been updated for week {current_week}.")
            return
    else:
        # For Daily and Monthly goals, check if there's an update today
        if not st.session_state.history[
            (st.session_state.history["GoalID"] == goal_id) & 
            (st.session_state.history["Date"] == today)
        ].empty:
            st.error("Progress for this goal has already been updated today.")
            return

    # Update progress
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
    st.success("Progress updated!")
    st.rerun()  # Refresh the page to reflect the update

def delete_goal(goal_id, goal_name):
    # Remove goal from data and history
    st.session_state.data = st.session_state.data[st.session_state.data["GoalID"] != goal_id]
    st.session_state.history = st.session_state.history[st.session_state.history["GoalID"] != goal_id]
    save_data()
    st.success(f"Goal '{goal_name}' deleted successfully!")
    st.rerun()  # Refresh the page to reflect deletion

def calculate_potential_progress(start_date, current_progress):
    today = datetime.now().date()
    days_since_start = (today - start_date).days
    potential_progress = 1.0
    for _ in range(days_since_start + 1):  # Include today
        potential_progress *= 1.01
    return potential_progress

def show_progress_info(gid, gname):
    df = st.session_state.history[st.session_state.history["GoalID"] == gid]
    if df.empty:
        return
    progress = df["Progress"].iloc[-1] if not df.empty else 1.0
    start_date = st.session_state.data[st.session_state.data["GoalID"] == gid]["DateAdded"].iloc[0]
    potential_progress = calculate_potential_progress(start_date, progress)
    today = datetime.now().date()

    # Display progress info in vertically stacked boxes with 3 decimal places
    st.markdown(f"""
        <div style='
            display: flex;
            flex-direction: column;
            gap: 15px;
            margin-top: 10px;
        '>
            <div style='
                background: linear-gradient(45deg, #ff6b6b, #ff8e53);
                color: white;
                font-size: 18px;
                padding: 15px 20px;
                border-radius: 12px;
                font-weight: bold;
                box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                text-align: center;
                transition: transform 0.2s ease-in-out;
            ' onmouseover='this.style.transform="scale(1.05)"' onmouseout='this.style.transform="scale(1)"'>
                🎯 Potential Progress: {potential_progress:.3f}
            </div>
            <div style='
                background: linear-gradient(45deg, #4facfe, #00f2fe);
                color: white;
                font-size: 18px;
                padding: 15px 20px;
                border-radius: 12px;
                font-weight: bold;
                box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                text-align: center;
                transition: transform 0.2s ease-in-out;
            ' onmouseover='this.style.transform="scale(1.05)"' onmouseout='this.style.transform="scale(1)"'>
                🔥 Actual Progress: {progress:.3f}
            </div>
            <div style='
                background: linear-gradient(45deg, #2ecc71, #27ae60);
                color: white;
                font-size: 18px;
                padding: 15px 20px;
                border-radius: 12px;
                font-weight: bold;
                box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                text-align: center;
                transition: transform 0.2s ease-in-out;
            ' onmouseover='this.style.transform="scale(1.05)"' onmouseout='this.style.transform="scale(1)"'>
                🚀 Start Date: {start_date.strftime('%Y-%m-%d')}
            </div>
            <div style='
                background: linear-gradient(45deg, #e84393, #a29bfe);
                color: white;
                font-size: 18px;
                padding: 15px 20px;
                border-radius: 12px;
                font-weight: bold;
                box-shadow: 0 6px 12px rgba(0,0,0,0.3);
                text-align: center;
                transition: transform 0.2s ease-in-out;
            ' onmouseover='this.style.transform="scale(1.05)"' onmouseout='this.style.transform="scale(1)"'>
                📅 Today: {today.strftime('%Y-%m-%d')}
            </div>
        </div>
    """, unsafe_allow_html=True)

def show_last_7_days(gid):
    today = datetime.now().date()
    start_date = st.session_state.data[st.session_state.data["GoalID"] == gid]["DateAdded"].iloc[0]
    days_since_start = (today - start_date).days
    display_start = max(today - timedelta(days=6), start_date)
    date_range = [display_start + timedelta(days=x) for x in range(min(7, days_since_start + 1))]
    
    df = st.session_state.history[
        (st.session_state.history["GoalID"] == gid) & 
        (st.session_state.history["Date"] >= display_start) & 
        (st.session_state.history["Date"] <= today)
    ]
    
    emojis = []
    for date in date_range:
        if date == start_date:
            emojis.append("🚀")
        else:
            history = df[df["Date"] == date]
            if not history.empty:
                pct = history["Percentage"].iloc[-1]  # Use the latest entry for the date
                emojis.append("🟢" if pct == 100 else "🟡" if pct == 50 else "🔴")
            else:
                emojis.append("🔴")
    return " ".join(emojis)

# -------- Streamlit UI --------
st.set_page_config(page_title="Goal Tracker", layout="wide")
st.title("🎯 Goal Tracker")

if "data" not in st.session_state:
    st.session_state.data = load_data()
if "history" not in st.session_state:
    st.session_state.history = load_history()

# Show goals
if not st.session_state.data.empty:
    st.subheader("📌 Your Goals")
    for _, row in st.session_state.data.iterrows():
        last_7_days = show_last_7_days(row["GoalID"])
        with st.expander(f"{row['GoalName']} | Last 7 Days: {last_7_days}"):
            show_progress_info(row["GoalID"], row["GoalName"])
            col1, col2 = st.columns([1, 1])  # Create two columns for Update and Delete buttons
            with col1:
                pct = st.selectbox("Progress Today", [0, 50, 100], key=f"pct_{row['GoalID']}")
                if st.button("Update", key=f"btn_{row['GoalID']}"):
                    update_progress(row["GoalID"], row["GoalName"], pct)
            with col2:
                if st.button("Delete Goal", key=f"del_{row['GoalID']}"):
                    delete_goal(row["GoalID"], row["GoalName"])

# Add goal form
st.markdown("---")
st.subheader("➕ Add New Goal")
with st.form("new_goal"):
    name = st.text_input("Goal Name")
    freq = st.selectbox("Frequency", ["Daily", "Weekly", "Monthly"])
    submit = st.form_submit_button("Add Goal")
    if submit:
        if name.strip():
            add_goal(name, freq)
            st.success(f"Added Goal: {name}")
        else:
            st.error("Goal name is required.")
