# app.py
from flask import Flask, request, jsonify
from tracker_utils import load_data, load_history, add_goal, update_goal

app = Flask(__name__)

@app.route("/")
def home():
    return "🧠 Habit Tracker API Running!"

@app.route("/add_goal", methods=["POST"])
def api_add_goal():
    data = request.get_json()
    goal_name = data.get("goal_name")
    due_date = data.get("due_date")  # Expected in 'YYYY-MM-DD'
    frequency = data.get("frequency")
    
    goal_id = add_goal(goal_name, due_date, frequency)
    return jsonify({"message": "Goal added", "goal_id": goal_id})

@app.route("/update_goal", methods=["POST"])
def api_update_goal():
    data = request.get_json()
    goal_id = data.get("goal_id")
    percentage = data.get("percentage")
    result = update_goal(goal_id, percentage)
    return jsonify(result)

@app.route("/get_goals", methods=["GET"])
def api_get_goals():
    data = load_data()
    return jsonify(data.to_dict(orient="records"))

@app.route("/get_history/<goal_id>", methods=["GET"])
def api_get_history(goal_id):
    history = load_history()
    goal_history = history[history['GoalID'] == goal_id]
    return jsonify(goal_history.to_dict(orient="records"))

if __name__ == "__main__":
    app.run(debug=True)
