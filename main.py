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

    # Create the orders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            meal TEXT,
            picked_up BOOLEAN DEFAULT FALSE,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create the menu table
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

    # Create the daily_menu table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheduled_date DATE NOT NULL,
            menu_id INTEGER NOT NULL,
            FOREIGN KEY (menu_id) REFERENCES menu (id)
        )
    """)

    # Create the students table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id TEXT PRIMARY KEY,
            preferences TEXT DEFAULT NULL
        )
    """)

    # Add default menu items
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

    conn.commit()
    conn.close()

@app.route("/preferences", methods=["GET", "POST"])
def preferences():
    if "user" not in session or not session["user"].isdigit():
        return redirect(url_for("login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == "POST":
        preference = request.form["preference"]
        student_id = session["user"]

        cursor.execute("""
            INSERT INTO students (id, preferences)
            VALUES (?, ?)
            ON CONFLICT(id) DO UPDATE SET preferences = ?
        """, (student_id, preference, preference))

        conn.commit()
        message = "Preference updated successfully."
    else:
        student_id = session["user"]
        cursor.execute("SELECT preferences FROM students WHERE id = ?", (student_id,))
        result = cursor.fetchone()
        preference = result[0] if result else None
        message = None

    conn.close()
    return render_template("preferences.html", preference=preference, message=message)


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

@app.route("/student_menu", methods=["GET", "POST"])
def student_menu():
    if "user" not in session or not session["user"].isdigit():
        return redirect(url_for("login"))

    student_id = session["user"]
    today = datetime.now().date()
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Get student preference
    cursor.execute("SELECT preferences FROM students WHERE id = ?", (student_id,))
    result = cursor.fetchone()
    preference = result[0] if result else None

    # Get today's menu
    cursor.execute("""
        SELECT menu.id, menu.name, menu.description, menu.image, menu.calories, menu.protein
        FROM daily_menu
        JOIN menu ON daily_menu.menu_id = menu.id
        WHERE daily_menu.scheduled_date = ?
    """, (today,))
    menu = cursor.fetchall()

    # Determine preordered meal based on preference
    preordered_meal = None
    if preference and menu:
        if preference == "least calories":
            cursor.execute("""
                SELECT menu.name
                FROM daily_menu
                JOIN menu ON daily_menu.menu_id = menu.id
                WHERE daily_menu.scheduled_date = ?
                ORDER BY menu.calories ASC
                LIMIT 1
            """, (today,))
        elif preference == "most calories":
            cursor.execute("""
                SELECT menu.name
                FROM daily_menu
                JOIN menu ON daily_menu.menu_id = menu.id
                WHERE daily_menu.scheduled_date = ?
                ORDER BY menu.calories DESC
                LIMIT 1
            """, (today,))
        elif preference == "most protein":
            cursor.execute("""
                SELECT menu.name
                FROM daily_menu
                JOIN menu ON daily_menu.menu_id = menu.id
                WHERE daily_menu.scheduled_date = ?
                ORDER BY menu.protein DESC
                LIMIT 1
            """, (today,))
        else:
            cursor.execute("""
                SELECT menu.name
                FROM daily_menu
                JOIN menu ON daily_menu.menu_id = menu.id
                WHERE daily_menu.scheduled_date = ?
                ORDER BY menu.calories ASC
                LIMIT 1
            """, (today,))
        
        preordered_meal_result = cursor.fetchone()
        preordered_meal = preordered_meal_result[0] if preordered_meal_result else None

    # Handle manual overrides
    if request.method == "POST":
        selected_meal = request.form["meal"]
        cursor.execute("INSERT INTO orders (student_id, meal) VALUES (?, ?)", (student_id, selected_meal))
        conn.commit()
        conn.close()
        return render_template("confirmation.html", meal=selected_meal)

    conn.close()
    return render_template("student_menu.html", menu=[
        {"id": row[0], "name": row[1], "description": row[2], "image": row[3], "calories": row[4], "protein": row[5]}
        for row in menu
    ], preference=preference, preordered_meal=preordered_meal)


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

    return redirect(url_for("admin_orders"))

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

    # Schedule the meal
    cursor.execute(
        "INSERT INTO daily_menu (scheduled_date, menu_id) VALUES (?, ?)", 
        (scheduled_date, menu_id)
    )

    # Automated preordering for students
    cursor.execute("SELECT id, preferences FROM students")
    students = cursor.fetchall()

    for student_id, preference in students:
        if preference:
            cursor.execute("""
                SELECT menu.name
                FROM daily_menu
                JOIN menu ON daily_menu.menu_id = menu.id
                WHERE daily_menu.scheduled_date = ?
                ORDER BY
                    CASE
                        WHEN ? = 'least calories' THEN menu.calories
                        WHEN ? = 'most calories' THEN menu.calories DESC
                        WHEN ? = 'most protein' THEN menu.protein DESC
                    END
                LIMIT 1
            """, (scheduled_date, preference, preference, preference))
            meal = cursor.fetchone()
            if meal:
                cursor.execute("INSERT INTO orders (student_id, meal) VALUES (?, ?)", (student_id, meal[0]))

    conn.commit()
    conn.close()

    return redirect(url_for("admin_schedule"))

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
