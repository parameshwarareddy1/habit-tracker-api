# tracker_utils.py
import pandas as pd
import os
from datetime import datetime

DATA_FILE = "tracker_data.csv"
HISTORY_FILE = "progress_history.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        data = pd.read_csv(DATA_FILE)
        data['DueDate'] = pd.to_datetime(data['DueDate']).dt.date
        data['DateAdded'] = pd.to_datetime(data['DateAdded']).dt.date
    else:
        data = pd.DataFrame(columns=[
            'GoalID', 'GoalName', 'DueDate', 'Frequency', 'Progress', 'DateAdded', 'Week'
        ])
    return data

def load_history():
    if os.path.exists(HISTORY_FILE):
        history = pd.read_csv(HISTORY_FILE)
        history['Date'] = pd.to_datetime(history['Date']).dt.date
    else:
        history = pd.DataFrame(columns=['GoalID', 'GoalName', 'Date', 'Progress', 'Percentage', 'Change'])
    return history

def save_data(data, history):
    data.to_csv(DATA_FILE, index=False)
    history.to_csv(HISTORY_FILE, index=False)

def get_week_number(date):
    return date.isocalendar()[1]

def add_goal(goal_name, due_date, frequency):
    data = load_data()
    history = load_history()
    current_date = datetime.now().date()
    week = get_week_number(current_date)
    goal_id = f"G{len(data['GoalID'].unique()) + 1}" if not data.empty else "G1"

    new_item = {
        'GoalID': goal_id,
        'GoalName': goal_name,
        'DueDate': due_date,
        'Frequency': frequency,
        'Progress': 1.0,
        'DateAdded': current_date,
        'Week': week
    }
    data = pd.concat([data, pd.DataFrame([new_item])], ignore_index=True)

    new_history = {
        'GoalID': goal_id,
        'GoalName': goal_name,
        'Date': current_date,
        'Progress': 1.0,
        'Percentage': 0.0,
        'Change': 0.0
    }
    history = pd.concat([history, pd.DataFrame([new_history])], ignore_index=True)
    save_data(data, history)
    return goal_id

def update_goal(goal_id, percentage):
    data = load_data()
    history = load_history()
    current_date = datetime.now().date()

    goal_row = data[data['GoalID'] == goal_id]
    if goal_row.empty:
        return {"error": "Goal ID not found"}

    current_progress = goal_row['Progress'].iloc[0]

    if percentage == 100:
        new_progress = current_progress * 1.01
        change = 0.01
    elif percentage == 50:
        new_progress = current_progress * 1.005
        change = 0.005
    else:
        new_progress = current_progress / 1.01
        change = -0.01

    data.loc[data['GoalID'] == goal_id, 'Progress'] = new_progress

    history_entry = {
        'GoalID': goal_id,
        'GoalName': goal_row['GoalName'].iloc[0],
        'Date': current_date,
        'Progress': new_progress,
        'Percentage': float(percentage),
        'Change': change
    }
    history = pd.concat([history, pd.DataFrame([history_entry])], ignore_index=True)
    save_data(data, history)
    return {"message": "Goal updated", "new_progress": new_progress}
