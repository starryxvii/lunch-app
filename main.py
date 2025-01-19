from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import sqlite3, os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('secret_key')
DATABASE = "lunch_app.db"

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Create the orders table with timestamp
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            meal TEXT,
            picked_up BOOLEAN DEFAULT FALSE,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create the menu table with calories and protein
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            image TEXT,
            calories INTEGER,
            protein INTEGER
        )
    """)

    # Create the daily_menu table for scheduling
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheduled_date DATE NOT NULL,
            menu_id INTEGER NOT NULL,
            FOREIGN KEY (menu_id) REFERENCES menu (id)
        )
    """)

    # Add default menu items if the menu table is empty
    cursor.execute("SELECT COUNT(*) FROM menu")
    if cursor.fetchone()[0] == 0:
        default_menu = [
            ("Pizza", "Cheesy and delicious.", "images/pizza.jpg", 300, 12),
            ("Burger", "Juicy and flavorful.", "images/burger.jpg", 500, 25),
            ("Salad", "Fresh and healthy.", "images/salad.jpg", 150, 5)
        ]
        cursor.executemany(
            "INSERT INTO menu (name, description, image, calories, protein) VALUES (?, ?, ?, ?, ?)",
            default_menu
        )

    # Schedule default meals for today if no schedules exist
    today = datetime.now().date()
    cursor.execute("SELECT COUNT(*) FROM daily_menu WHERE scheduled_date = ?", (today,))
    if cursor.fetchone()[0] == 0:
        # Retrieve all menu item IDs
        cursor.execute("SELECT id FROM menu")
        menu_ids = [row[0] for row in cursor.fetchall()]

        # Schedule all menu items for today
        for menu_id in menu_ids:
            cursor.execute("INSERT INTO daily_menu (scheduled_date, menu_id) VALUES (?, ?)", (today, menu_id))

    conn.commit()
    conn.close()



@app.route("/")
def login():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def handle_login():
    username = request.form["username"]
    password = request.form["password"]

    # Admin login
    if username.lower() == "admin" and password == "admin123":
        session["user"] = "admin"
        return redirect(url_for("admin_orders"))  # Redirect to orders page

    # Student login
    elif username.isdigit():
        session["user"] = username
        return redirect(url_for("student_menu"))

    # Invalid login
    else:
        return render_template("login.html", error="Invalid username or password")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/student_menu")
def student_menu():
    if "user" not in session or not session["user"].isdigit():
        return redirect(url_for("login"))

    today = datetime.now().date()
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Retrieve meals scheduled for today
    cursor.execute("""
        SELECT menu.name, menu.description, menu.image, menu.calories, menu.protein
        FROM daily_menu
        JOIN menu ON daily_menu.menu_id = menu.id
        WHERE daily_menu.scheduled_date = ?
    """, (today,))
    menu = cursor.fetchall()
    conn.close()

    if not menu:
        return render_template("student_menu.html", menu=[], message="No meals are scheduled for today.")

    return render_template("student_menu.html", menu=[
        {"name": row[0], "description": row[1], "image": row[2], "calories": row[3], "protein": row[4]}
        for row in menu
    ])


@app.route("/submit_order", methods=["POST"])
def submit_order():
    if "user" not in session or not session["user"].isdigit():
        return redirect(url_for("login"))

    student_id = session["user"]
    meal = request.form["meal"]

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (student_id, meal) VALUES (?, ?)", (student_id, meal))
    conn.commit()
    conn.close()

    return render_template("confirmation.html", meal=meal)

@app.route("/admin/orders")
def admin_orders():
    if "user" not in session or session["user"] != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Retrieve sorted orders
    cursor.execute("""
        SELECT id, student_id, meal, picked_up, timestamp
        FROM orders
        ORDER BY timestamp DESC
    """)
    orders = cursor.fetchall()
    conn.close()

    return render_template("admin_orders.html", orders=orders)


@app.route("/admin/schedule")
def admin_schedule():
    if "user" not in session or session["user"] != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Retrieve scheduled meals
    cursor.execute("""
        SELECT daily_menu.scheduled_date, menu.name, menu.description, menu.calories, menu.image
        FROM daily_menu
        JOIN menu ON daily_menu.menu_id = menu.id
        ORDER BY daily_menu.scheduled_date
    """)
    scheduled_menu = cursor.fetchall()

    # Retrieve available menu items
    cursor.execute("SELECT id, name FROM menu")
    menu = cursor.fetchall()
    conn.close()

    return render_template("admin_schedule.html", scheduled_menu=scheduled_menu, menu=menu)


@app.route("/admin/menu")
def admin_menu():
    if "user" not in session or session["user"] != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Retrieve all menu items
    cursor.execute("SELECT id, name, description, image, calories, protein FROM menu")
    menu = cursor.fetchall()
    conn.close()

    return render_template("admin_menu.html", menu=menu)



@app.route("/add_menu_item", methods=["POST"])
def add_menu_item():
    if "user" not in session or session["user"] != "admin":
        return redirect(url_for("login"))

    name = request.form["name"]
    description = request.form["description"]
    image = request.form["image"]
    calories = request.form["calories"]
    protein = request.form["protein"]

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO menu (name, description, image, calories, protein) VALUES (?, ?, ?, ?, ?)", 
                   (name, description, image, calories, protein))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_menu"))

@app.route("/delete_menu_item/<int:menu_id>")
def delete_menu_item(menu_id):
    if "user" not in session or session["user"] != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM menu WHERE id = ?", (menu_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_menu"))  # Redirect to Manage Menu page


@app.route("/mark_picked_up", methods=["POST"])
def mark_picked_up():
    if "user" not in session or session["user"] != "admin":
        return redirect(url_for("login"))

    order_id = request.form["order_id"]

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET picked_up = 1 WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))

@app.route("/api/orders")
def get_orders():
    if "user" not in session or session["user"] != "admin":
        return jsonify({"error": "Unauthorized"}), 401

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, student_id, meal, picked_up, timestamp
        FROM orders
        ORDER BY timestamp DESC
    """)
    orders = cursor.fetchall()
    conn.close()

    return jsonify([
        {
            "id": order[0],
            "student_id": order[1],
            "meal": order[2],
            "picked_up": order[3],
            "timestamp": order[4]
        }
        for order in orders
    ])

@app.route("/schedule_menu", methods=["POST"])
def schedule_menu():
    if "user" not in session or session["user"] != "admin":
        return redirect(url_for("login"))

    scheduled_date = request.form["scheduled_date"]
    menu_id = request.form["menu_id"]

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO daily_menu (scheduled_date, menu_id) VALUES (?, ?)", 
        (scheduled_date, menu_id)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("admin_schedule"))  # Redirect to Schedule Meals page


@app.route("/get_scheduled_menu/<date>")
def get_scheduled_menu(date):
    if "user" not in session or session["user"] != "admin":
        return jsonify({"error": "Unauthorized"}), 401

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT menu.name, menu.description, menu.image, menu.calories
        FROM daily_menu
        JOIN menu ON daily_menu.menu_id = menu.id
        WHERE daily_menu.scheduled_date = ?
    """, (date,))
    scheduled_menu = cursor.fetchall()
    conn.close()

    return jsonify([
        {"name": row[0], "description": row[1], "image": row[2], "calories": row[3]}
        for row in scheduled_menu
    ])


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
