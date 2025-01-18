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

    # Create the menu table with calories
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            image TEXT,
            calories INTEGER
        )
    """)

    # Add default menu items if the table is empty
    cursor.execute("SELECT COUNT(*) FROM menu")
    if cursor.fetchone()[0] == 0:
        default_menu = [
            ("Pizza", "Cheesy and delicious.", "images/pizza.jpg", 300),
            ("Burger", "Juicy and flavorful.", "images/burger.jpg", 500),
            ("Salad", "Fresh and healthy.", "images/salad.jpg", 150)
        ]
        cursor.executemany("INSERT INTO menu (name, description, image, calories) VALUES (?, ?, ?, ?)", default_menu)

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
        return redirect(url_for("admin_dashboard"))

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

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, description, image, calories FROM menu")
    menu = cursor.fetchall()
    conn.close()

    return render_template("student_menu.html", menu=[
        {"name": row[0], "description": row[1], "image": row[2], "calories": row[3]} for row in menu
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

@app.route("/admin_dashboard")
def admin_dashboard():
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

    # Retrieve menu items with calories
    cursor.execute("SELECT id, name, description, image, calories FROM menu")
    menu = cursor.fetchall()

    conn.close()

    return render_template("admin_dashboard.html", orders=orders, menu=menu)

@app.route("/add_menu_item", methods=["POST"])
def add_menu_item():
    if "user" not in session or session["user"] != "admin":
        return redirect(url_for("login"))

    name = request.form["name"]
    description = request.form["description"]
    image = request.form["image"]
    calories = request.form["calories"]

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO menu (name, description, image, calories) VALUES (?, ?, ?, ?)", 
                   (name, description, image, calories))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))

@app.route("/delete_menu_item/<int:menu_id>")
def delete_menu_item(menu_id):
    if "user" not in session or session["user"] != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM menu WHERE id = ?", (menu_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))

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

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
