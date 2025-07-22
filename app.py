import streamlit as st
from datetime import datetime, date, timedelta
import pandas as pd
import os
import subprocess
import logging
from pathlib import Path

# =============================================================
# CONFIG
# =============================================================
DATA_FILE = "tracker_data.xlsx"
HISTORY_FILE = "progress_history.xlsx"
BRANCH = "main"
GITHUB_REPO = "parameshwarareddy1/habit-tracker-api"  # <user/repo>

# Progress factors (tweakable)
DAILY_UP_FACTOR = 1.01   # when 100%
HALF_UP_FACTOR = 1.005   # when 50%
DOWN_FACTOR = 1.01       # when 0%

# -------------------------------------------------------------
# Logging
# -------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =============================================================
# PATH HELPERS
# =============================================================
# Use the directory that contains this script when run locally; fall back to cwd.
try:
    BASE_DIR = Path(__file__).parent.resolve()
except NameError:  # when run via streamlit run - script executed as __main__ w/ no __file__ in some envs
    BASE_DIR = Path.cwd().resolve()

DATA_PATH = BASE_DIR / DATA_FILE
HISTORY_PATH = BASE_DIR / HISTORY_FILE

# =============================================================
# UTILITIES
# =============================================================
def _safe_to_date(series):
    """Coerce a Pandas Series to Python date (or NaT-handling)."""
    return pd.to_datetime(series, errors="coerce").dt.date


def get_week_number(d: date) -> int:
    return d.isocalendar()[1]


def _init_dataframes():
    cols_data = ["GoalID", "GoalName", "Frequency", "Progress", "DateAdded", "Week"]
    cols_hist = ["GoalID", "GoalName", "Date", "Progress", "Percentage", "Change"]

    if DATA_PATH.exists():
        try:
            df_data = pd.read_excel(DATA_PATH, engine="openpyxl")
            df_data = df_data.reindex(columns=cols_data)  # ensure column order
            df_data["DateAdded"] = _safe_to_date(df_data["DateAdded"])
            df_data["Week"] = df_data["DateAdded"].apply(lambda d: get_week_number(d) if pd.notna(d) else None)
            logger.info(f"Loaded {DATA_PATH}")
        except Exception as e:
            logger.error(f"Error reading {DATA_PATH}: {e}")
            st.error(f"Error reading {DATA_FILE}: {e}")
            df_data = pd.DataFrame(columns=cols_data)
    else:
        logger.warning(f"{DATA_PATH} not found; starting empty.")
        df_data = pd.DataFrame(columns=cols_data)

    if HISTORY_PATH.exists():
        try:
            df_hist = pd.read_excel(HISTORY_PATH, engine="openpyxl")
            df_hist = df_hist.reindex(columns=cols_hist)
            df_hist["Date"] = _safe_to_date(df_hist["Date"])
            logger.info(f"Loaded {HISTORY_PATH}")
        except Exception as e:
            logger.error(f"Error reading {HISTORY_PATH}: {e}")
            st.error(f"Error reading {HISTORY_FILE}: {e}")
            df_hist = pd.DataFrame(columns=cols_hist)
    else:
        logger.warning(f"{HISTORY_PATH} not found; starting empty.")
        df_hist = pd.DataFrame(columns=cols_hist)

    return df_data, df_hist


# =============================================================
# PERSISTENCE
# =============================================================
def save_dataframes():
    """Persist data + history to Excel and push to GitHub (best effort)."""
    try:
        # Write atomically: write to temp, then replace.
        tmp_data = DATA_PATH.with_suffix(".tmp.xlsx")
        tmp_hist = HISTORY_PATH.with_suffix(".tmp.xlsx")
        st.session_state.data.to_excel(tmp_data, index=False, engine="openpyxl")
        st.session_state.history.to_excel(tmp_hist, index=False, engine="openpyxl")
        tmp_data.replace(DATA_PATH)
        tmp_hist.replace(HISTORY_PATH)
        logger.info("Local Excel files saved.")
    except Exception as e:
        logger.exception("Error saving Excel files")
        st.error(f"Error saving Excel files: {e}")
        return  # bail; don't attempt git if save failed

    # Git push is optional; failure shouldn't break app usage.
    commit_and_push_to_github()


def commit_and_push_to_github():
    """Commit & push changes. Uses token from st.secrets or env."""
    token = st.secrets.get("GITHUB_TOKEN", os.environ.get("GITHUB_TOKEN")) if hasattr(st, "secrets") else os.environ.get("GITHUB_TOKEN")
    if not token:
        logger.warning("No GitHub token found; skipping push.")
        return

    # Config git user (idempotent)
    try:
        subprocess.run(["git", "config", "user.name", "Streamlit Bot"], check=True)
        subprocess.run(["git", "config", "user.email", "bot@streamlit.app"], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"git config failed: {e}")
        return

    # Stage files
    try:
        subprocess.run(["git", "add", str(DATA_PATH), str(HISTORY_PATH)], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"git add failed: {e}")
        return

    # Only commit if something changed
    diff_rc = subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode
    if diff_rc == 1:  # changes present
        commit_msg = f"Update tracker data {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        try:
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            logger.info(f"Committed: {commit_msg}")
        except subprocess.CalledProcessError as e:
            logger.error(f"git commit failed: {e}")
            return
    else:
        logger.info("No changes to commit.")

    # Push (using token in remote URL each time to avoid storing creds)
    remote_url = f"https://{token}@github.com/{GITHUB_REPO}.git"
    try:
        subprocess.run(["git", "push", remote_url, BRANCH], check=True)
        logger.info("Pushed to GitHub.")
    except subprocess.CalledProcessError as e:
        logger.error(f"git push failed: {e}")


# =============================================================
# GOAL CRUD
# =============================================================
def add_goal(name: str, freq: str):
    # Auto-ID: G1, G2 ... based on existing count (including deleted holes -> next integer)
    next_id = len(st.session_state.data) + 1
    goal_id = f"G{next_id}"
    today = date.today()
    week = get_week_number(today)

    new_row = {
        "GoalID": goal_id,
        "GoalName": name.strip(),
        "Frequency": freq,
        "Progress": 1.0,
        "DateAdded": today,
        "Week": week,
    }

    hist_row = {
        "GoalID": goal_id,
        "GoalName": name.strip(),
        "Date": today,
        "Progress": 1.0,
        "Percentage": 0,
        "Change": 0.0,
    }

    st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_row])], ignore_index=True)
    st.session_state.history = pd.concat([st.session_state.history, pd.DataFrame([hist_row])], ignore_index=True)

    save_dataframes()
    st.success(f"Added Goal: {name}")
    st.rerun()


def _get_goal_frequency(goal_id: str) -> str:
    try:
        return st.session_state.data.loc[st.session_state.data["GoalID"] == goal_id, "Frequency"].iloc[0]
    except IndexError:
        return "Daily"  # fallback


def update_progress(goal_id: str, goal_name: str, pct: int):
    today = date.today()
    current_week = get_week_number(today)
    freq = _get_goal_frequency(goal_id)

    hist = st.session_state.history
    if freq == "Weekly":
        already = hist[(hist["GoalID"] == goal_id) & (hist["Date"].apply(get_week_number) == current_week)]
        if not already.empty:
            st.error(f"Already updated for week {current_week}.")
            return
    elif freq == "Monthly":
        already = hist[(hist["GoalID"] == goal_id) & (pd.to_datetime(hist["Date"]).dt.to_period('M') == pd.Period(today, freq='M'))]
        if not already.empty:
            st.error("Already updated this month.")
            return
    else:  # Daily
        already = hist[(hist["GoalID"] == goal_id) & (hist["Date"] == today)]
        if not already.empty:
            st.error("Already updated today.")
            return

    # Current progress
    current_progress = st.session_state.data.loc[st.session_state.data["GoalID"] == goal_id, "Progress"].iloc[0]

    if pct == 100:
        new_progress = current_progress * DAILY_UP_FACTOR
        change = DAILY_UP_FACTOR - 1.0
    elif pct == 50:
        new_progress = current_progress * HALF_UP_FACTOR
        change = HALF_UP_FACTOR - 1.0
    else:  # 0
        new_progress = current_progress / DOWN_FACTOR
        change = -(DOWN_FACTOR - 1.0)

    st.session_state.data.loc[st.session_state.data["GoalID"] == goal_id, "Progress"] = new_progress

    row = {
        "GoalID": goal_id,
        "GoalName": goal_name,
        "Date": today,
        "Progress": new_progress,
        "Percentage": pct,
        "Change": change,
    }
    st.session_state.history = pd.concat([st.session_state.history, pd.DataFrame([row])], ignore_index=True)

    save_dataframes()
    st.success("Progress updated!")
    st.rerun()


def delete_goal(goal_id: str, goal_name: str):
    st.session_state.data = st.session_state.data[st.session_state.data["GoalID"] != goal_id].copy()
    st.session_state.history = st.session_state.history[st.session_state.history["GoalID"] != goal_id].copy()
    save_dataframes()
    st.success(f"Deleted: {goal_name}")
    st.rerun()


# =============================================================
# METRICS / INFO
# =============================================================
def calculate_potential_progress(start_date: date) -> float:
    """Potential if you had hit 100% every day since start."""
    days = (date.today() - start_date).days
    potential = 1.0
    for _ in range(days + 1):
        potential *= DAILY_UP_FACTOR
    return potential


def show_progress_info(goal_id: str, goal_name: str):
    df_goal_hist = st.session_state.history[st.session_state.history["GoalID"] == goal_id].sort_values("Date")
    if df_goal_hist.empty:
        return
    latest_progress = df_goal_hist["Progress"].iloc[-1]
    start_date = st.session_state.data.loc[st.session_state.data["GoalID"] == goal_id, "DateAdded"].iloc[0]
    potential_progress = calculate_potential_progress(start_date)
    today = date.today()

    st.markdown(f"""
        <div style='display:flex;flex-direction:column;gap:12px;margin-top:8px;'>
            <div style='background:#ff6b6b;color:white;padding:10px;border-radius:8px;text-align:center;font-weight:bold;'>🎯 Potential Progress: {potential_progress:.3f}</div>
            <div style='background:#4facfe;color:white;padding:10px;border-radius:8px;text-align:center;font-weight:bold;'>🔥 Actual Progress: {latest_progress:.3f}</div>
            <div style='background:#2ecc71;color:white;padding:10px;border-radius:8px;text-align:center;font-weight:bold;'>🚀 Start Date: {start_date:%Y-%m-%d}</div>
            <div style='background:#a29bfe;color:white;padding:10px;border-radius:8px;text-align:center;font-weight:bold;'>📅 Today: {today:%Y-%m-%d}</div>
        </div>
    """, unsafe_allow_html=True)


def show_last_7_days(goal_id: str) -> str:
    today = date.today()
    start_date = st.session_state.data.loc[st.session_state.data["GoalID"] == goal_id, "DateAdded"].iloc[0]
    display_start = max(today - timedelta(days=6), start_date)
    date_range = [display_start + timedelta(days=i) for i in range((today - display_start).days + 1)]

    df = st.session_state.history
    df_goal = df[df["GoalID"] == goal_id]

    emojis = []
    for d in date_range:
        if d == start_date:
            emojis.append("🚀")
            continue
        row = df_goal[df_goal["Date"] == d]
        if row.empty:
            emojis.append("⬜")
        else:
            pct = int(row["Percentage"].iloc[-1])
            emojis.append("🟢" if pct == 100 else "🟡" if pct == 50 else "🔴")
    return " ".join(emojis)


# =============================================================
# CALENDAR (FIXED: date-vs-string bug + Sunday-first grid)
# =============================================================
WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def _first_day_sunday_index(d: date) -> int:
    """Return column index (0=Sun) for given date (Python weekday 0=Mon)."""
    # Convert Python Monday=0..Sunday=6 to Sunday=0..Saturday=6
    return (d.weekday() + 1) % 7


def show_calendar(goal_id: str, year: int | None = None, month: int | None = None):
    try:
        today = date.today()
        year = year or today.year
        month = month or today.month

        start_date = st.session_state.data.loc[st.session_state.data["GoalID"] == goal_id, "DateAdded"].iloc[0]
        df_goal = st.session_state.history[st.session_state.history["GoalID"] == goal_id]

        # Build dict keyed by *date* (not string) so comparisons work.
        # If multiple entries per day, take last one.
        df_goal_sorted = df_goal.sort_values("Date")
        hist_by_date = df_goal_sorted.groupby("Date").tail(1).set_index("Date")["Percentage"].to_dict()

        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)

        # Leading pads to align Sunday-first grid.
        pad_count = _first_day_sunday_index(first_day)
        cells = ["" for _ in range(pad_count)]

        for d in range(1, last_day.day + 1):
            ds = date(year, month, d)
            if ds > today:
                emoji = ""  # future blank
            elif ds == start_date:
                emoji = "🚀"
            elif ds in hist_by_date:
                pct = int(hist_by_date[ds])
                emoji = "🟢" if pct == 100 else "🟡" if pct == 50 else "🔴"
            else:
                emoji = "⬜"
            cells.append(f"{d} {emoji}")

        # Pad trailing cells so grid multiple of 7
        while len(cells) % 7 != 0:
            cells.append("")

        # Render grid HTML
        header_html = "".join(
            f"<div style='font-weight:bold;background:#eee;padding:6px;text-align:center;'>{lbl}</div>" for lbl in WEEKDAY_LABELS
        )
        body_html = "".join(
            f"<div style='padding:6px;text-align:center;border:1px solid #ccc;min-height:32px;'>{c}</div>" for c in cells
        )
        calendar_html = f"""
            <h4 style='margin-top:0;'>Calendar for {year}-{month:02d}</h4>
            <div style='display:grid;grid-template-columns:repeat(7,1fr);gap:4px;'>
              {header_html}
              {body_html}
            </div>
        """
        st.markdown(calendar_html, unsafe_allow_html=True)

        # Legend
        st.caption("🚀 Start • 🟢100% • 🟡50% • 🔴0% • ⬜ Miss • Blank=future")

    except Exception as e:
        logger.exception("Error in show_calendar")
        st.error(f"Error displaying calendar: {e}")


# =============================================================
# SIDEBAR CONTROLS
# =============================================================
def sidebar_controls():
    st.sidebar.header("Options")
    if st.sidebar.button("Reload from disk / Git"):
        st.session_state.data, st.session_state.history = _init_dataframes()
        st.experimental_rerun()

    st.sidebar.write("\n")
    st.sidebar.write("Data & History rows:")
    st.sidebar.metric("Goals", len(st.session_state.data))
    st.sidebar.metric("History", len(st.session_state.history))


# =============================================================
# MAIN UI
# =============================================================
st.set_page_config(page_title="Goal Tracker", layout="wide")
st.title("🎯 Goal Tracker")

# Initialize state on first load OR when explicitly reloaded.
if "data" not in st.session_state or "history" not in st.session_state:
    st.session_state.data, st.session_state.history = _init_dataframes()

# Sidebar
sidebar_controls()

# Existing goals ------------------------------------------------
if st.session_state.data.empty:
    st.info("No goals yet. Add one below.")
else:
    st.subheader("📌 Your Goals")
    for _, row in st.session_state.data.iterrows():
        gid = row["GoalID"]
        gname = row["GoalName"]
        last_7 = show_last_7_days(gid)
        with st.expander(f"{gname} | Last 7 Days: {last_7}"):
            show_progress_info(gid, gname)
            col1, col2, col3 = st.columns([1,1,1])
            with col1:
                pct = st.selectbox("Progress", [0,50,100], key=f"pct_{gid}")
                if st.button("Update", key=f"btn_{gid}"):
                    update_progress(gid, gname, pct)
            with col2:
                if st.button("Delete Goal", key=f"del_{gid}"):
                    delete_goal(gid, gname)
            with col3:
                if st.button("Show Calendar", key=f"cal_{gid}"):
                    # optional month/year pickers (populated w/ current month defaults)
                    with st.popover("Pick Month", key=f"pop_{gid}"):
                        sel_year = st.number_input("Year", min_value=2000, max_value=2100, value=date.today().year, key=f"yr_{gid}")
                        sel_month = st.number_input("Month", min_value=1, max_value=12, value=date.today().month, key=f"mo_{gid}")
                        if st.button("Show", key=f"showcal_{gid}"):
                            show_calendar(gid, int(sel_year), int(sel_month))
                    # Also show current month immediately for convenience
                    show_calendar(gid)

# Add new goal --------------------------------------------------
st.subheader("Add New Goal")
with st.form("add_goal_form", clear_on_submit=True):
    name = st.text_input("Goal Name")
    freq = st.selectbox("Frequency", ["Daily", "Weekly", "Monthly"])
    submitted = st.form_submit_button("Add Goal")
    if submitted:
        if not name.strip():
            st.warning("Please enter a goal name.")
        else:
            add_goal(name, freq)

# =============================================================
# DEBUG PANEL (optional)
# =============================================================
with st.expander("🔧 Debug DataFrames"):
    st.write("**Data**")
    st.dataframe(st.session_state.data)
    st.write("**History**")
    st.dataframe(st.session_state.history)
    st.caption(f"Files located at:\n{DATA_PATH}\n{HISTORY_PATH}")
