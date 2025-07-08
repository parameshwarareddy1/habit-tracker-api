import streamlit as st
from datetime import datetime
import pandas as pd
import os
import plotly.graph_objects as go

# File paths
DATA_FILE = "tracker_data.csv"
HISTORY_FILE = "progress_history.csv"

# Load or initialize data
def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df['DueDate'] = pd.to_datetime(df['DueDate']).dt.date
        df['DateAdded'] = pd.to_datetime(df['DateAdded']).dt.date
    else:
        df = pd.DataFrame(columns=["GoalID", "GoalName", "DueDate", "Frequency", "Progress", "DateAdded", "Week"])
    return df

def load_history():
    if os.path.exists(HISTORY_FILE):
        df = pd.read_csv(HISTORY_FILE)
        df['Date'] = pd.to_datetime(df['Date']).dt.date
    else:
        df = pd.DataFrame(columns=["GoalID", "GoalName", "Date", "Progress", "Percentage", "Change"])
    return df

def save_data():
    st.session_state.data.to_csv(DATA_FILE, index=False)
    st.session_state.history.to_csv(HISTORY_FILE, index=False)

def get_week_number(date):
    return date.isocalendar()[1]

def add_goal(name, due, freq):
    goal_id = f"G{len(st.session_state.data) + 1}"
    today = datetime.now().date()
    week = get_week_number(today)
    new_row = {
        "GoalID": goal_id,
        "GoalName": name,
        "DueDate": due,
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

def show_graph(gid, gname):
    df = st.session_state.history[st.session_state.history["GoalID"] == gid]
    df = df.sort_values("Date")
    if df.empty:
        return
    progress = df["Progress"].iloc[-1]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Progress"], mode="lines+markers", fill="tozeroy",
        line=dict(color="deepskyblue", shape="spline", width=4),
        marker=dict(size=8, symbol="circle")
    ))
    fig.add_trace(go.Scatter(
        x=[df["Date"].iloc[-1]], y=[progress],
        mode="markers+text", text=[f"🏁 {progress:.2f}"], textposition="top center",
        marker=dict(size=18, color="orange")
    ))
    fig.update_layout(
        height=350, margin=dict(l=10, r=10, t=30, b=30),
        xaxis_title="Date", yaxis_title="Progress",
        showlegend=False, plot_bgcolor="white", paper_bgcolor="white"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"""
        <div style='
            background: #00cec9;
            color: white;
            font-size: 22px;
            padding: 10px 20px;
            border-radius: 12px;
            display: inline-block;
            margin-top: 10px;
            font-weight: bold;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        '>
        🔥 Current Progress: {progress:.2f}
        </div>
    """, unsafe_allow_html=True)

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
        with st.expander(f"{row['GoalName']} - Due: {row['DueDate']}"):
            show_graph(row["GoalID"], row["GoalName"])
            pct = st.selectbox("Progress Today", [0, 50, 100], key=f"pct_{row['GoalID']}")
            if st.button("Update", key=f"btn_{row['GoalID']}"):
                update_progress(row["GoalID"], row["GoalName"], pct)
                st.success("Progress updated!")

# Add goal form
st.markdown("---")
st.subheader("➕ Add New Goal")
with st.form("new_goal"):
    name = st.text_input("Goal Name")
    due = st.date_input("Target Date", min_value=datetime.today())
    freq = st.selectbox("Frequency", ["Daily", "Weekly", "Monthly"])
    submit = st.form_submit_button("Add Goal")
    if submit:
        if name.strip():
            add_goal(name, due, freq)
            st.success(f"Added Goal: {name}")
        else:
            st.error("Goal name is required.")
