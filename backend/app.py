from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import json
import os
from report_generator import generate_report
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime # ✨ NEW IMPORT

app = Flask(__name__)
CORS(app)
DATABASE_FILE = 'proctoring_data.db'

# ✨ MODIFIED: Added new "web" alert weights
ALERT_WEIGHTS = {
    "Multiple faces detected!": 25,
    "CELL PHONE detected!": 20,
    "Distraction: Looking away while talking": 10,
    "No person detected!": 15,
    "Someone is talking!": 5,
    "Suspicious micro gesture detected!": 5,
    "Hand on mouse/keyboard detected!": 2,
    "WEB: Switched tabs": 8, # ✨ NEW
    "WEB: Left focus": 5     # ✨ NEW
}

def calculate_integrity_score(alerts):
    score = 100
    if not alerts: return score
    for alert in set(alerts):
        for key, weight in ALERT_WEIGHTS.items():
            if key in alert: score -= weight; break
    return max(0, score)

def init_db():
    # ... (init_db function is completely unchanged) ...
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student', 'admin'))
    );
    """)
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
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        created_by_admin_id INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by_admin_id) REFERENCES users (id)
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS exam_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'assigned',
        assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (exam_id) REFERENCES exams (id),
        FOREIGN KEY (student_id) REFERENCES users (id),
        UNIQUE(exam_id, student_id)
    );
    """)
    conn.commit()
    conn.close()
    print("SQLite database is ready with 'users', 'events', 'exams', and 'exam_assignments' tables.")


# ===================================================
# 🔹 AUTH ENDPOINTS (Unchanged) 🔹
# ===================================================
@app.route('/register', methods=['POST'])
def register():
    # ... (endpoint is unchanged) ...
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')
    if not username or not password or not role:
        return jsonify({"status": "error", "message": "Missing username, password, or role"}), 400
    if role not in ['student', 'admin']:
        return jsonify({"status": "error", "message": "Role must be 'student' or 'admin'"}), 400
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"status": "error", "message": "Username already exists"}), 409
    password_hash = generate_password_hash(password)
    sql = "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)"
    cursor.execute(sql, (username, password_hash, role))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "User registered successfully"}), 201

@app.route('/login', methods=['POST'])
def login():
    # ... (endpoint is unchanged) ...
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"status": "error", "message": "Missing username or password"}), 400
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if not user or not check_password_hash(user['password_hash'], password):
        conn.close()
        return jsonify({"status": "error", "message": "Invalid username or password"}), 401
    conn.close()
    return jsonify({
        "status": "success",
        "message": "Login successful",
        "user": {
            "id": user['id'],
            "username": user['username'],
            "role": user['role']
        }
    }), 200

# ===================================================
# 🔹 ADMIN API ENDPOINTS 🔹
# ===================================================
@app.route('/api/students', methods=['GET'])
def get_students():
    # ... (endpoint is unchanged) ...
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users WHERE role = 'student'")
    students = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(students)

@app.route('/api/exams', methods=['GET', 'POST'])
def handle_exams():
    # ... (endpoint is unchanged) ...
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    if request.method == 'POST':
        data = request.json
        title = data.get('title')
        description = data.get('description')
        admin_id = data.get('admin_id')
        if not title or not admin_id:
            return jsonify({"status": "error", "message": "Missing title or admin_id"}), 400
        cursor = conn.cursor()
        sql = "INSERT INTO exams (title, description, created_by_admin_id) VALUES (?, ?, ?)"
        cursor.execute(sql, (title, description, admin_id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Exam created successfully"}), 201
    elif request.method == 'GET':
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.id, e.title, e.description, e.created_at, u.username as admin_username
            FROM exams e
            JOIN users u ON e.created_by_admin_id = u.id
            ORDER BY e.created_at DESC
        """)
        exams = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(exams)

@app.route('/api/assign', methods=['POST'])
def assign_exam():
    # ... (endpoint is unchanged) ...
    data = request.json
    exam_id = data.get('exam_id')
    student_id = data.get('student_id')
    if not exam_id or not student_id:
        return jsonify({"status": "error", "message": "Missing exam_id or student_id"}), 400
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    try:
        sql = "INSERT INTO exam_assignments (exam_id, student_id) VALUES (?, ?)"
        cursor.execute(sql, (exam_id, student_id))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"status": "error", "message": "This exam is already assigned to this student"}), 409
    conn.close()
    return jsonify({"status": "success", "message": "Exam assigned successfully"}), 201

# --- ✨ NEW ENDPOINT: Get details for a single exam ---
@app.route('/api/exam_details/<int:exam_id>', methods=['GET'])
def get_exam_details(exam_id):
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description FROM exams WHERE id = ?", (exam_id,))
    exam = cursor.fetchone()
    if not exam:
        conn.close()
        return jsonify({"status": "error", "message": "Exam not found"}), 404
    conn.close()
    return jsonify(dict(exam))

# --- ✨ MODIFIED ENDPOINT: Correctly queries by username ---
@app.route('/api/exam_sessions/<int:exam_id>', methods=['GET'])
def get_sessions_for_exam(exam_id):
    """Fetches all proctoring sessions for a specific exam."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Find all students (by username) assigned to this exam
    cursor.execute("""
        SELECT u.username 
        FROM exam_assignments a
        JOIN users u ON a.student_id = u.id
        WHERE a.exam_id = ?
    """, (exam_id,))
    
    students = cursor.fetchall()
    if not students:
        conn.close()
        return jsonify([])

    student_usernames = [s['username'] for s in students]
    placeholders = ','.join('?' for _ in student_usernames)
    
    # Get all event sessions for those students' usernames
    # ✨ We also filter by session_id starting with 'exam_{exam_id}_'
    query = f"""
        SELECT 
            e.session_id, 
            e.student_id as student_username, 
            MIN(e.timestamp) as start_time, 
            MAX(e.integrity_score) as final_score
        FROM events e
        WHERE e.student_id IN ({placeholders}) AND e.session_id LIKE ?
        GROUP BY e.session_id, e.student_id
        ORDER BY start_time DESC
    """
    
    # Add the exam_id filter for the LIKE clause
    params = student_usernames + [f"exam_{exam_id}_%"]
    
    cursor.execute(query, params)
    sessions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(sessions)

# ===================================================
# 🔹 STUDENT API ENDPOINTS 🔹
# ===================================================
@app.route('/api/my_exams/<int:student_id>', methods=['GET'])
def get_student_exams(student_id):
    # ... (endpoint is unchanged) ...
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            e.id as exam_id, e.title, e.description, a.status, a.assigned_at
        FROM exam_assignments a
        JOIN exams e ON a.exam_id = e.id
        WHERE a.student_id = ?
        ORDER BY a.assigned_at DESC
    """, (student_id,))
    exams = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(exams)

# ===================================================
# 🔹 PROCTORING DATA ENDPOINT 🔹
# ===================================================

# --- ✨ MODIFIED ENDPOINT: To handle web alerts and Python alerts ---
@app.route('/log_data', methods=['POST'])
def log_data():
    data = request.json
    
    # Data can come from Python (full payload) or Web (simple alert)
    is_web_alert = data.get('source') == 'web'
    
    student_id = data.get('student_id') # This is the username (e.g., 'student1')
    session_id = data.get('session_id')
    
    if not student_id or not session_id:
        return jsonify({"status": "error", "message": "student_id and session_id are required"}), 400

    if is_web_alert:
        # Simple payload from React (tab switch)
        alerts = data.get('alerts', [])
        metrics = {"source": "web"}
        timestamp = datetime.utcnow().isoformat() + "Z"
    else:
        # Full payload from Python client-agent
        alerts = data.get('alerts', [])
        metrics = data.get('metrics', {})
        timestamp = data.get('timestamp')

    score = calculate_integrity_score(alerts)
    alerts_json = json.dumps(alerts)
    metrics_json = json.dumps(metrics)

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # We store the student's *username* (e.g., 'student1') in the student_id column
    # This is consistent and matches what we query in /api/exam_sessions
    sql = "INSERT INTO events (student_id, session_id, timestamp, alerts, metrics, integrity_score) VALUES (?, ?, ?, ?, ?, ?)"
    cursor.execute(sql, (student_id, session_id, timestamp, alerts_json, metrics_json, score))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Data logged"}), 200

# ===================================================
# 🔹 REPORTING ENDPOINTS (Unchanged) 🔹
# ===================================================
@app.route('/get_sessions/<student_id>', methods=['GET'])
def get_sessions(student_id):
    # ... (endpoint is unchanged) ...
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT session_id FROM events WHERE student_id = ? ORDER BY session_id DESC", (student_id,))
    sessions = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(sessions)

@app.route('/get_data/<student_id>/<session_id>', methods=['GET'])
def get_data(student_id, session_id):
    # ... (endpoint is unchanged) ...
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
    # ... (endpoint is unchanged) ...
    report_path = f"temp_report_{student_id}_{session_id}.pdf"
    generated_file = generate_report(student_id, session_id, report_path)
    if generated_file:
        return send_file(generated_file, as_attachment=True, download_name=f"Report_{student_id}_{session_id}.pdf")
    else:
        return "Could not generate report: No data for this session.", 404

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)