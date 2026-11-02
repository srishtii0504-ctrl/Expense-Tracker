import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash

# Initialize the Flask application
app = Flask(__name__)

# Secret key is required by Flask to display flash messages (alert popups)
app.secret_key = "student_expense_tracker_secret_key"

# Path to our SQLite database file
DATABASE = "expenses.db"

# Predefined list of standard categories requested for students
CATEGORIES = [
    "Food",
    "Travel",
    "Shopping",
    "Education",
    "Entertainment",
    "Healthcare",
    "Other"
]


def get_db_connection():
    """
    Helper function to establish a connection to the SQLite database.
    Setting row_factory to sqlite3.Row allows accessing columns by name like a dictionary.
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Creates the required database tables automatically if they do not already exist.
    Called when the application starts.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Table 1: expenses (Stores all student expense records)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL
        )
    """)

    # Table 2: budget (Stores monthly budget amounts)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budget (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month_year TEXT UNIQUE NOT NULL,
            amount REAL NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# -------------------------------------------------------------------
# ROUTE 1: DASHBOARD (Home Page)
# -------------------------------------------------------------------
@app.route("/")
def index():
    """
    Displays the main dashboard:
    1. Total expense sum
    2. Total transaction count
    3. Monthly budget summary (budget, spent this month, remaining)
    4. Table of all recorded expenses (sorted by date descending)
    """
    conn = get_db_connection()

    # 1. Fetch all expenses ordered with most recent first
    expenses = conn.execute(
        "SELECT * FROM expenses ORDER BY date DESC, id DESC"
    ).fetchall()

    # 2. Calculate overall total expenses and count
    total_expenses = sum(expense["amount"] for expense in expenses)
    total_transactions = len(expenses)

    # 3. Monthly budget calculations for the current month
    current_month_str = datetime.now().strftime("%Y-%m")  # Format: "2026-11"
    current_month_name = datetime.now().strftime("%B %Y")  # Format: "November 2026"

    # Get budget for this month if set by user
    budget_row = conn.execute(
        "SELECT amount FROM budget WHERE month_year = ?", (current_month_str,)
    ).fetchone()

    monthly_budget = budget_row["amount"] if budget_row else 0.0

    # Calculate total spent specifically in this current month
    month_spent_row = conn.execute(
        "SELECT SUM(amount) AS total FROM expenses WHERE strftime('%Y-%m', date) = ?",
        (current_month_str,)
    ).fetchone()
    monthly_spent = month_spent_row["total"] if month_spent_row["total"] else 0.0

    # Calculate remaining budget and warning status
    remaining_budget = monthly_budget - monthly_spent
    is_budget_exceeded = monthly_spent > monthly_budget and monthly_budget > 0

    conn.close()

    return render_template(
        "index.html",
        expenses=expenses,
        total_expenses=total_expenses,
        total_transactions=total_transactions,
        monthly_budget=monthly_budget,
        monthly_spent=monthly_spent,
        remaining_budget=remaining_budget,
        is_budget_exceeded=is_budget_exceeded,
        current_month_name=current_month_name
    )


# -------------------------------------------------------------------
# ROUTE 2: ADD EXPENSE
# -------------------------------------------------------------------
@app.route("/add", methods=["GET", "POST"])
def add_expense():
    """
    Allows adding a new expense:
    - GET: Shows the form with categories and default date (today)
    - POST: Validates input, saves to database, and redirects to dashboard
    """
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        amount_str = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        expense_date = request.form.get("date", "").strip()

        # Input Validation
        if not title:
            flash("Please enter an expense name.", "error")
            return redirect(url_for("add_expense"))

        try:
            amount = float(amount_str)
            if amount <= 0:
                flash("Amount must be greater than zero.", "error")
                return redirect(url_for("add_expense"))
        except ValueError:
            flash("Please enter a valid numeric amount.", "error")
            return redirect(url_for("add_expense"))

        if category not in CATEGORIES:
            flash("Please select a valid category from the list.", "error")
            return redirect(url_for("add_expense"))

        if not expense_date:
            flash("Please select a valid date.", "error")
            return redirect(url_for("add_expense"))

        # Save to SQLite Database
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO expenses (title, amount, category, date) VALUES (?, ?, ?, ?)",
            (title, amount, category, expense_date)
        )
        conn.commit()
        conn.close()

        flash("Expense added successfully!", "success")
        return redirect(url_for("index"))

    # For GET request, supply today's date as default
    today_date = datetime.now().strftime("%Y-%m-%d")
    return render_template("add_expense.html", categories=CATEGORIES, today_date=today_date)


# -------------------------------------------------------------------
# ROUTE 3: EDIT EXPENSE
# -------------------------------------------------------------------
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_expense(id):
    """
    Allows editing an existing expense record:
    - GET: Loads current expense data into the form
    - POST: Updates the record in SQLite
    """
    conn = get_db_connection()
    expense = conn.execute("SELECT * FROM expenses WHERE id = ?", (id,)).fetchone()

    if expense is None:
        conn.close()
        flash("Expense not found.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        amount_str = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        expense_date = request.form.get("date", "").strip()

        # Input Validation
        if not title:
            flash("Expense name cannot be empty.", "error")
            return redirect(url_for("edit_expense", id=id))

        try:
            amount = float(amount_str)
            if amount <= 0:
                flash("Amount must be greater than zero.", "error")
                return redirect(url_for("edit_expense", id=id))
        except ValueError:
            flash("Please enter a valid numeric amount.", "error")
            return redirect(url_for("edit_expense", id=id))

        if category not in CATEGORIES:
            flash("Please select a valid category.", "error")
            return redirect(url_for("edit_expense", id=id))

        if not expense_date:
            flash("Please select a date.", "error")
            return redirect(url_for("edit_expense", id=id))

        # Update record in Database
        conn.execute(
            "UPDATE expenses SET title = ?, amount = ?, category = ?, date = ? WHERE id = ?",
            (title, amount, category, expense_date, id)
        )
        conn.commit()
        conn.close()

        flash("Expense updated successfully!", "success")
        return redirect(url_for("index"))

    conn.close()
    return render_template("edit_expense.html", expense=expense, categories=CATEGORIES)


# -------------------------------------------------------------------
# ROUTE 4: DELETE EXPENSE
# -------------------------------------------------------------------
@app.route("/delete/<int:id>", methods=["POST", "GET"])
def delete_expense(id):
    """
    Deletes an expense record from the database.
    Accessible via form submission or link.
    """
    conn = get_db_connection()
    conn.execute("DELETE FROM expenses WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    flash("Expense deleted successfully!", "success")
    return redirect(url_for("index"))


# -------------------------------------------------------------------
# ROUTE 5: MONTHLY BUDGET
# -------------------------------------------------------------------
@app.route("/budget", methods=["GET", "POST"])
def budget():
    """
    Manages the monthly budget:
    - View current month's budget and expense summary
    - Set or update the budget amount for the current month
    - Displays warnings if budget is exceeded
    """
    current_month_str = datetime.now().strftime("%Y-%m")
    current_month_name = datetime.now().strftime("%B %Y")

    conn = get_db_connection()

    if request.method == "POST":
        amount_str = request.form.get("budget_amount", "").strip()

        try:
            budget_amount = float(amount_str)
            if budget_amount < 0:
                flash("Budget amount cannot be negative.", "error")
                return redirect(url_for("budget"))

            # Insert or replace budget for this month
            conn.execute("""
                INSERT INTO budget (month_year, amount)
                VALUES (?, ?)
                ON CONFLICT(month_year) DO UPDATE SET amount = excluded.amount
            """, (current_month_str, budget_amount))
            conn.commit()

            flash("Monthly budget updated successfully!", "success")
            return redirect(url_for("budget"))

        except ValueError:
            flash("Please enter a valid numeric budget amount.", "error")
            return redirect(url_for("budget"))

    # Fetch budget for current month
    budget_row = conn.execute(
        "SELECT amount FROM budget WHERE month_year = ?", (current_month_str,)
    ).fetchone()
    monthly_budget = budget_row["amount"] if budget_row else 0.0

    # Calculate total spent in this month
    month_spent_row = conn.execute(
        "SELECT SUM(amount) AS total FROM expenses WHERE strftime('%Y-%m', date) = ?",
        (current_month_str,)
    ).fetchone()
    monthly_spent = month_spent_row["total"] if month_spent_row["total"] else 0.0

    remaining_budget = monthly_budget - monthly_spent
    is_budget_exceeded = monthly_spent > monthly_budget and monthly_budget > 0

    # Calculate percentage spent for visual progress
    percentage_spent = 0
    if monthly_budget > 0:
        percentage_spent = min(round((monthly_spent / monthly_budget) * 100, 1), 100)

    conn.close()

    return render_template(
        "budget.html",
        current_month_name=current_month_name,
        monthly_budget=monthly_budget,
        monthly_spent=monthly_spent,
        remaining_budget=remaining_budget,
        is_budget_exceeded=is_budget_exceeded,
        percentage_spent=percentage_spent
    )


# Application entry point: automatically initializes database and runs server
if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
    print("Running Student Expense Tracker on http://127.0.0.1:5000")
    app.run(debug=True)
