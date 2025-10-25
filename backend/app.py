from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import json
import os
from report_generator import generate_report
from werkzeug.security import generate_password_hash, check_password_hash  # NEW IMPORTS

app = Flask(__name__)
CORS(app)  # This allows our React frontend to make requests
DATABASE_FILE = 'proctoring_data.db'

# (Your existing proctoring logic remains)
ALERT_WEIGHTS = {"Multiple faces detected!": 25, "CELL PHONE detected!": 20, "Distraction: Looking away while talking": 10, "No person detected!": 15, "Someone is talking!": 5, "Suspicious micro gesture detected!": 5, "Hand on mouse/keyboard detected!": 2}

def calculate_integrity_score(alerts):
    score = 100
    if not alerts: return score
    for alert in set(alerts):
        for key, weight in ALERT_WEIGHTS.items():
            if key in alert: score -= weight; break
    return max(0, score)

def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # --- MODIFIED: Added 'users' table ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student', 'admin'))
    );
    """)
    
    # --- This is your existing 'events' table ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        alerts TEXT,
        metrics TEXT,
        integrity_score REAL
    );
    """)
    conn.commit()
    conn.close()
    print("SQLite database is ready with 'users' and 'events' tables.")


# --- NEW ENDPOINT: User Registration ---
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role') # 'student' or 'admin'

    if not username or not password or not role:
        return jsonify({"status": "error", "message": "Missing username, password, or role"}), 400

    if role not in ['student', 'admin']:
        return jsonify({"status": "error", "message": "Role must be 'student' or 'admin'"}), 400

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # Check if user already exists
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"status": "error", "message": "Username already exists"}), 409

    # Hash password and insert new user
    password_hash = generate_password_hash(password)
    sql = "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)"
    cursor.execute(sql, (username, password_hash, role))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "success", "message": "User registered successfully"}), 201


# --- NEW ENDPOINT: User Login ---
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"status": "error", "message": "Missing username or password"}), 400

    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row # Allows us to access columns by name
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return jsonify({"status": "error", "message": "Invalid username or password"}), 401
    
    if not check_password_hash(user['password_hash'], password):
        conn.close()
        return jsonify({"status": "error", "message": "Invalid username or password"}), 401

    conn.close()
    
    # Login successful
    return jsonify({
        "status": "success",
        "message": "Login successful",
        "user": {
            "username": user['username'],
            "role": user['role']
        }
    }), 200


# ===================================================
# 🔹 EXISTING PROCTORING ENDPOINTS (Unchanged) 🔹
# ===================================================

@app.route('/log_data', methods=['POST'])
def log_data():
    data = request.json
    session_id = data.get('session_id')
    if not session_id:
        return jsonify({"status": "error", "message": "session_id is required"}), 400

    student_id = data.get('student_id')
    timestamp = data.get('timestamp')
    alerts = data.get('alerts', [])
    score = calculate_integrity_score(alerts)
    alerts_json = json.dumps(alerts)
    metrics_json = json.dumps(data.get('metrics', {}))

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    sql = "INSERT INTO events (student_id, session_id, timestamp, alerts, metrics, integrity_score) VALUES (?, ?, ?, ?, ?, ?)"
    cursor.execute(sql, (student_id, session_id, timestamp, alerts_json, metrics_json, score))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Data logged"}), 200

@app.route('/get_sessions/<student_id>', methods=['GET'])
def get_sessions(student_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT session_id FROM events WHERE student_id = ? ORDER BY session_id DESC", (student_id,))
    sessions = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(sessions)

@app.route('/get_data/<student_id>/<session_id>', methods=['GET'])
def get_data(student_id, session_id):
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE student_id = ? AND session_id = ? ORDER BY timestamp DESC", (student_id, session_id))
    rows = cursor.fetchall()
    data = [dict(row) for row in rows]
    conn.close()
    return jsonify(data)

@app.route('/generate_report/<student_id>/<session_id>', methods=['GET'])
def download_report(student_id, session_id):
    report_path = f"temp_report_{student_id}_{session_id}.pdf"
    generated_file = generate_report(student_id, session_id, report_path)

    if generated_file:
        return send_file(generated_file, as_attachment=True, download_name=f"Report_{student_id}_{session_id}.pdf")
    else:
        return "Could not generate report: No data for this session.", 404

if __name__ == '__main__':
    init_db()
    # Note: debug=True is great for development, but should be False in production.
    app.run(host='0.0.0.0', port=5000, debug=True)