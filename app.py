from flask import Flask, render_template, request, redirect, send_file
import sqlite3
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "database.db")


# CREATE DATABASE TABLE
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

    conn.commit()
    conn.close()


init_db()


# HOME PAGE
@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":

        district = request.form["district"]
        location = request.form["location"]
        operator_name = request.form["operator_name"]
        mobile = request.form["mobile"]
        new_mmmsy = request.form["new_mmmsy"]
        redo_mmmsy = request.form["redo_mmmsy"]

        today = datetime.now().strftime("%d-%m-%Y")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

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


# SUCCESS PAGE
@app.route("/success")
def success():
    return render_template("success.html")


# VIEW REPORTS
@app.route("/view")
def view():

    conn = sqlite3.connect(db_path)

    df = pd.read_sql_query(
        "SELECT * FROM reports ORDER BY id DESC", conn
    )

    conn.close()

    reports = df.values.tolist()

    return render_template("view.html", reports=reports)


# EXPORT TO EXCEL
@app.route("/export")
def export():

    conn = sqlite3.connect(db_path)

    df = pd.read_sql_query("SELECT * FROM reports", conn)

    conn.close()

    file_path = os.path.join(BASE_DIR, "reports.xlsx")

    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)


# RUN SERVER
if __name__ == "__main__":
    app.run(debug=True)
