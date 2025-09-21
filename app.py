from flask import Flask, request, jsonify, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import openai

app = Flask(__name__)
app.secret_key = "supersecretkey"
CORS(app, supports_credentials=True, origins=["http://127.0.0.1:5500"])
openai.api_key = "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"

@app.route("/ask_ai", methods=["POST"])
def ask_ai():
    data = request.get_json()
    question = data.get("question")

    if not question:
        return jsonify({"answer": "Please ask a valid question."})

    # Call OpenAI API
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": question}],
        temperature=0.7
    )

    answer = response.choices[0].message['content']
    return jsonify({"answer": answer})
def get_db():
    conn = sqlite3.connect("careercraft.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        stream TEXT DEFAULT 'Not set',
        skills TEXT DEFAULT '',
        achievements TEXT DEFAULT '',
        profile_pic TEXT DEFAULT ''
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS scholarships(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        url TEXT UNIQUE NOT NULL,
        provider TEXT NOT NULL,
        eligibility TEXT NOT NULL)
    """)
    # Internships table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS internships(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        url TEXT NOT NULL,
        eligibility TEXT NOT NULL
    )
    """)
    cur.execute("""
CREATE TABLE IF NOT EXISTS certifications(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT NOT NULL,
    name TEXT NOT NULL,
    issuer TEXT NOT NULL,
    url TEXT NOT NULL,
    issue_date TEXT NOT NULL
)
""")

    conn.commit()
    conn.close()

@app.route("/certifications", methods=["POST"])
def add_certification():
    data = request.get_json()
    user_email = data.get("email")
    name = data.get("name")
    issuer = data.get("issuer")
    url = data.get("url")
    issue_date = data.get("issue_date")

    if not all([user_email, name, issuer, url, issue_date]):
        return jsonify({"status":"error","message":"All fields required"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO certifications (user_email, name, issuer, url, issue_date)
        VALUES (?, ?, ?, ?, ?)
    """, (user_email, name, issuer, url, issue_date))
    conn.commit()
    conn.close()

    return jsonify({"status":"success","message":"Certification added"}), 200

@app.route("/certifications", methods=["GET"])
def get_certifications():
    email = request.args.get("email")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM certifications WHERE user_email = ?", (email,))
    certs = cur.fetchall()
    return jsonify([dict(c) for c in certs]), 200

@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    email = data["email"]
    password = generate_password_hash(data["password"])
    name = data["name"]

    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
        conn.commit()
        return jsonify({"status": "success"}), 200
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "message": "Email already registered"}), 409

@app.route("/signin", methods=["POST"])
def signin():
    data = request.get_json()
    email = data["email"]
    password = data["password"]

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cur.fetchone()

    if user and check_password_hash(user["password"], password):
        session["user"] = dict(user)
        return jsonify({"status": "success", "user": dict(user)}), 200
    else:
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401

@app.route("/profile", methods=["GET"])
def profile():
    if "user" not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    return jsonify(session["user"])

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "logged out"}), 200


@app.route("/users", methods=["GET"])
def get_all_users():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()

    # Convert rows into list of dicts
    users_list = [dict(user) for user in users]

    return jsonify({"status": "success", "users": users_list}), 200

@app.route("/scholarships", methods=["POST"])
def add_scholarship():
    data = request.get_json()
    name = data.get("name")
    url = data.get("url")
    provider = data.get("provider")
    eligibility = data.get("eligibility")

    if not all([name, url, provider, eligibility]):
        return jsonify({"status": "error", "message": "All fields are required"}), 400

    conn = get_db()
    cur = conn.cursor()

    # Check if scholarship exists
    cur.execute("SELECT id FROM scholarships WHERE url = ?", (url,))
    existing = cur.fetchone()

    if existing:
        # Update existing record
        cur.execute("""
            UPDATE scholarships
            SET name = ?, provider = ?, eligibility = ?
            WHERE id = ?
        """, (name, provider, eligibility, existing["id"]))
        message = "Scholarship updated successfully"
    else:
        # Insert new record
        cur.execute("""
            INSERT INTO scholarships (name, url, provider, eligibility)
            VALUES (?, ?, ?, ?)
        """, (name, url, provider, eligibility))
        message = "Scholarship added successfully"

    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": message}), 200

@app.route("/internships", methods=["POST"])
def add_internship():
    data = request.get_json()
    title = data.get("title")
    company = data.get("company")
    url = data.get("url")
    eligibility = data.get("eligibility")

    if not all([title, company, url, eligibility]):
        return jsonify({"status": "error", "message": "All fields are required"}), 400

    conn = get_db()
    cur = conn.cursor()

    # Check if internship already exists by URL
    cur.execute("SELECT id FROM internships WHERE url = ?", (url,))
    existing = cur.fetchone()

    if existing:
        # Update existing record
        cur.execute("""
            UPDATE internships
            SET title = ?, company = ?, eligibility = ?
            WHERE id = ?
        """, (title, company, eligibility, existing["id"]))
        message = "Internship updated successfully"
    else:
        # Insert new record
        cur.execute("""
            INSERT INTO internships (title, company, url, eligibility)
            VALUES (?, ?, ?, ?)
        """, (title, company, url, eligibility))
        message = "Internship added successfully"

    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": message}), 200

@app.route("/scholarships", methods=["GET"])
def get_scholarships():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM scholarships")
    scholarships = cur.fetchall()
    return jsonify([dict(s) for s in scholarships]), 200

@app.route("/internships", methods=["GET"])
def get_internships():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM internships")
    internships = cur.fetchall()
    return jsonify([dict(s) for s in internships]), 200

@app.route("/update_profile", methods=["POST"])
def update_profile():
    if "user" not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    stream = data.get("stream", "")
    skills = data.get("skills", "")
    achievements = data.get("achievements", "")
    profile_pic = data.get("profile_pic", "")  # new field

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users 
        SET name = ?, email = ?, stream = ?, skills = ?, achievements = ?, profile_pic = ?
        WHERE id = ?
    """, (name, email, stream, skills, achievements, profile_pic, session["user"]["id"]))

    conn.commit()
    
    cur.execute("SELECT * FROM users WHERE id = ?", (session["user"]["id"],))
    updated_user = cur.fetchone()
    session["user"] = dict(updated_user)

    return jsonify({"status": "success", "user": dict(updated_user)}), 200


if __name__ == "__main__":
    init_db() 
    app.run(debug=True)
