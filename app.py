from flask import Flask, render_template, request, redirect, send_file, session, flash
import sqlite3
import pandas as pd
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "super_secret_key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "database.db")


# ---------------- DB INIT ----------------
def init_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            district TEXT,
            location TEXT,
            operator_name TEXT,
            mobile TEXT,
            new_mmmsy INTEGER,
            redo_mmmsy INTEGER,
            report_date TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    users = [("arsh.kaur1", "bhatia1"),
             ("arsh.kaur2", "bhatia2"),
             ("arsh.kaur3", "bhatia3"),
             ("arsh.kaur4", "bhatia4")]

    for user in users:
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", user)
        except:
            pass

    conn.commit()
    conn.close()


init_db()


# ---------------- LOGIN REQUIRED DECORATOR ----------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/")
        else:
            flash("Invalid Credentials")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")


# ---------------- HOME ----------------
# @app.route("/", methods=["GET", "POST"])
# @login_required
# def index():
#     if request.method == "POST":
#         district = request.form["district"]
#         location = request.form["location"]
#         operator_name = request.form["operator_name"]
#         mobile = request.form["mobile"]
#         new_mmmsy = request.form["new_mmmsy"]
#         redo_mmmsy = request.form["redo_mmmsy"]
#
#         today = datetime.now().strftime("%d-%m-%Y")
#
#         # VALIDATION
#         if not mobile.isdigit() or len(mobile) != 10:
#             flash("Mobile number must be 10 digits")
#             return redirect("/")
#
#         if not new_mmmsy.isdigit() or not redo_mmmsy.isdigit():
#             flash("Transactions must be numeric")
#             return redirect("/")
#
#         conn = sqlite3.connect(db_path)
#         cursor = conn.cursor()
#
#         # DUPLICATE CHECK
#         cursor.execute("""
#             SELECT * FROM reports
#             WHERE district=? AND location=? AND operator_name=? AND report_date=?
#         """, (district, location, operator_name, today))
#
#         if cursor.fetchone():
#             flash("Duplicate record for same day not allowed")
#             conn.close()
#             return redirect("/")
#
#         cursor.execute("""
#             INSERT INTO reports
#             (district, location, operator_name, mobile, new_mmmsy, redo_mmmsy, report_date)
#             VALUES (?, ?, ?, ?, ?, ?, ?)
#         """, (district, location, operator_name, mobile, new_mmmsy, redo_mmmsy, today))
#
#         conn.commit()
#         conn.close()
#
#         return render_template("success.html",
#                                district=district,
#                                location=location,
#                                operator_name=operator_name,
#                                mobile=mobile,
#                                new_mmmsy=new_mmmsy,
#                                redo_mmmsy=redo_mmmsy,
#                                today=today)
#
#     today = datetime.now().strftime("%d-%m-%Y")
#     return render_template("index.html", today=today)


@app.route("/")
@login_required
def home():
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM reports ORDER BY id DESC", conn)
    conn.close()
    reports = df.values.tolist()
    return render_template("view.html", reports=reports)


@app.route("/add", methods=["GET", "POST"])
@login_required
def add_report():
    if request.method == "POST":
        district = request.form["district"]
        location = request.form["location"]
        operator_name = request.form["operator_name"]
        mobile = request.form["mobile"]
        new_mmmsy = request.form["new_mmmsy"]
        redo_mmmsy = request.form["redo_mmmsy"]
        today = datetime.now().strftime("%d-%m-%Y")

        # Validation
        if not mobile.isdigit() or len(mobile) != 10:
            flash("Mobile number must be 10 digits")
            return redirect("/add")

        if not new_mmmsy.isdigit() or not redo_mmmsy.isdigit():
            flash("Transactions must be numeric")
            return redirect("/add")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Duplicate check
        cursor.execute("""
            SELECT * FROM reports
            WHERE district=? AND location=? AND operator_name=? AND report_date=?
        """, (district, location, operator_name, today))

        if cursor.fetchone():
            flash("Duplicate record for same day not allowed")
            conn.close()
            return redirect("/add")

        cursor.execute("""
            INSERT INTO reports
            (district, location, operator_name, mobile, new_mmmsy, redo_mmmsy, report_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (district, location, operator_name, mobile, new_mmmsy, redo_mmmsy, today))

        conn.commit()
        conn.close()

        return redirect("/success")

    today = datetime.now().strftime("%d-%m-%Y")
    return render_template("index.html", today=today)


# ---------------- SUCCESS ----------------
@app.route("/success")
@login_required
def success():
    return render_template("success.html")


# ---------------- VIEW ----------------
@app.route("/view")
@login_required
def view():
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM reports ORDER BY id DESC", conn)
    conn.close()
    reports = df.values.tolist()
    return render_template("view.html", reports=reports)


# ---------------- EDIT ----------------
@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if request.method == "POST":
        district = request.form["district"]
        location = request.form["location"]
        operator_name = request.form["operator_name"]
        mobile = request.form["mobile"]
        new_mmmsy = request.form["new_mmmsy"]
        redo_mmmsy = request.form["redo_mmmsy"]

        cursor.execute("""
            UPDATE reports
            SET district=?, location=?, operator_name=?, mobile=?, new_mmmsy=?, redo_mmmsy=?
            WHERE id=?
        """, (district, location, operator_name, mobile, new_mmmsy, redo_mmmsy, id))

        conn.commit()
        conn.close()

        flash("Record updated successfully")
        return redirect("/view")

    cursor.execute("SELECT * FROM reports WHERE id=?", (id,))
    report = cursor.fetchone()
    conn.close()

    return render_template("edit.html", report=report)


# ---------------- DELETE ----------------
@app.route("/delete/<int:id>")
@login_required
def delete(id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reports WHERE id=?", (id,))
    conn.commit()
    conn.close()

    flash("Record deleted successfully")
    return redirect("/view")


# ---------------- EXPORT ----------------
@app.route("/export")
@login_required
def export():
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM reports", conn)
    conn.close()

    file_path = os.path.join(BASE_DIR, "reports.xlsx")
    df.to_excel(file_path, index=False)
    return send_file(file_path, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
