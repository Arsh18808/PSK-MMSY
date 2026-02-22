from flask import Flask, render_template, request, redirect, send_file, session, flash
import sqlite3
import pandas as pd
import os
from dotenv import load_dotenv
from datetime import datetime
from functools import wraps
import smtplib
from email.message import EmailMessage
from io import BytesIO

load_dotenv()

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


@app.route("/")
@login_required
def home():
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM reports ORDER BY id DESC", conn)
    conn.close()
    reports = df.values.tolist()
    return render_template("view.html", reports=reports)


@app.route("/send-custom-report", methods=["POST"])
@login_required
def send_custom_report():
    emails = request.form.get("emails")

    if not emails:
        flash("No email provided")
        return redirect("/")

    email_list = [e.strip() for e in emails.split(",")]

    # Fetch report data
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM reports", conn)
    conn.close()

    # Create Excel in memory
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    # SMTP Config
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
    SMTP_EMAIL = os.getenv("SMTP_EMAIL")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SMTP_EMAIL_SUBJECT = os.getenv("SMTP_EMAIL_SUBJECT")

    msg = EmailMessage()
    msg["Subject"] = SMTP_EMAIL_SUBJECT
    msg["From"] = SMTP_EMAIL
    msg["To"] = ", ".join(email_list)

    msg.set_content("MMSY Camp Report Attached. Please view in an HTML-supported email client.")

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
    body {{
        font-family: Arial, sans-serif;
        background-color: #f4f6f9;
        margin: 0;
        padding: 0;
    }}
    .container {{
        max-width: 600px;
        margin: auto;
        background: #ffffff;
        padding: 20px;
        border-radius: 8px;
    }}
    .header {{
        background: linear-gradient(135deg, #1f2937, #111827);
        color: white;
        padding: 15px;
        text-align: center;
        border-radius: 6px 6px 0 0;
    }}
    .stats {{
        display: flex;
        justify-content: space-between;
        margin: 20px 0;
    }}
    .stat-box {{
        width: 48%;
        background: #f1f5f9;
        padding: 15px;
        border-radius: 6px;
        text-align: center;
    }}
    .footer {{
        font-size: 12px;
        color: #777;
        margin-top: 20px;
        text-align: center;
    }}
    .button {{
        display: inline-block;
        padding: 10px 18px;
        background: #28a745;
        color: white;
        text-decoration: none;
        border-radius: 20px;
        margin-top: 15px;
    }}
    </style>
    </head>
    <body>

    <div class="container">

        <div class="header">
            <h2>MMSY Camp Reporting System</h2>
            <p>Automated Report Notification</p>
        </div>

        <p>Hello,</p>

        <p>Please find attached the latest <strong>MMSY Camp Report</strong>.</p>

        <div class="stats">
            <div class="stat-box">
                <h4>Total Records</h4>
                <p>{len(df)}</p>
            </div>
            <div class="stat-box">
                <h4>Generated On</h4>
                <p>{datetime.now().strftime("%d-%m-%Y %H:%M")}</p>
            </div>
        </div>

        <p>The detailed report is attached as an Excel file.</p>

        <div style="text-align:center;">
            <a class="button" href="#">MMSY Dashboard</a>
        </div>

        <div class="footer">
            This is an automated email from MMSY Reporting System.<br>
            Please do not reply to this email.
        </div>

    </div>

    </body>
    </html>
    """

    msg.add_alternative(html_content, subtype="html")

    msg.add_attachment(
        output.read(),
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="reports.xlsx"
    )

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.login(SMTP_EMAIL, SMTP_PASSWORD)
            smtp.send_message(msg)

        flash("Email sent successfully!")

    except Exception as e:
        print(e)
        flash("Failed to send email")

    return redirect("/")


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

        session["last_submission"] = {
            "district": district,
            "location": location,
            "operator_name": operator_name,
            "mobile": mobile,
            "new_mmmsy": new_mmmsy,
            "redo_mmmsy": redo_mmmsy,
            "today": today
        }

        return redirect("/success")

    today = datetime.now().strftime("%d-%m-%Y")
    return render_template("index.html", today=today)


# ---------------- SUCCESS ----------------
# @app.route("/success")
# @login_required
# def success():
#     return render_template("success.html")

@app.route("/success")
@login_required
def success():
    data = session.get("last_submission")

    if not data:
        return redirect("/")

    # optional: clear after use
    session.pop("last_submission", None)

    return render_template("success.html", **data)


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
